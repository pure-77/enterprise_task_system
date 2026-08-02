""""每个成员完成团队公开任务的记录"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import BaseModel


class TaskCompletion(BaseModel):
    __tablename__ = "task_completions"
    __table_args__ = {'extend_existing': True}

    task_id = Column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="完成人ID")
    completed_at = Column(DateTime, server_default=func.now(), comment="完成时间")

    task = relationship("Task", backref="completions")
    user = relationship("User")
