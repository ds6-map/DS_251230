import base64
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Dict, Optional


# 说明：
# - 本文件提供"图片相似检索"的能力：把数据库图片向量化存入 ChromaDB，然后对用户上传图片做相似度查询
# - 设计上不处理 HTTP；上层会传入 base64 或本地文件路径
@dataclass(frozen=True)
class VisionMatch:
    path: str
    score: float


def _try_import_backend():
    # 可选依赖：如果环境没装 chromadb / open_clip，则返回 None
    try:
        import chromadb  # type: ignore
        from langchain_experimental.open_clip import OpenCLIPEmbeddings  # type: ignore
        return chromadb, OpenCLIPEmbeddings
    except ImportError as e:
        # 静默处理导入错误，只在 DEBUG 模式下输出详细信息
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[vision_client] 图片识别依赖未安装: {e}")
        logger.info("[vision_client] 💡 提示: 如需使用图片识别功能，请安装依赖: pip install chromadb langchain-experimental open-clip-torch torch torchvision")
        return None, None
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.warning(f"[vision_client] 导入依赖时出错: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            traceback.print_exc()
        return None, None


def _list_images(dataset_folder: str) -> List[str]:
    # 遍历图像库目录，收集支持的图片文件
    image_paths: List[str] = []
    valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    for root, _, files in os.walk(dataset_folder):
        for file in files:
            if file.lower().endswith(valid_extensions):
                image_paths.append(os.path.join(root, file))
    return image_paths


def _extract_label(image_path: str, dataset_folder: str) -> str:
    """从图片路径中提取标签（父文件夹名称）"""
    rel_path = os.path.relpath(image_path, dataset_folder)
    parts = rel_path.split(os.sep)
    if len(parts) >= 2:
        return parts[-2]  # 直接父文件夹作为标签
    return "unknown"


_MODEL = None
_COLLECTION = None
_INDEXED_DATASET = None


def _project_root() -> Path:
    # 统一以项目根作为基准，保证从任意 cwd 启动都能找到 image_data/
    # vision_client.py 位于: backend/app/services/vision_client.py
    # 项目根目录应该是: backend/app/services/ -> backend/app/ -> backend/ -> 项目根
    current_file = Path(__file__).resolve()
    # 从 backend/app/services/vision_client.py 到项目根需要上3级
    project_root = current_file.parents[3]
    
    # 验证：检查 image_data 目录是否存在
    image_data_path = project_root / "image_data"
    if not image_data_path.exists():
        # 如果找不到，尝试从 backend 目录向上找
        backend_dir = current_file.parents[2]  # backend/
        project_root_alt = backend_dir.parent  # 项目根
        if (project_root_alt / "image_data").exists():
            return project_root_alt
    
    return project_root


def _resolve_dataset_folder(dataset_folder: str) -> str:
    # 支持传入绝对路径；如果是相对路径则相对项目根解析
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        p = Path(dataset_folder).expanduser()
        if p.is_absolute():
            resolved_path = str(p.resolve())
            logger.debug(f"[vision_client] 使用绝对路径: {resolved_path}")
            if not os.path.exists(resolved_path):
                logger.warning(f"[vision_client] 路径不存在: {resolved_path}")
            return resolved_path
        
        project_root = _project_root()
        resolved_path = str((project_root / p).resolve())
        logger.debug(f"[vision_client] 解析路径: {dataset_folder} -> {resolved_path}")
        logger.debug(f"[vision_client] 项目根目录: {project_root}")
        
        if not os.path.exists(resolved_path):
            logger.warning(f"[vision_client] 路径不存在: {resolved_path}")
            logger.warning(f"[vision_client] 请检查 image_data 目录是否在项目根目录下")
        
        return resolved_path
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[vision_client] 路径解析失败: {e}", exc_info=True)
        # ERROR_CODE: VISION_ERR_PATH_RESOLVE_FAILED
        raise RuntimeError(f"VISION_ERR_PATH_RESOLVE_FAILED: {str(e)}")


def _chroma_persist_dir() -> str:
    p = (_project_root() / "chroma").resolve()
    os.makedirs(p, exist_ok=True)
    return str(p)


def _collection_name_for_dataset(dataset_folder: str) -> str:
    h = hashlib.sha1(dataset_folder.encode("utf-8")).hexdigest()
    return f"visual_search_{h}"


def _image_id(image_path: str) -> str:
    return hashlib.sha1(image_path.encode("utf-8")).hexdigest()


def _normalize_embeddings(vectors: Any) -> List[List[float]]:
    if (
        isinstance(vectors, list)
        and len(vectors) > 0
        and isinstance(vectors[0], list)
        and len(vectors[0]) > 0
        and isinstance(vectors[0][0], list)
    ):
        return [v[0] for v in vectors]
    return vectors


def _scan_dataset(dataset_folder: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in _list_images(dataset_folder):
        try:
            mtime = float(os.path.getmtime(p))
        except Exception:
            mtime = 0.0
        items.append(
            {
                "id": _image_id(p),
                "path": p,
                "mtime": mtime,
                "label": _extract_label(p, dataset_folder),
            }
        )
    items.sort(key=lambda x: x["path"])
    return items


def _sync_collection(dataset_folder: str, collection):
    assert _MODEL is not None

    current_items = _scan_dataset(dataset_folder)
    if not current_items:
        # ERROR_CODE: VISION_ERR_DATASET_EMPTY
        raise RuntimeError(f"VISION_ERR_DATASET_EMPTY: No valid images in {dataset_folder}")

    current_by_id = {x["id"]: x for x in current_items}

    existing_by_id: Dict[str, Dict[str, Any]] = {}
    try:
        limit = None
        if hasattr(collection, "count"):
            try:
                limit = int(collection.count())
            except Exception:
                limit = None
        if limit:
            got = collection.get(limit=limit, include=["metadatas", "documents"])
        else:
            got = collection.get(include=["metadatas", "documents"])
        ids = got.get("ids") or []
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        for i, _id in enumerate(ids):
            meta = metas[i] if i < len(metas) else None
            doc = docs[i] if i < len(docs) else None
            if not _id:
                continue
            existing_by_id[str(_id)] = {"document": doc, "metadata": meta or {}}
    except Exception:
        existing_by_id = {}

    existing_ids = set(existing_by_id.keys())
    current_ids = set(current_by_id.keys())

    ids_to_delete = sorted(existing_ids - current_ids)
    ids_to_add: List[str] = []
    ids_to_update: List[str] = []

    for _id, item in current_by_id.items():
        if _id not in existing_by_id:
            ids_to_add.append(_id)
            continue
        meta = existing_by_id[_id].get("metadata") or {}
        doc = existing_by_id[_id].get("document")
        prev_path = meta.get("path") or doc
        prev_mtime = meta.get("mtime")
        if prev_path != item["path"] or prev_mtime != item["mtime"]:
            ids_to_update.append(_id)

    if ids_to_delete:
        try:
            collection.delete(ids=ids_to_delete)
        except Exception:
            pass

    def _write_items(item_ids: List[str], *, mode: str):
        if not item_ids:
            return
        batch_size = 64
        for i in range(0, len(item_ids), batch_size):
            chunk_ids = item_ids[i : i + batch_size]
            chunk_items = [current_by_id[_id] for _id in chunk_ids]
            chunk_paths = [x["path"] for x in chunk_items]
            chunk_vectors = _normalize_embeddings(_MODEL.embed_image(uris=chunk_paths))
            chunk_metadatas = [
                {"path": x["path"], "mtime": x["mtime"], "label": x["label"]} for x in chunk_items
            ]
            if mode == "upsert" and hasattr(collection, "upsert"):
                collection.upsert(
                    ids=chunk_ids,
                    documents=chunk_paths,
                    embeddings=chunk_vectors,
                    metadatas=chunk_metadatas,
                )
            else:
                if mode == "upsert":
                    try:
                        collection.delete(ids=chunk_ids)
                    except Exception:
                        pass
                collection.add(
                    ids=chunk_ids,
                    documents=chunk_paths,
                    embeddings=chunk_vectors,
                    metadatas=chunk_metadatas,
                )

    _write_items(ids_to_add, mode="add")
    _write_items(ids_to_update, mode="upsert")


def _guess_mime_from_path(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".jpg" or ext == ".jpeg":
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext == ".bmp":
        return "image/bmp"
    return "application/octet-stream"


def _bytes_to_data_url(data: bytes, mime: str) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _file_to_data_url(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            data = f.read()
        return _bytes_to_data_url(data, _guess_mime_from_path(path))
    except Exception:
        return None


def _ensure_index(dataset_folder: str):
    # 确保已为 dataset_folder 建立检索索引（向量化 + 写入 Chroma collection）
    global _MODEL, _COLLECTION, _INDEXED_DATASET

    chromadb, OpenCLIPEmbeddings = _try_import_backend()
    if not chromadb or not OpenCLIPEmbeddings:
        # ERROR_CODE: VISION_ERR_BACKEND_MISSING
        import logging
        logger = logging.getLogger(__name__)
        logger.error("[vision_client] 图片识别依赖未安装")
        logger.error("[vision_client] 请运行: pip install chromadb langchain-experimental open-clip-torch torch torchvision")
        raise RuntimeError("VISION_ERR_BACKEND_MISSING: 缺少图片识别依赖包。请安装: pip install chromadb langchain-experimental open-clip-torch torch torchvision")

    if _INDEXED_DATASET == dataset_folder and _MODEL is not None and _COLLECTION is not None:
        return

    if not os.path.exists(dataset_folder):
        # ERROR_CODE: VISION_ERR_DATASET_NOT_FOUND
        raise RuntimeError(f"VISION_ERR_DATASET_NOT_FOUND: {dataset_folder}")

    try:
        _MODEL = OpenCLIPEmbeddings(model_name="ViT-B-32", checkpoint="laion2b_s34b_b79k")

        client = chromadb.PersistentClient(path=_chroma_persist_dir())
        collection = client.get_or_create_collection(name=_collection_name_for_dataset(dataset_folder))
        _sync_collection(dataset_folder, collection)

        _COLLECTION = collection
        _INDEXED_DATASET = dataset_folder
    except Exception as e:
        # ERROR_CODE: VISION_ERR_INDEXING_FAILED
        raise RuntimeError(f"VISION_ERR_INDEXING_FAILED: {str(e)}")


def recognize_image_path(
    *,
    image_path: str,
    dataset_folder: str = "image_data",
    top_k: int = 3,
) -> Dict[str, Any]:
    # 输入：本地图片路径
    dataset_folder = _resolve_dataset_folder(dataset_folder)
    _ensure_index(dataset_folder)
    
    assert _MODEL is not None
    assert _COLLECTION is not None

    import logging
    logger = logging.getLogger(__name__)
    
    # 验证文件是否存在且可读
    if not os.path.exists(image_path):
        logger.error(f"[vision_client] 图片文件不存在: {image_path}")
        raise RuntimeError(f"VISION_ERR_QUERY_IMAGE_NOT_FOUND: {image_path}")
    
    # 检查文件权限
    if not os.access(image_path, os.R_OK):
        logger.error(f"[vision_client] 图片文件无读取权限: {image_path}")
        logger.error(f"[vision_client] 文件信息: exists={os.path.exists(image_path)}, isfile={os.path.isfile(image_path)}")
        raise RuntimeError(f"VISION_ERR_QUERY_IMAGE_PERMISSION_DENIED: {image_path}")
    
    try:
        file_size = os.path.getsize(image_path)
        logger.debug(f"[vision_client] 开始处理图片: {image_path}, 大小: {file_size} bytes")
        
        # 提取图片特征向量
        logger.debug(f"[vision_client] 调用 embed_image 提取特征...")
        
        # 在 Windows 上，使用绝对路径确保文件可访问
        abs_image_path = os.path.abspath(image_path)
        logger.debug(f"[vision_client] 原始路径: {image_path}")
        logger.debug(f"[vision_client] 绝对路径: {abs_image_path}")
        
        # 再次验证绝对路径的文件可访问性
        if not os.path.exists(abs_image_path):
            raise RuntimeError(f"VISION_ERR_QUERY_IMAGE_NOT_FOUND: {abs_image_path}")
        if not os.access(abs_image_path, os.R_OK):
            raise RuntimeError(f"VISION_ERR_QUERY_IMAGE_PERMISSION_DENIED: {abs_image_path}")
        
        # 使用绝对路径调用 embed_image
        query_vector = _MODEL.embed_image(uris=[abs_image_path])
        query_vector = _normalize_embeddings(query_vector)
        logger.debug(f"[vision_client] 特征向量提取完成，维度: {len(query_vector[0]) if query_vector and len(query_vector) > 0 else 0}")

        # 在向量库中搜索
        logger.debug(f"[vision_client] 在向量库中搜索相似图片...")
        results = _COLLECTION.query(query_embeddings=query_vector, n_results=top_k)
        top_matches = results["documents"][0]
        top_scores = results["distances"][0]
        logger.debug(f"[vision_client] 搜索完成，找到 {len(top_matches)} 个候选结果")

        matches: List[Dict[str, Any]] = []
        for i, p in enumerate(top_matches):
            score = 1 - float(top_scores[i])
            label = _extract_label(p, dataset_folder)
            matches.append({"path": p, "score": score, "label": label})
            logger.debug(f"[vision_client] 匹配 [{i+1}]: {label} (路径: {p}, 相似度: {score:.4f})")
        
        logger.info(f"[vision_client] 识别成功，返回 {len(matches)} 个匹配结果")
        return {"matches": matches, "status": "success"}
    except PermissionError as e:
        logger.error(f"[vision_client] 权限错误: {e}")
        logger.error(f"[vision_client] 文件路径: {image_path}")
        logger.error(f"[vision_client] 文件存在: {os.path.exists(image_path)}")
        logger.error(f"[vision_client] 文件可读: {os.access(image_path, os.R_OK) if os.path.exists(image_path) else False}")
        raise RuntimeError(f"VISION_ERR_SEARCH_EXECUTION_FAILED: 权限被拒绝 - {image_path}。错误: {str(e)}")
    except Exception as e:
        logger.error(f"[vision_client] 图片识别失败: {e}", exc_info=True)
        logger.error(f"[vision_client] 文件路径: {image_path}")
        logger.error(f"[vision_client] 文件存在: {os.path.exists(image_path)}")
        # ERROR_CODE: VISION_ERR_SEARCH_EXECUTION_FAILED
        raise RuntimeError(f"VISION_ERR_SEARCH_EXECUTION_FAILED: {str(e)}")


def recognize_image_base64(
    *,
    image_base64: str,
    dataset_folder: str = "image_data",
    top_k: int = 3,
) -> Dict[str, Any]:
    # 输入：前端 DataURL 或纯 base64
    dataset_folder = _resolve_dataset_folder(dataset_folder)
    
    try:
        raw0 = image_base64.strip()
        query_image_data_url = raw0 if raw0.startswith("data:") else f"data:image/jpeg;base64,{raw0}"
        raw = raw0
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        data = base64.b64decode(raw, validate=False)
    except Exception as e:
        # ERROR_CODE: VISION_ERR_BASE64_DECODE_FAILED
        raise RuntimeError(f"VISION_ERR_BASE64_DECODE_FAILED: {str(e)}")

    # 使用 mkstemp 创建临时文件，避免 Windows 权限问题
    temp_fd = None
    temp_path = None
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # 创建临时文件（Windows 兼容方式）
        temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg", prefix="vision_")
        logger.debug(f"[vision_client] 创建临时文件: {temp_path}")
        
        try:
            # 使用文件描述符写入数据
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(data)
                f.flush()
            # 文件描述符会在 with 语句中自动关闭
            temp_fd = None
            
            # 在 Windows 上，确保文件有读取权限
            # 使用 stat 模块设置文件权限（如果系统支持）
            try:
                import stat
                # 设置文件为可读可写（用户、组、其他）
                os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                logger.debug(f"[vision_client] 已设置临时文件权限: {temp_path}")
            except Exception as chmod_error:
                # 在某些系统上 chmod 可能不可用，忽略错误
                logger.debug(f"[vision_client] 无法设置文件权限（可忽略）: {chmod_error}")
        except Exception as e:
            # 如果写入失败，确保关闭文件描述符
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except Exception:
                    pass
            raise
        
        # 验证文件是否存在且可读
        if not os.path.exists(temp_path):
            raise RuntimeError(f"临时文件创建失败: {temp_path}")
        
        file_size = os.path.getsize(temp_path)
        logger.debug(f"[vision_client] 临时文件已创建，大小: {file_size} bytes")
        
        # 再次验证文件权限（在调用识别前）
        if not os.access(temp_path, os.R_OK):
            logger.error(f"[vision_client] 临时文件无读取权限: {temp_path}")
            raise RuntimeError(f"临时文件无读取权限: {temp_path}")
        
        # 尝试打开文件验证可访问性
        try:
            with open(temp_path, 'rb') as test_f:
                test_f.read(1)  # 尝试读取一个字节
            logger.debug(f"[vision_client] 临时文件权限验证通过，准备调用识别函数")
        except PermissionError as e:
            logger.error(f"[vision_client] 无法读取临时文件: {e}")
            raise RuntimeError(f"无法读取临时文件: {temp_path}, 错误: {str(e)}")
        
        # 调用识别函数（确保文件在识别过程中保持可访问）
        result = recognize_image_path(image_path=temp_path, dataset_folder=dataset_folder, top_k=top_k)
        matches = result.get("matches") or []
        
        # 为匹配结果添加图片数据 URL
        for m in matches:
            p = m.get("path") if isinstance(m, dict) else None
            if isinstance(p, str) and p:
                m["image_data_url"] = _file_to_data_url(p)
        
        result["query_image_data_url"] = query_image_data_url
        logger.debug(f"[vision_client] 识别完成，找到 {len(matches)} 个匹配结果")
        
        return result
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[vision_client] 处理临时文件时出错: {e}", exc_info=True)
        # 透传下游错误
        if "VISION_ERR" in str(e):
            raise
        raise RuntimeError(f"VISION_ERR_TEMPFILE_OP_FAILED: {str(e)}")
    finally:
        # 清理临时文件
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except Exception:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"[vision_client] 已删除临时文件: {temp_path}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[vision_client] 删除临时文件失败: {temp_path}, 错误: {e}")

