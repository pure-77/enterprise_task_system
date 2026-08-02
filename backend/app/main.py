from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.db.session import init_db
from app.api.v1 import api_router
from app.core.celery_config import celery_app
from app.api.v1.websocket import start_redis_subscriber
from app.middleware.response_handler import ResponseHandlerMiddleware
from app.middleware.audit_log import AuditLogMiddleware

# 创建FastAPI应用实例 - 面试考点：应用配置和元数据
app = FastAPI(
    title=settings.APP_NAME,
    description="个人任务管理系统API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 统一响应格式中间件
app.add_middleware(ResponseHandlerMiddleware)
# 审计日志中间件
app.add_middleware(AuditLogMiddleware)

# 配置CORS中间件 — 必须最后添加（最外层），确保异常响应也携带 CORS 头
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 - 模块化路由管理
from app.modules.task.router import task_router
from app.modules.org.router import router as org_router
from app.modules.im.router import router as im_router
from app.modules.notification.router import router as notification_router
from app.modules.approval.router import router as approval_router
from app.modules.calendar.router import router as calendar_router
from app.modules.attendance.router import router as attendance_router
from app.modules.announcement.router import router as announcement_router
from app.modules.file.router import router as file_router

app.include_router(api_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1/org")
app.include_router(im_router, prefix="/api/v1/im")
app.include_router(notification_router, prefix="/api/v1/notification")
app.include_router(approval_router, prefix="/api/v1/approval")
app.include_router(calendar_router, prefix="/api/v1/calendar")
app.include_router(attendance_router, prefix="/api/v1/attendance")
app.include_router(announcement_router, prefix="/api/v1/announcements")
app.include_router(file_router, prefix="/api/v1/files")

# 挂载静态文件服务 - 用于提供头像等静态文件
import os
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=static_dir), name="uploads")


@app.on_event("startup")
async def startup_event():
    """应用启动事件 - 面试考点：初始化数据库连接"""
    init_db()
    # 启动 Redis 订阅者
    start_redis_subscriber()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件 - 清理资源"""
    from app.api.v1.websocket import stop_redis_subscriber
    stop_redis_subscriber()


@app.get("/")
async def root():
    """根路径 - 面试考点：健康检查接口"""
    return {
        "message": "欢迎使用个人任务管理系统",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查 - 面试考点：用于监控和负载均衡"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
