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
from app.middleware.static_auth import StaticAuthMiddleware
import logging

logger = logging.getLogger("main")

# 配置日志：缓存相关日志输出到控制台，方便排查
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
# 缓存模块单独设置 INFO 级别
logging.getLogger("cache").setLevel(logging.INFO)

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
# 静态文件认证中间件 — 保护 /uploads 路径
app.add_middleware(StaticAuthMiddleware)

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
from app.modules.agent.router import router as agent_router
from app.modules.knowledge.router import router as knowledge_router

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
# Agent 路由 — 企业办公智能助手
app.include_router(agent_router, prefix="/api/v1/agent")
# 知识库路由 — RAG 索引运维（重建 / 统计）
app.include_router(knowledge_router, prefix="/api/v1/knowledge")

# MCP 工具服务（P1：5 个只读工具对外暴露，开关控制，默认关闭）
if settings.AGENT_MCP_ENABLED:
    from app.modules.agent.mcp.server import build_mcp_asgi
    app.mount(settings.AGENT_MCP_MOUNT_PATH, build_mcp_asgi())

# 挂载静态文件服务 - 用于提供头像等静态文件
import os
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=static_dir), name="uploads")

# 生产镜像：前端 dist 由 Dockerfile 构建后复制到 /app/static，由 FastAPI 同源托管
# 本地开发不设置 FRONTEND_DIST，前端仍走 vite dev server
frontend_dist = os.getenv("FRONTEND_DIST", "")


@app.on_event("startup")
async def startup_event():
    """应用启动事件 - 面试考点：初始化数据库连接"""
    init_db()
    # 启动 Redis 订阅者
    start_redis_subscriber()
    # 初始化 Agent 工具注册
    from app.modules.agent.tools import register_all_tools
    register_all_tools()

    # MCP 工具服务：FastMCP 的 session_manager 必须在父应用生命周期内显式启动
    # （app.mount 不会向子应用传递 lifespan 事件，不启动则 tools/call 全部 500）
    if settings.AGENT_MCP_ENABLED:
        from app.modules.agent.mcp.server import mcp as _mcp_server
        app.state.mcp_session_cm = _mcp_server.session_manager.run()
        await app.state.mcp_session_cm.__aenter__()
        logger.info(f"[MCP] 工具服务 session_manager 已启动，挂载路径 {settings.AGENT_MCP_MOUNT_PATH}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件 - 清理资源"""
    # 关闭 MCP session_manager（若已启动）
    cm = getattr(app.state, "mcp_session_cm", None)
    if cm is not None:
        await cm.__aexit__(None, None, None)
    from app.api.v1.websocket import stop_redis_subscriber
    stop_redis_subscriber()
    # P3: 释放 LangGraph checkpointer（redis saver 的连接）
    from app.modules.agent.graph.checkpointer import close_checkpointer
    await close_checkpointer()


@app.get("/")
async def root():
    """根路径 - 面试考点：健康检查接口"""
    index_file = os.path.join(frontend_dist, "index.html") if frontend_dist else ""
    if index_file and os.path.isfile(index_file):
        from fastapi.responses import FileResponse
        return FileResponse(index_file)
    return {
        "message": "欢迎使用个人任务管理系统",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查 - 面试考点：用于监控和负载均衡"""
    return {"status": "healthy"}


# 前端静态资源与 SPA 兜底（必须注册在所有 API / 健康检查路由之后）
if frontend_dist and os.path.isdir(frontend_dist):
    from fastapi.responses import FileResponse, JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # 注意：不要注册 @app.get("/{full_path:path}") 兜底路由。
    # 它会抢先命中「无尾斜杠的 API 请求」（如 GET /api/v1/categories，而路由是 /api/v1/categories/），
    # 导致本该由 Starlette 自动 307 重定向的请求变成 404/405。
    # 改用 404 异常处理器：路由层未命中才回退首页，API 路径仍返回 JSON 404。
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request, exc):
        path = request.url.path
        api_prefixes = ("/api/", "/uploads/", "/mcp", "/docs", "/redoc", "/openapi.json", "/health")
        if exc.status_code == 404 and request.method in ("GET", "HEAD") and not path.startswith(api_prefixes):
            candidate = os.path.join(frontend_dist, path.lstrip("/"))
            if path != "/" and os.path.isfile(candidate):
                return FileResponse(candidate)
            # Vue Router 使用 history 模式，其余非 API 路径统一返回 index.html
            return FileResponse(os.path.join(frontend_dist, "index.html"))
        return JSONResponse(
            {"detail": exc.detail},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
