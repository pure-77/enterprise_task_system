"""每个成员完成团队公开任务的记录"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.db.base import BaseModel


class TaskCompletion(BaseModel):
    __tablename__ = "task_completions"
    __table_args__ = {'extend_existing': True}

    task_id = Column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="完成人ID")
    completed_at = Column(DateTime, server_default=func.now(), comment="完成时间")

    # cascade+passive_deletes：删除任务时级联删掉完成记录（DB 层 ON DELETE CASCADE 兜底），
    # 否则 SQLAlchemy 默认行为是把 task_id 置 NULL，被非空约束拒绝导致 500
    task = relationship("Task", backref=backref("completions", cascade="all, delete-orphan", passive_deletes=True))
    user = relationship("User")
