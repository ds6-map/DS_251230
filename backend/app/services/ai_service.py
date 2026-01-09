"""
AI 服务模块
视觉定位和图像识别
使用 OpenCLIP (ViT-B-32) + ChromaDB 进行图像相似度检索
"""
import random
import base64
import logging
from typing import List, Optional, Dict, Any
from app.schemas import LocationCandidate
from app.services.graph_service import graph_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """
    AI 服务类
    提供图像识别和视觉定位功能

    实现方式：
    - Mock 模式：随机返回节点（用于测试）
    - 真实模式：使用 OpenCLIP (ViT-B-32) 提取特征 + ChromaDB 向量检索
    """

    def __init__(self):
        self._model_loaded = False
        self._mock_mode = settings.AI_MOCK_MODE
        self._vision_available = False

    async def load_model(self) -> None:
        """
        加载 AI 模型
        检测 vision_client 是否可用
        """
        if self._mock_mode:
            # Mock 模式下不需要加载模型
            self._model_loaded = True
            logger.info("🎭 [AI服务] Mock 模式已启用")
            return

        # 检测 vision_client 是否可用
        try:
            from app.services.vision_client import _try_import_backend
            chromadb, OpenCLIPEmbeddings = _try_import_backend()
            if chromadb and OpenCLIPEmbeddings:
                self._vision_available = True
                self._model_loaded = True
                logger.info("✅ [AI服务] ViT 图像识别功能已就绪")
            else:
                logger.warning("⚠️ [AI服务] 图像识别依赖未安装，将使用 Mock 模式")
                self._vision_available = False
                self._model_loaded = True
        except Exception as e:
            logger.warning(f"⚠️ [AI服务] 初始化图像识别失败: {e}，将使用 Mock 模式")
            self._vision_available = False
            self._model_loaded = True

    async def recognize_location(
        self,
        image_data: bytes,
        top_k: int = 3
    ) -> List[LocationCandidate]:
        """
        识别图片中的位置

        Args:
            image_data: 图片二进制数据
            top_k: 返回前 K 个候选结果

        Returns:
            LocationCandidate 列表，按置信度降序排列
        """
        # Mock 模式
        if self._mock_mode:
            logger.info("🎭 [AI服务] 使用 Mock 模式进行识别")
            return await self._mock_recognize(top_k)

        # 真实识别模式
        if not self._vision_available:
            logger.warning("⚠️ [AI服务] 图像识别不可用，回退到 Mock 模式")
            return await self._mock_recognize(top_k)

        try:
            logger.info("🔍 [AI服务] 使用 ViT 模型进行真实图像识别")
            return await self._real_recognize(image_data, top_k)
        except Exception as e:
            logger.error(f"❌ [AI服务] 真实识别失败: {e}，回退到 Mock 模式")
            return await self._mock_recognize(top_k)

    async def _real_recognize(
        self,
        image_data: bytes,
        top_k: int = 3
    ) -> List[LocationCandidate]:
        """
        使用 ViT 模型进行真实图像识别

        流程：
        1. 将图片数据转为 base64
        2. 调用 vision_client 进行相似度检索
        3. 将返回的 label 映射到数据库节点
        4. 返回 LocationCandidate 列表
        """
        from app.services.vision_client import recognize_image_base64

        # 1. 将图片数据转为 base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        logger.info(f"📷 [AI服务] 图片大小: {len(image_data)} bytes")

        # 2. 调用 vision_client 进行相似度检索
        logger.info("🔍 [AI服务] 调用 vision_client 进行图像检索...")
        result = recognize_image_base64(
            image_base64=image_base64,
            dataset_folder="image_data",
            top_k=top_k
        )

        if result.get("status") != "success":
            logger.warning(f"⚠️ [AI服务] 图像检索失败: {result}")
            return []

        matches = result.get("matches", [])
        logger.info(f"✅ [AI服务] 找到 {len(matches)} 个匹配结果")

        # 3. 将返回的 label 映射到数据库节点
        candidates = await self._map_matches_to_candidates(matches)

        return candidates

    async def _map_matches_to_candidates(
        self,
        matches: List[Dict[str, Any]]
    ) -> List[LocationCandidate]:
        """
        将 vision_client 返回的匹配结果映射到 LocationCandidate

        matches 格式: [{"path": "...", "score": 0.85, "label": "L4_LT9"}, ...]
        label 格式如 "L4_LT9" 对应楼层4的LT9教室
        """
        candidates = []
        all_nodes = graph_service.get_all_nodes()

        if not all_nodes:
            logger.warning("⚠️ [AI服务] 图结构中没有节点数据")
            return []

        # 创建节点查找映射（按 id 和 name）
        nodes_by_id = {node["id"]: node for node in all_nodes}
        nodes_by_name = {node["name"]: node for node in all_nodes}

        for i, match in enumerate(matches):
            label = match.get("label", "")
            score = match.get("score", 0.0)
            path = match.get("path", "")

            logger.info(f"📍 [AI服务] 匹配 [{i+1}]: label={label}, score={score:.4f}")

            # 尝试匹配节点
            node = None

            # 1. 直接用 label 作为 node_id 查找
            if label in nodes_by_id:
                node = nodes_by_id[label]
                logger.info(f"  ✅ 通过 ID 匹配到节点: {node['name']}")

            # 2. 用 label 作为 node_name 查找
            elif label in nodes_by_name:
                node = nodes_by_name[label]
                logger.info(f"  ✅ 通过名称匹配到节点: {node['name']}")

            # 3. 模糊匹配：label 包含在节点 id 或 name 中
            else:
                for n in all_nodes:
                    if label in n["id"] or label in n["name"] or n["id"] in label or n["name"] in label:
                        node = n
                        logger.info(f"  ✅ 通过模糊匹配到节点: {node['name']}")
                        break

            # 4. 从 label 解析楼层，尝试找同楼层的节点
            if not node and label:
                floor = self._extract_floor_from_label(label)
                if floor:
                    floor_nodes = [n for n in all_nodes if n.get("floor") == floor]
                    if floor_nodes:
                        # 选择第一个同楼层节点
                        node = floor_nodes[0]
                        logger.info(f"  ⚠️ 未精确匹配，使用同楼层节点: {node['name']}")

            if node:
                candidate = LocationCandidate(
                    node_id=node["id"],
                    node_name=node["name"],
                    detail=node.get("detail") or f"识别自: {label}",
                    floor=node["floor"],
                    confidence=round(score, 2),
                )
                candidates.append(candidate)
            else:
                logger.warning(f"  ❌ 无法匹配 label: {label}")

        # 按置信度降序排序
        candidates.sort(key=lambda x: x.confidence, reverse=True)

        return candidates

    def _extract_floor_from_label(self, label: str) -> Optional[int]:
        """
        从 label 中提取楼层信息
        例如 "L4_LT9" -> 4, "L5_PACE" -> 5
        """
        import re
        match = re.search(r'L(\d+)', label, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    async def _mock_recognize(self, top_k: int = 3) -> List[LocationCandidate]:
        """
        Mock 识别实现
        随机返回一些节点作为候选结果
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🎲 [Mock识别] 开始 Mock 识别，请求 top_k={top_k}")
        
        all_nodes = graph_service.get_all_nodes()
        logger.info(f"📊 [Mock识别] 图中共有 {len(all_nodes)} 个节点")
        
        if not all_nodes:
            logger.warning("⚠️ [Mock识别] 图结构中没有节点数据")
            return []
        
        # 随机选择节点
        sample_size = min(top_k, len(all_nodes))
        selected_nodes = random.sample(all_nodes, sample_size)
        logger.info(f"🎯 [Mock识别] 随机选择了 {sample_size} 个节点")
        
        # 生成随机置信度（按降序排列）
        confidences = sorted([random.uniform(0.5, 0.95) for _ in range(sample_size)], reverse=True)
        
        candidates = []
        for i, node in enumerate(selected_nodes):
            candidate = LocationCandidate(
                node_id=node["id"],
                node_name=node["name"],
                detail=node.get("detail"),
                floor=node["floor"],
                confidence=round(confidences[i], 2),
            )
            candidates.append(candidate)
            logger.info(f"  [{i+1}] 节点: {node['name']} (ID: {node['id']}, 楼层: {node['floor']}, 置信度: {candidate.confidence})")
        
        logger.info(f"✅ [Mock识别] 完成，返回 {len(candidates)} 个候选结果")
        return candidates
    
    async def _extract_image_features(self, image_data: bytes):
        """
        提取图像特征向量
        
        TODO: 使用 CLIP 模型提取特征
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            特征向量 (numpy array)
        """
        # TODO: 实现图像特征提取
        # from PIL import Image
        # import io
        # image = Image.open(io.BytesIO(image_data))
        # features = self.model.encode(image)
        # return features
        pass
    
    async def _search_similar_nodes(
        self,
        query_vector,
        top_k: int = 3
    ) -> List[LocationCandidate]:
        """
        在向量库中搜索相似节点
        
        TODO: 使用 FAISS 或简单余弦相似度
        
        Args:
            query_vector: 查询向量
            top_k: 返回前 K 个结果
            
        Returns:
            LocationCandidate 列表
        """
        # TODO: 实现向量检索
        # distances, indices = self.faiss_index.search(query_vector, top_k)
        # 或使用简单的余弦相似度
        # similarities = cosine_similarity(query_vector, node_vectors)
        pass
    
    async def _ocr_recognize(self, image_data: bytes) -> Optional[List[LocationCandidate]]:
        """
        OCR 识别图片中的文字
        
        TODO: 使用 PaddleOCR 识别文字
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            如果识别到匹配的节点，返回 LocationCandidate 列表
            否则返回 None
        """
        # TODO: 实现 OCR 识别
        # from paddleocr import PaddleOCR
        # ocr = PaddleOCR()
        # result = ocr.ocr(image_data)
        # 解析结果，匹配节点名称
        pass


# 全局单例
ai_service = AIService()

