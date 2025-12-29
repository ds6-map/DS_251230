"""
节点相关的 Pydantic 模型
用于 API 请求/响应的数据验证
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class NodeBase(BaseModel):
    """节点基础模型"""
    id: str = Field(..., description="节点唯一标识，如 LT5")
    name: str = Field(..., description="节点名称，如 LectureTheater5")
    floor: int = Field(..., description="所在楼层")


class NodeCreate(NodeBase):
    """创建节点请求模型"""
    detail: Optional[str] = Field(None, description="详细位置描述")
    x: Optional[float] = Field(None, description="X坐标（像素）")
    y: Optional[float] = Field(None, description="Y坐标（像素）")
    node_type: Optional[str] = Field("other", description="节点类型")


class NodeResponse(NodeBase):
    """节点响应模型"""
    detail: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    node_type: Optional[str] = None
    has_coordinates: bool = Field(..., description="是否已设置坐标")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NodePositionUpdate(BaseModel):
    """更新节点坐标请求模型"""
    x: float = Field(..., description="X坐标（像素）")
    y: float = Field(..., description="Y坐标（像素）")


class NodeBatchUpdate(BaseModel):
    """批量更新节点坐标请求模型"""
    nodes: List[dict] = Field(..., description="节点列表，每个包含 id, x, y")


class NodeListResponse(BaseModel):
    """节点列表响应"""
    nodes: List[NodeResponse]
    total: int

