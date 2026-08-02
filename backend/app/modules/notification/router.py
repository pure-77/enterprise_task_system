"""通知中心模块 — API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.modules.notification.crud import notification_crud, setting_crud
from app.modules.notification.schemas import NotificationReadMark, SettingUpdate

router = APIRouter()


@router.get("/notifications")
async def get_notifications(
    type: str = Query(None, description="按类型筛选"),
    is_read: bool = Query(None, description="按已读状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取通知列表"""
    return notification_crud.get_list(db, current_user.id, type, is_read, page, page_size)


@router.get("/notifications/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取未读通知数量"""
    count = notification_crud.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.post("/notifications/read")
async def mark_notifications_read(
    body: NotificationReadMark,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记通知已读"""
    count = notification_crud.mark_read(db, current_user.id, body.notification_ids)
    return {"marked_count": count}


@router.post("/notifications/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """全部标记已读"""
    count = notification_crud.mark_all_read(db, current_user.id)
    return {"marked_count": count}


# ==================== 通知偏好设置 ====================

@router.get("/settings")
async def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取通知偏好设置"""
    return setting_crud.get_settings(db, current_user.id)


@router.put("/settings/{notif_type}")
async def update_setting(
    notif_type: str,
    body: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新某类通知的偏好设置"""
    setting_crud.update(
        db, current_user.id, notif_type,
        **body.model_dump(exclude_none=True)
    )
    return {"message": "设置已更新"}
