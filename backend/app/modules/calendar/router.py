"""日程日历模块 — API 路由"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.modules.calendar.crud import event_crud
from app.modules.calendar.schemas import EventCreate, EventUpdate, AttendeeUpdate

router = APIRouter()


@router.get("/events")
async def get_events(
    workspace_id: int = Query(None),
    start: str = Query(None, description="开始日期 ISO"),
    end: str = Query(None, description="结束日期 ISO"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取时间范围内的事件 — 重复事件自动展开"""
    get_workspace_member(workspace_id, current_user.id, db)

    if not start:
        start_dt = datetime.now().replace(day=1)
    else:
        start_dt = datetime.fromisoformat(start)
    if not end:
        end_dt = start_dt + timedelta(days=42)
    else:
        end_dt = datetime.fromisoformat(end)

    events = event_crud.get_events(db, workspace_id, current_user.id, start_dt, end_dt)
    return events


@router.post("/events", status_code=201)
async def create_event(
    ev_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建日程事件"""
    get_workspace_member(ev_in.workspace_id, current_user.id, db)

    ev = event_crud.create(
        db, ev_in.workspace_id, current_user.id,
        title=ev_in.title,
        start_time=ev_in.start_time,
        end_time=ev_in.end_time,
        description=ev_in.description,
        location=ev_in.location,
        is_all_day=ev_in.is_all_day,
        color=ev_in.color,
        event_type=ev_in.event_type,
        task_id=ev_in.task_id,
        recurrence_rule=ev_in.recurrence_rule,
        attendee_ids=ev_in.attendee_ids,
        remind_minutes=ev_in.remind_minutes
    )
    return event_crud._format(ev)


@router.put("/events/{event_id}")
async def update_event(
    event_id: int,
    ev_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新事件"""
    ev = event_crud.get_by_id(db, event_id)
    if ev.created_by != current_user.id:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="只能编辑自己创建的日程")
    ev = event_crud.update(db, event_id, **ev_in.model_dump(exclude_none=True))
    return event_crud._format(ev)


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除事件"""
    ev = event_crud.get_by_id(db, event_id)
    if ev.created_by != current_user.id:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="只能删除自己创建的日程")
    event_crud.delete(db, event_id)
    return {"message": "日程已删除"}


@router.put("/events/{event_id}/attendees")
async def update_attendee_status(
    event_id: int,
    body: AttendeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新参与状态 — 接受/拒绝/待定"""
    att = event_crud.update_attendee_status(db, event_id, current_user.id, body.status)
    return {"status": att.status.value}
