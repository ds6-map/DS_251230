"""
地图底图模型
存储每个楼层的底图信息
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.db import Base


class Map(Base):
    """
    地图底图表
    每个楼层对应一张底图
    """
    __tablename__ = "maps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    floor = Column(Integer, nullable=False, unique=True, index=True, comment="楼层号")
    image_url = Column(String(500), nullable=False, comment="底图文件URL")
    image_filename = Column(String(255), nullable=False, comment="底图文件名")
    width = Column(Integer, nullable=True, comment="底图宽度(像素)")
    height = Column(Integer, nullable=True, comment="底图高度(像素)")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<Map(floor={self.floor}, image_url={self.image_url})>"

