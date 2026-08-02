"""任务模块路由 — 聚合所有现有 API 端点"""
from fastapi import APIRouter
from app.api.v1 import task as task_endpoints
from app.api.v1 import category as category_endpoints
from app.api.v1 import statistics as statistics_endpoints
from app.api.v1 import tag as tag_endpoints
from app.api.v1 import backup as backup_endpoints
from app.api.v1 import workspace as workspace_endpoints
from app.api.v1 import invitation as invitation_endpoints

task_router = APIRouter()

task_router.include_router(task_endpoints.router, prefix="/tasks", tags=["tasks"])
task_router.include_router(category_endpoints.router, prefix="/categories", tags=["categories"])
task_router.include_router(statistics_endpoints.router, prefix="/statistics", tags=["statistics"])
task_router.include_router(tag_endpoints.router, prefix="/tags", tags=["tags"])
task_router.include_router(backup_endpoints.router, prefix="/backup", tags=["backup"])
task_router.include_router(workspace_endpoints.router, prefix="/workspaces", tags=["workspaces"])
task_router.include_router(invitation_endpoints.router, prefix="/invitations", tags=["invitations"])
