"""日程日历模块 — CRUD 操作"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.modules.calendar.models import (
    Event, EventAttendee, EventReminder,
    EventType, AttendeeStatus, ReminderMethod
)
from app.modules.calendar.recurrence import parse_recurrence
from app.core.exceptions import ResourceNotFoundError, BusinessError
from app.db.base import get_beijing_time


class EventCRUD:

    def get_events(self, db: Session, workspace_id: int, user_id: int,
                   start: datetime, end: datetime) -> list[dict]:
        """获取时间范围内的所有事件（含重复事件展开）"""
        # 基础查询：用户创建的 + 被邀请参与的
        base_events = db.query(Event).filter(
            Event.is_active == True,
            Event.workspace_id == workspace_id,
            or_(
                Event.created_by == user_id,
                Event.attendees.any(EventAttendee.user_id == user_id)
            )
        ).filter(
            or_(
                # 单次事件在范围内
                and_(Event.recurrence_rule.is_(None),
                     Event.start_time < end,
                     Event.end_time > start),
                # 重复事件：取截止时间 > start 的
                and_(Event.recurrence_rule.isnot(None),
                     Event.start_time < end)
            )
        ).all()

        result = []
        for ev in base_events:
            if ev.recurrence_rule:
                # 展开重复事件
                occurrences = parse_recurrence(
                    ev.recurrence_rule, ev.start_time, end
                )
                duration = ev.end_time - ev.start_time
                for occ in occurrences:
                    if occ >= start and occ <= end:
                        result.append(self._format(ev, occ, occ + duration))
            else:
                result.append(self._format(ev))

        result.sort(key=lambda x: x["start_time"])
        return result

    def get_by_id(self, db: Session, event_id: int) -> Event:
        ev = db.query(Event).filter(
            Event.id == event_id, Event.is_active == True
        ).first()
        if not ev:
            raise ResourceNotFoundError(resource="日程")
        return ev

    def create(self, db: Session, workspace_id: int, created_by: int,
               title: str, start_time: datetime, end_time: datetime,
               description: str = None, location: str = None,
               is_all_day: bool = False, color: str = None,
               event_type: str = "normal", task_id: int = None,
               recurrence_rule: str = None,
               attendee_ids: list[int] = None,
               remind_minutes: list[int] = None) -> Event:
        try:
            etype = EventType(event_type)
        except ValueError:
            etype = EventType.NORMAL

        ev = Event(
            workspace_id=workspace_id,
            title=title,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            color=color,
            type=etype,
            task_id=task_id,
            recurrence_rule=recurrence_rule,
            created_by=created_by
        )
        db.add(ev)
        db.flush()

        for uid in (attendee_ids or []):
            db.add(EventAttendee(event_id=ev.id, user_id=uid))

        for mins in (remind_minutes or []):
            remind_at = start_time - timedelta(minutes=mins)
            db.add(EventReminder(event_id=ev.id, remind_at=remind_at,
                                 method=ReminderMethod.NOTIFICATION))

        db.commit()
        db.refresh(ev)
        return ev

    def update(self, db: Session, event_id: int, **kwargs) -> Event:
        ev = self.get_by_id(db, event_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(ev, k):
                setattr(ev, k, v)
        db.commit()
        db.refresh(ev)
        return ev

    def delete(self, db: Session, event_id: int) -> Event:
        ev = self.get_by_id(db, event_id)
        ev.is_active = False
        db.commit()
        return ev

    def update_attendee_status(self, db: Session, event_id: int,
                               user_id: int, status: str) -> EventAttendee:
        att = db.query(EventAttendee).filter(
            EventAttendee.event_id == event_id,
            EventAttendee.user_id == user_id
        ).first()
        if not att:
            raise ResourceNotFoundError(resource="参与人记录")
        try:
            att.status = AttendeeStatus(status)
        except ValueError:
            raise BusinessError(f"无效的状态: {status}")
        db.commit()
        db.refresh(att)
        return att

    def _format(self, ev: Event, start_override: datetime = None,
                end_override: datetime = None) -> dict:
        attendees = []
        for a in ev.attendees:
            attendees.append({
                "user_id": a.user_id,
                "name": a.user.nickname if a.user else None,
                "status": a.status.value
            })

        return {
            "id": ev.id,
            "title": ev.title,
            "description": ev.description,
            "location": ev.location,
            "start_time": (start_override or ev.start_time).isoformat(),
            "end_time": (end_override or ev.end_time).isoformat(),
            "is_all_day": ev.is_all_day,
            "color": ev.color,
            "type": ev.type.value if ev.type else "normal",
            "recurrence_rule": ev.recurrence_rule,
            "creator_name": ev.creator.nickname if ev.creator else None,
            "attendees": attendees,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }


event_crud = EventCRUD()
