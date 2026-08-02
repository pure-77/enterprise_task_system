from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from typing import List, Optional
from app.db.session import get_db
from app.crud.statistics import statistics
from app.utils.excel_exporter import export_tasks_to_excel
from app.api.v1.task import get_current_user_id

router = APIRouter()


@router.get("/overview")
async def get_overview(
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取概览统计 - 面试考点：聚合查询接口"""
    return statistics.get_overview(db, user_id, workspace_id)


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