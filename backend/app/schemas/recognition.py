"""
图像识别相关的 Pydantic 模型
用于 API 请求/响应的数据验证
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class LocationCandidate(BaseModel):
    """位置候选结果"""
    node_id: str = Field(..., description="节点ID")
    node_name: str = Field(..., description="节点名称")
    detail: Optional[str] = Field(None, description="详细位置")
    floor: int = Field(..., description="楼层")
    confidence: float = Field(..., ge=0, le=1, description="置信度分数 (0-1)")


class RecognitionResponse(BaseModel):
    """图像识别响应模型"""
    success: bool = True
    candidates: List[LocationCandidate] = Field(..., description="候选位置列表，按置信度降序")
    message: str = "识别完成"
    method: str = Field("mock", description="识别方法：mock/ocr/clip")


class RecognitionErrorResponse(BaseModel):
    """识别错误响应"""
    success: bool = False
    message: str
    candidates: List[LocationCandidate] = []
    method: str = "error"

