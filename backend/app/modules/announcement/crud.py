"""企业公告模块 — CRUD"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.modules.announcement.models import Announcement, AnnouncementRead
from app.core.exceptions import ResourceNotFoundError
from app.db.base import get_beijing_time


class AnnouncementCRUD:

    def get_list(self, db: Session, workspace_id: int, type: str = None,
                 page: int = 1, page_size: int = 20) -> dict:
        q = db.query(Announcement).filter(
            Announcement.workspace_id == workspace_id,
            Announcement.is_active == True
        )
        if type:
            q = q.filter(Announcement.type == type)

        # 置顶优先，然后按时间倒序
        q = q.order_by(desc(Announcement.is_pinned), desc(Announcement.created_at))
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [self._format(a) for a in items],
            "total": total, "page": page, "page_size": page_size
        }

    def get_by_id(self, db: Session, ann_id: int) -> Announcement:
        a = db.query(Announcement).filter(
            Announcement.id == ann_id, Announcement.is_active == True
        ).first()
        if not a:
            raise ResourceNotFoundError(resource="公告")
        return a

    def create(self, db: Session, workspace_id: int, created_by: int,
               title: str, content: str, type: str = "notice",
               is_pinned: bool = False, is_must_read: bool = False,
               publish_at: str = None, expire_at: str = None) -> Announcement:
        from app.modules.announcement.models import AnnouncementType
        try:
            atype = AnnouncementType(type)
        except ValueError:
            atype = AnnouncementType.NOTICE

        a = Announcement(workspace_id=workspace_id, title=title, content=content,
                        type=atype, is_pinned=is_pinned, is_must_read=is_must_read,
                        created_by=created_by)
        if publish_at:
            from datetime import datetime
            a.publish_at = datetime.fromisoformat(publish_at)
        if expire_at:
            from datetime import datetime
            a.expire_at = datetime.fromisoformat(expire_at)

        db.add(a)
        db.commit()
        db.refresh(a)
        return a

    def delete(self, db: Session, ann_id: int) -> Announcement:
        a = self.get_by_id(db, ann_id)
        a.is_active = False
        db.commit()
        return a

    def mark_read(self, db: Session, ann_id: int, user_id: int):
        self.get_by_id(db, ann_id)
        existing = db.query(AnnouncementRead).filter(
            AnnouncementRead.announcement_id == ann_id,
            AnnouncementRead.user_id == user_id
        ).first()
        if not existing:
            db.add(AnnouncementRead(announcement_id=ann_id, user_id=user_id,
                                    read_at=get_beijing_time()))
            db.commit()

    def get_read_status(self, db: Session, ann_id: int) -> dict:
        """获取已读/未读名单"""
        self.get_by_id(db, ann_id)
        reads = db.query(AnnouncementRead).filter(
            AnnouncementRead.announcement_id == ann_id
        ).all()
        return {
            "read_count": len(reads),
            "read_users": [{"user_id": r.user_id, "name": r.user.nickname if r.user else None,
                           "read_at": r.read_at.isoformat() if r.read_at else None}
                          for r in reads]
        }

    def _format(self, a: Announcement) -> dict:
        return {
            "id": a.id, "title": a.title, "content": a.content,
            "type": a.type.value if a.type else "notice",
            "is_pinned": a.is_pinned, "is_must_read": a.is_must_read,
            "creator_name": a.creator.nickname if a.creator else None,
            "publish_at": a.publish_at.isoformat() if a.publish_at else None,
            "expire_at": a.expire_at.isoformat() if a.expire_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }


announcement_crud = AnnouncementCRUD()
