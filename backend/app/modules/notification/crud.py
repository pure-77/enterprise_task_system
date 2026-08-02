"""通知中心模块 — CRUD"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.modules.notification.models import Notification, NotificationSetting
from app.core.exceptions import ResourceNotFoundError
from app.db.base import get_beijing_time


class NotificationCRUD:

    def get_list(self, db: Session, user_id: int, type: str = None,
                 is_read: bool = None, page: int = 1, page_size: int = 20) -> dict:
        query = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_active == True
        )
        if type:
            query = query.filter(Notification.type == type)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        total = query.count()
        items = (
            query.order_by(desc(Notification.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [{
                "id": n.id,
                "type": n.type.value if n.type else None,
                "title": n.title,
                "content": n.content,
                "related_type": n.related_type,
                "related_id": n.related_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            } for n in items],
            "total": total,
            "unread_count": self.get_unread_count(db, user_id),
            "page": page,
            "page_size": page_size
        }

    def get_unread_count(self, db: Session, user_id: int) -> int:
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_active == True
        ).count()

    def create(self, db: Session, user_id: int, type: str, title: str,
               content: str = None, related_type: str = None, related_id: int = None) -> Notification:
        from app.modules.notification.models import NotificationType
        try:
            ntype = NotificationType(type)
        except ValueError:
            ntype = NotificationType.SYSTEM

        notif = Notification(
            user_id=user_id,
            type=ntype,
            title=title,
            content=content,
            related_type=related_type,
            related_id=related_id
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    def mark_read(self, db: Session, user_id: int, notif_ids: list[int] = None) -> int:
        query = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        if notif_ids:
            query = query.filter(Notification.id.in_(notif_ids))

        count = query.count()
        query.update({"is_read": True, "read_at": get_beijing_time()}, synchronize_session=False)
        db.commit()
        return count

    def mark_all_read(self, db: Session, user_id: int) -> int:
        return self.mark_read(db, user_id, notif_ids=None)


class NotificationSettingCRUD:

    def get_settings(self, db: Session, user_id: int) -> dict:
        settings = db.query(NotificationSetting).filter(
            NotificationSetting.user_id == user_id,
            NotificationSetting.is_active == True
        ).all()

        defaults = ["task", "approval", "chat", "calendar", "announcement", "system"]
        result = {}
        for t in defaults:
            existing = next((s for s in settings if s.notification_type == t), None)
            result[t] = {
                "in_app": existing.in_app if existing else True,
                "push": existing.push if existing else False,
                "email": existing.email if existing else False,
            }
        return result

    def update(self, db: Session, user_id: int, notif_type: str, **kwargs) -> NotificationSetting:
        setting = db.query(NotificationSetting).filter(
            NotificationSetting.user_id == user_id,
            NotificationSetting.notification_type == notif_type
        ).first()

        if not setting:
            setting = NotificationSetting(user_id=user_id, notification_type=notif_type)
            db.add(setting)
            db.flush()

        for key, value in kwargs.items():
            if hasattr(setting, key):
                setattr(setting, key, value)

        db.commit()
        db.refresh(setting)
        return setting


notification_crud = NotificationCRUD()
setting_crud = NotificationSettingCRUD()
