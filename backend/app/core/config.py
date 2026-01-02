"""
全局配置模块
使用 pydantic-settings 管理环境变量和配置
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "Campus Indoor Navigation"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置 (SQLite - 无需安装，文件数据库)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/campus_nav.db"
    
    # 文件存储配置
    UPLOAD_DIR: str = "data/maps"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg"}
    
    # 静态文件 URL 前缀
    STATIC_URL_PREFIX: str = "/static/maps"
    
    # CORS 配置
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # AI 服务配置 (Mock 模式)
    AI_MOCK_MODE: bool = True
    CLIP_MODEL_NAME: str = "openai/clip-vit-base-patch32"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()

