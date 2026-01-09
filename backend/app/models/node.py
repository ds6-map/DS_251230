"""
节点模型
存储地图上的所有节点信息（教室、楼梯、电梯等）
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, func
from app.db import Base
import enum


class NodeType(str, enum.Enum):
    """节点类型枚举"""
    CLASSROOM = "classroom"      # 教室
    STAIRS = "stairs"            # 楼梯
    LIFT = "lift"                # 电梯
    CORRIDOR = "corridor"        # 走廊
    RESTROOM = "restroom"        # 洗手间
    ENTRANCE = "entrance"        # 入口
    OTHER = "other"              # 其他


class Node(Base):
    """
    节点表
    存储地图上的所有节点信息
    """
    __tablename__ = "nodes"
    
    id = Column(String(50), primary_key=True, comment="节点唯一标识，如 LT5")
    name = Column(String(100), nullable=False, index=True, comment="节点名称，如 LectureTheater5")
    detail = Column(String(200), nullable=True, comment="详细位置描述，如 NS2-02-07")
    floor = Column(Integer, nullable=False, index=True, comment="所在楼层")
    x = Column(Float, nullable=True, comment="X坐标（像素，相对于底图）")
    y = Column(Float, nullable=True, comment="Y坐标（像素，相对于底图）")
    node_type = Column(
        String(20),
        nullable=True,
        default=NodeType.OTHER.value,
        comment="节点类型"
    )
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<Node(id={self.id}, name={self.name}, floor={self.floor})>"
    
    @property
    def has_coordinates(self) -> bool:
        """检查节点是否已设置坐标"""
        return self.x is not None and self.y is not None

