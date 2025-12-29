from fastapi import APIRouter
from .endpoints import navigation, recognition, maps

# 创建主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(navigation.router)
api_router.include_router(recognition.router)
api_router.include_router(maps.router)

