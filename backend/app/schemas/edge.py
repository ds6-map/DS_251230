"""
边相关的 Pydantic 模型
用于 API 请求/响应的数据验证
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class EdgeBase(BaseModel):
    """边基础模型"""
    from_node_id: str = Field(..., description="起点节点ID")
    to_node_id: str = Field(..., description="终点节点ID")
    weight: float = Field(1.0, description="权重（距离）")


class EdgeCreate(EdgeBase):
    """创建边请求模型"""
    edge_type: str = Field("normal", description="边类型：normal/stairs/lifts")
    is_vertical: bool = Field(False, description="是否为垂直移动")


class EdgeResponse(EdgeBase):
    """边响应模型"""
    id: int
    edge_type: str
    is_vertical: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class EdgeListResponse(BaseModel):
    """边列表响应"""
    edges: List[EdgeResponse]
    total: int

