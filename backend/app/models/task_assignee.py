""""任务多人分配中间表"""
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Table, func, Index
from app.db.base import Base

task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, comment="自增ID"),
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="任务ID"),
    Column("user_id", ForeignKey("users.id"), nullable=False, comment="被分配人ID"),
    Column("created_at", DateTime, default=func.now(), server_default=func.now(), comment="创建时间"),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now(), server_default=func.now(), comment="更新时间"),
    Column("is_active", Boolean, default=True, server_default="1", comment="是否激活"),
    Index('ix_task_assignees_task_id', 'task_id'),
    Index('ix_task_assignees_user_id', 'user_id'),
    Index('ix_task_assignees_task_user', 'task_id', 'user_id'),
)
