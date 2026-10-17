from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from typing import Optional
from app.db.session import get_db
from app.crud.statistics import statistics
from app.utils.excel_exporter import export_tasks_to_excel
from app.api.v1.task import get_current_user_id
from app.services.cache_service import CacheService

router = APIRouter()


@router.get("/overview")
async def get_overview(
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取概览统计 - 带缓存优化（stale-while-revalidate）"""
    # 尝试从缓存读取
    cached = CacheService.get_stats(user_id, workspace_id)
    if cached is not None:
        # 后台异步刷新缓存（不阻塞响应）
        def _refresh(db_session, uid, wid):
            try:
                return statistics.get_overview(db_session, uid, wid)
            except Exception:
                return None

        # 仅在缓存即将过期时触发异步刷新（TTL 过半后）
        CacheService.refresh_stats_async(user_id, workspace_id, _refresh)
        return cached

    # 缓存未命中，查询DB
    result = statistics.get_overview(db, user_id, workspace_id)
    # 回填缓存
    CacheService.set_stats(user_id, result, workspace_id)
    return result


@router.get("/category")
async def get_category_stats(
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取分类统计 - 面试考点：分组查询接口"""
    return statistics.get_category_stats(db, user_id, workspace_id)


@router.get("/status")
async def get_status_stats(
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取状态统计 - 面试考点：分组查询接口"""
    return statistics.get_status_stats(db, user_id, workspace_id)


@router.get("/completion-trend")
async def get_completion_trend(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """"获取完成趋势 - 面试考点：日期分组查询接口"""
    return statistics.get_completion_trend(db, user_id, days, workspace_id)


@router.get("/export/excel")
async def export_tasks_excel(
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出任务到Excel - 面试考点：文件导出接口"""
    tasks = statistics.get_export_data(db, user_id, workspace_id)
    excel_file = export_tasks_to_excel(tasks)
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=tasks_{user_id}.xlsx"}
    )
