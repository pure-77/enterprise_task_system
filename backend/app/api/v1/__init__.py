from fastapi import APIRouter
from app.api.v1 import auth, profile, websocket
# 任务相关端点（task/category/statistics/tag/backup/workspace/invitation）
# 已迁移至 modules/task/router.py

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(websocket.router, tags=["websocket"])
