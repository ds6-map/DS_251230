"""
导航相关的 Pydantic 模型
用于 API 请求/响应的数据验证
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """导航路径请求模型"""
    start_node_id: str = Field(..., description="起点节点ID")
    target_name: Optional[str] = Field(None, description="目标名称（模糊搜索）")
    target_node_id: Optional[str] = Field(None, description="目标节点ID（精确指定）")


class PathNode(BaseModel):
    """路径中的节点信息"""
    id: str
    name: str
    detail: Optional[str] = None
    floor: int
    x: Optional[float] = None
    y: Optional[float] = None
    node_type: Optional[str] = None


class NavigationStep(BaseModel):
    """导航步骤"""
    step_number: int = Field(..., description="步骤编号")
    instruction: str = Field(..., description="导航指令文字")
    from_node_id: str
    to_node_id: str
    distance: float = Field(..., description="该步距离")
    edge_type: str = Field("normal", description="边类型")
    floor_change: Optional[int] = Field(None, description="楼层变化，正数上楼，负数下楼")


class RouteResponse(BaseModel):
    """导航路径响应模型"""
    success: bool = True
    path: List[str] = Field(..., description="路径节点ID列表")
    path_nodes: List[PathNode] = Field(..., description="路径节点详细信息")
    total_distance: float = Field(..., description="总距离")
    steps: List[NavigationStep] = Field(..., description="分步导航指令")
    floors_involved: List[int] = Field(..., description="涉及的楼层列表")
    message: str = "路径规划成功"


class RouteErrorResponse(BaseModel):
    """导航错误响应"""
    success: bool = False
    message: str
    path: List[str] = []
    path_nodes: List[PathNode] = []
    total_distance: float = 0
    steps: List[NavigationStep] = []
    floors_involved: List[int] = []


class SearchNodeRequest(BaseModel):
    """搜索节点请求"""
    keyword: str = Field(..., description="搜索关键词")


class SearchNodeResponse(BaseModel):
    """搜索节点响应"""
    nodes: List[PathNode]
    total: int

