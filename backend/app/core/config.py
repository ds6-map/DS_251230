"""
全局配置模块
使用 pydantic-settings 管理环境变量和配置
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import sys
from pathlib import Path


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
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB (允许高分辨率图片)
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "webp"}
    
    # 静态文件 URL 前缀
    STATIC_URL_PREFIX: str = "/static/maps"
    
    # CORS 配置
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # AI 服务配置 (Mock 模式)
    AI_MOCK_MODE: bool = True
    CLIP_MODEL_NAME: str = "openai/clip-vit-base-patch32"
    
    # Agent Chat 配置 (来自 add 项目)
    OPENAI_API_KEY: Optional[str] = ""
    OPENAI_API_BASE: Optional[str] = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GMAPS_API_KEY: Optional[str] = ""
    DEFAULT_ORIGIN: str = "Nanyang Technological University, Singapore"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()

# 尝试从 key.py 加载密钥（兼容 add 项目）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PARENT_ROOT = _PROJECT_ROOT.parent
for _p in (str(_PROJECT_ROOT), str(_PARENT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 缓存从 key.py 读取的密钥
_cached_openai_key = None
_cached_gmaps_key = None
_cached_openai_base = None

def _get_api_keys():
    """从 key.py 读取密钥（如果存在）"""
    global _cached_openai_key, _cached_gmaps_key, _cached_openai_base
    if _cached_openai_key is not None and _cached_gmaps_key is not None:
        return _cached_openai_key, _cached_gmaps_key, _cached_openai_base
    
    _cached_openai_base = None
    try:
        from key import openai_api_key as _openai_api_key  # type: ignore
        from key import google_api_key as _google_api_key  # type: ignore
        _cached_openai_key = _openai_api_key or ""
        _cached_gmaps_key = _google_api_key or ""
        # 尝试读取 base_url（如果存在）
        try:
            from key import base_url as _base_url  # type: ignore
            _cached_openai_base = _base_url or None
        except (ImportError, AttributeError):
            _cached_openai_base = None
    except Exception:
        _cached_openai_key = ""
        _cached_gmaps_key = ""
        _cached_openai_base = None
    
    return _cached_openai_key, _cached_gmaps_key, _cached_openai_base


# Agent Chat 辅助函数（来自 add 项目）
def get_openai_client():
    """获取 OpenAI 客户端"""
    try:
        from openai import OpenAI
        api_key = settings.OPENAI_API_KEY or ""
        base_url = settings.OPENAI_API_BASE or ""
        
        if not api_key or not base_url:
            # 尝试从 key.py 读取
            key_from_file, _, base_from_file = _get_api_keys()
            if not api_key:
                api_key = key_from_file
            if not base_url and base_from_file:
                base_url = base_from_file
        
        if not api_key:
            return None
        
        return OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    except ImportError:
        return None
    except Exception as e:
        if settings.DEBUG:
            print(f"Failed to create OpenAI client: {e}")
        return None


def get_gmaps_client():
    """获取 Google Maps 客户端"""
    try:
        import googlemaps
        api_key = settings.GMAPS_API_KEY or ""
        if not api_key:
            # 尝试从 key.py 读取
            api_key, _, _ = _get_api_keys()
        if not api_key:
            return None
        return googlemaps.Client(key=api_key)
    except ImportError:
        return None
    except Exception as e:
        if settings.DEBUG:
            print(f"Failed to create GMaps client: {e}")
        return None

