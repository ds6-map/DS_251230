"""
地图相关的 Pydantic 模型
用于 API 请求/响应的数据验证
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MapBase(BaseModel):
    """地图基础模型"""
    floor: int = Field(..., description="楼层号")


class MapCreate(MapBase):
    """创建地图时的请求模型（文件上传时使用）"""
    pass


class MapResponse(MapBase):
    """地图响应模型"""
    id: int
    image_url: str = Field(..., description="底图文件URL")
    image_filename: str = Field(..., description="底图文件名")
    width: Optional[int] = Field(None, description="底图宽度(像素)")
    height: Optional[int] = Field(None, description="底图高度(像素)")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MapUploadResponse(BaseModel):
    """地图上传响应"""
    message: str = "上传成功"
    map: MapResponse

