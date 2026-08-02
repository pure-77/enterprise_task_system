"""考勤模块 — API 路由"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.modules.attendance.crud import attendance_crud
from app.modules.attendance.schemas import RuleCreate, CheckInOut

router = APIRouter()


def _require_admin(workspace_id: int, user_id: int, db: Session):
    member = get_workspace_member(workspace_id, user_id, db)
    if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="需要管理员权限")


@router.get("/rules")
async def get_rules(
    workspace_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    rules = attendance_crud.get_rules(db, workspace_id)
    return [{"id": r.id, "name": r.name,
             "work_start": r.work_start.isoformat() if r.work_start else None,
             "work_end": r.work_end.isoformat() if r.work_end else None,
             "flexible_minutes": r.flexible_minutes, "work_days": r.work_days}
            for r in rules]


@router.post("/rules", status_code=201)
async def create_rule(
    body: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(body.workspace_id, current_user.id, db)
    r = attendance_crud.create_rule(db, body.workspace_id, body.name,
                                    body.work_start, body.work_end,
                                    body.flexible_minutes, body.work_days)
    return {"id": r.id, "name": r.name}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    r = attendance_crud.get_rule(db, rule_id)
    _require_admin(r.workspace_id, current_user.id, db)
    attendance_crud.delete_rule(db, rule_id)
    return {"message": "规则已删除"}


@router.post("/check-in")
async def check_in(
    body: CheckInOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rec = attendance_crud.check_in(db, current_user.id, body.rule_id, body.remark)
    return {"id": rec.id, "date": rec.date.isoformat() if rec.date else None,
            "check_in_time": rec.check_in_time.isoformat() if rec.check_in_time else None,
            "check_in_type": rec.check_in_type.value if rec.check_in_type else None}


@router.post("/check-out")
async def check_out(
    body: CheckInOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rec = attendance_crud.check_out(db, current_user.id, body.rule_id, body.remark)
    return {"id": rec.id, "date": rec.date.isoformat() if rec.date else None,
            "check_out_time": rec.check_out_time.isoformat() if rec.check_out_time else None,
            "check_out_type": rec.check_out_type.value if rec.check_out_type else None}


@router.get("/records")
async def get_records(
    rule_id: int = Query(...),
    start_date: str = Query(None),
    end_date: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(31, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    return attendance_crud.get_records(db, current_user.id, rule_id, sd, ed, page, page_size)


@router.get("/stats")
async def get_stats(
    rule_id: int = Query(...),
    period_start: str = Query(None, description="YYYY-MM-DD, 默认当月1号"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ps = date.fromisoformat(period_start) if period_start else None
    return attendance_crud.get_my_stats(db, current_user.id, rule_id, ps)


@router.get("/today")
async def get_today_status(
    rule_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取今日打卡状态"""
    from datetime import date as dt_date
    from app.modules.attendance.models import AttendanceRecord
    today = dt_date.today()
    rec = db.query(AttendanceRecord).filter(
        AttendanceRecord.user_id == current_user.id,
        AttendanceRecord.rule_id == rule_id,
        AttendanceRecord.date == today
    ).first()
    if not rec:
        return {"checked_in": False, "checked_out": False}
    return {
        "checked_in": rec.check_in_time is not None,
        "checked_out": rec.check_out_time is not None,
        "check_in_time": rec.check_in_time.isoformat() if rec.check_in_time else None,
        "check_out_time": rec.check_out_time.isoformat() if rec.check_out_time else None,
        "check_in_type": rec.check_in_type.value if rec.check_in_type else None,
    }
