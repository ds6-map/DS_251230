"""
FastAPI 应用主入口
校园室内导航系统后端
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from app.core.config import settings
from app.db import init_db, close_db
from app.api import api_router
from app.services import graph_service, ai_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时初始化数据库和服务
    关闭时清理资源
    """
    # 启动时执行
    print("🚀 正在启动应用...")
    
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 初始化数据库
    try:
        await init_db()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"⚠️  数据库初始化失败: {e}")
        if settings.DEBUG:
            print("⚠️  应用将继续运行，但数据库功能可能不可用")
        else:
            raise
    
    # 创建上传目录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"✅ 上传目录已就绪: {settings.UPLOAD_DIR}")
    
    # 加载 AI 模型（Mock 模式）
    await ai_service.load_model()
    print("✅ AI 服务已就绪（Mock 模式）")
    
    print("🎉 应用启动完成!")
    
    yield
    
    # 关闭时执行
    print("👋 正在关闭应用...")
    await close_db()
    print("✅ 数据库连接已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="校园室内导航系统 API",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件（底图文件）
if os.path.exists(settings.UPLOAD_DIR):
    app.mount(
        settings.STATIC_URL_PREFIX,
        StaticFiles(directory=settings.UPLOAD_DIR),
        name="maps"
    )

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")

# 注册 Agent Chat API（无前缀，兼容 add 项目）
from app.api.endpoints import chat
app.include_router(chat.router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用校园室内导航系统 API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }


# 开发模式直接运行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

