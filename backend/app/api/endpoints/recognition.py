"""
图像识别 API
视觉定位功能
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import RecognitionResponse, RecognitionErrorResponse
from app.services import ai_service, graph_service

router = APIRouter(prefix="/recognition", tags=["图像识别"])


@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_location(
    file: UploadFile = File(..., description="上传的图片文件"),
    db: AsyncSession = Depends(get_db)
) -> RecognitionResponse:
    """
    识别图片中的位置
    
    上传一张周围环境的照片，系统识别当前位置并返回最可能的候选结果。
    
    - **file**: 图片文件（支持 PNG、JPG 格式）
    
    返回按置信度排序的 Top 3 候选位置。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 [识别请求] 开始处理图片识别请求")
    logger.info(f"📄 [文件信息] 文件名: {file.filename}, 类型: {file.content_type}, 大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning(f"❌ [文件验证] 无效的文件类型: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail="请上传图片文件（PNG、JPG 格式）"
        )
    logger.info(f"✅ [文件验证] 文件类型验证通过: {file.content_type}")
    
    # 确保图结构已加载（用于获取节点信息）
    if graph_service.reload_required():
        logger.info("🔄 [图结构] 需要重新加载图结构")
        await graph_service.load_graph_from_db(db)
    else:
        logger.info("✅ [图结构] 图结构已加载")
    
    node_count = len(graph_service.get_all_nodes())
    logger.info(f"📊 [图结构] 当前节点数量: {node_count}")
    
    # 读取图片内容
    try:
        image_data = await file.read()
        image_size = len(image_data)
        logger.info(f"✅ [图片读取] 成功读取图片，大小: {image_size} bytes ({image_size / 1024:.2f} KB)")
    except Exception as e:
        logger.error(f"❌ [图片读取] 读取失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"读取图片失败: {str(e)}")
    
    # 验证图片大小（最大 10MB）
    if image_size > 10 * 1024 * 1024:
        logger.warning(f"❌ [图片验证] 图片过大: {image_size / 1024 / 1024:.2f} MB")
        raise HTTPException(status_code=400, detail="图片文件过大，最大支持 10MB")
    
    # 检查 AI 服务模式
    is_mock = ai_service._mock_mode
    logger.info(f"🤖 [AI服务] 当前模式: {'Mock (模拟)' if is_mock else 'Real (真实识别)'}")
    
    # 调用 AI 服务进行识别
    try:
        logger.info("🚀 [识别开始] 调用 AI 服务进行识别...")
        candidates = await ai_service.recognize_location(image_data, top_k=3)
        logger.info(f"✅ [识别完成] 识别到 {len(candidates)} 个候选位置")
        
        if candidates:
            for i, candidate in enumerate(candidates, 1):
                logger.info(f"  [{i}] {candidate.node_name} (楼层: {candidate.floor}, 置信度: {candidate.confidence})")
    except Exception as e:
        logger.error(f"❌ [识别失败] 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")
    
    if not candidates:
        logger.warning("⚠️ [识别结果] 未识别到任何位置")
        return RecognitionResponse(
            success=True,
            candidates=[],
            message="未能识别出位置，请尝试更换角度重新拍照",
            method="mock" if is_mock else "real",
            debug_info={
                "node_count": node_count,
                "image_size": image_size,
                "mode": "mock" if is_mock else "real"
            }
        )
    
    logger.info(f"✅ [请求完成] 成功返回 {len(candidates)} 个候选位置")
    return RecognitionResponse(
        success=True,
        candidates=candidates,
        message="识别完成",
        method="mock" if is_mock else "real",
        debug_info={
            "node_count": node_count,
            "image_size": image_size,
            "mode": "mock" if is_mock else "real",
            "candidates_count": len(candidates)
        }
    )

