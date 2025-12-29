"""
边模型
存储节点之间的连接关系
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, func
from app.db import Base
import enum


class EdgeType(str, enum.Enum):
    """边类型枚举"""
    NORMAL = "normal"    # 普通走廊
    STAIRS = "stairs"    # 楼梯
    LIFTS = "lifts"      # 电梯


class Edge(Base):
    """
    边表
    存储节点之间的连接关系（双向）
    """
    __tablename__ = "edges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_node_id = Column(
        String(50),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="起点节点ID"
    )
    to_node_id = Column(
        String(50),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="终点节点ID"
    )
    weight = Column(Float, nullable=False, default=1.0, comment="权重（距离）")
    edge_type = Column(
        String(20),
        nullable=False,
        default=EdgeType.NORMAL.value,
        comment="边类型：normal/stairs/lifts"
    )
    is_vertical = Column(Boolean, default=False, comment="是否为垂直移动（楼梯/电梯）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    # 复合索引，加速查询
    __table_args__ = (
        Index('idx_from_to', 'from_node_id', 'to_node_id'),
        Index('idx_to_from', 'to_node_id', 'from_node_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Edge(from={self.from_node_id}, to={self.to_node_id}, weight={self.weight})>"

