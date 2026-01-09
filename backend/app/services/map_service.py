"""
地图服务模块
处理底图文件上传和管理
"""
import os
import uuid
import aiofiles
from typing import Optional, Tuple
from PIL import Image
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Map
from app.core.config import settings


class MapService:
    """
    地图服务类
    管理底图文件的上传、存储和查询
    """
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self) -> None:
        """确保上传目录存在"""
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名"""
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    def _is_allowed_file(self, filename: str) -> bool:
        """检查文件类型是否允许"""
        ext = self._get_file_extension(filename)
        return ext in settings.ALLOWED_EXTENSIONS
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """生成唯一文件名"""
        ext = self._get_file_extension(original_filename)
        unique_id = uuid.uuid4().hex[:12]
        return f"{unique_id}.{ext}"
    
    async def get_image_dimensions(self, file_content: bytes) -> Tuple[int, int]:
        """
        获取图片尺寸
        
        Args:
            file_content: 文件二进制内容
            
        Returns:
            (width, height)
        """
        image = Image.open(io.BytesIO(file_content))
        return image.size
    
    async def save_map_file(
        self,
        file_content: bytes,
        original_filename: str,
        floor: int,
        db: AsyncSession
    ) -> Map:
        """
        保存底图文件
        
        Args:
            file_content: 文件二进制内容
            original_filename: 原始文件名
            floor: 楼层号
            db: 数据库会话
            
        Returns:
            Map 对象
            
        Raises:
            ValueError: 文件类型不支持或文件过大
        """
        # 验证文件类型
        if not self._is_allowed_file(original_filename):
            raise ValueError(f"不支持的文件类型。允许的类型: {settings.ALLOWED_EXTENSIONS}")
        
        # 验证文件大小
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise ValueError(f"文件过大。最大允许: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")
        
        # 获取图片尺寸
        try:
            width, height = await self.get_image_dimensions(file_content)
        except Exception as e:
            raise ValueError(f"无法读取图片信息: {str(e)}")
        
        # 生成唯一文件名
        unique_filename = self._generate_unique_filename(original_filename)
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        # 保存文件
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        # 生成 URL
        image_url = f"{settings.STATIC_URL_PREFIX}/{unique_filename}"
        
        # 检查该楼层是否已有底图
        result = await db.execute(select(Map).where(Map.floor == floor))
        existing_map = result.scalar_one_or_none()
        
        if existing_map:
            # 删除旧文件
            old_file_path = os.path.join(
                self.upload_dir,
                existing_map.image_filename
            )
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # 更新记录
            existing_map.image_url = image_url
            existing_map.image_filename = unique_filename
            existing_map.width = width
            existing_map.height = height
            await db.commit()
            await db.refresh(existing_map)
            return existing_map
        else:
            # 创建新记录
            new_map = Map(
                floor=floor,
                image_url=image_url,
                image_filename=unique_filename,
                width=width,
                height=height,
            )
            db.add(new_map)
            await db.commit()
            await db.refresh(new_map)
            return new_map
    
    async def get_map_by_floor(self, floor: int, db: AsyncSession) -> Optional[Map]:
        """
        获取指定楼层的底图
        
        Args:
            floor: 楼层号
            db: 数据库会话
            
        Returns:
            Map 对象或 None
        """
        result = await db.execute(select(Map).where(Map.floor == floor))
        return result.scalar_one_or_none()
    
    async def get_all_maps(self, db: AsyncSession) -> list:
        """
        获取所有底图
        
        Args:
            db: 数据库会话
            
        Returns:
            Map 列表
        """
        result = await db.execute(select(Map).order_by(Map.floor))
        return result.scalars().all()
    
    async def delete_map(self, floor: int, db: AsyncSession) -> bool:
        """
        删除指定楼层的底图
        
        Args:
            floor: 楼层号
            db: 数据库会话
            
        Returns:
            是否删除成功
        """
        result = await db.execute(select(Map).where(Map.floor == floor))
        map_obj = result.scalar_one_or_none()
        
        if not map_obj:
            return False
        
        # 删除文件
        file_path = os.path.join(self.upload_dir, map_obj.image_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 删除数据库记录
        await db.delete(map_obj)
        await db.commit()
        return True


# 全局单例
map_service = MapService()

