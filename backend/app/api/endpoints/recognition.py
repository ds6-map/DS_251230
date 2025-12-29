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
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="请上传图片文件（PNG、JPG 格式）"
        )
    
    # 确保图结构已加载（用于获取节点信息）
    if graph_service.reload_required():
        await graph_service.load_graph_from_db(db)
    
    # 读取图片内容
    try:
        image_data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取图片失败: {str(e)}")
    
    # 验证图片大小（最大 10MB）
    if len(image_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片文件过大，最大支持 10MB")
    
    # 调用 AI 服务进行识别
    try:
        candidates = await ai_service.recognize_location(image_data, top_k=3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")
    
    if not candidates:
        return RecognitionResponse(
            success=True,
            candidates=[],
            message="未能识别出位置，请尝试更换角度重新拍照",
            method="mock",
        )
    
    return RecognitionResponse(
        success=True,
        candidates=candidates,
        message="识别完成",
        method="mock",  # 当前为 Mock 模式
    )

