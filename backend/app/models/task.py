from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class TaskStatus(str, enum.Enum):
    """任务状态枚举 - 面试考点：使用枚举类型限制状态值"""
    PENDING = "pending"  # 待办
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    OVERDUE = "overdue"  # 已逾期


class TaskPriority(str, enum.Enum):
    """任务优先级枚举 - 面试考点：使用枚举类型限制优先级值"""
    LOW = "low"  # 低优先级
    MEDIUM = "medium"  # 中优先级
    HIGH = "high"  # 高优先级
    URGENT = "urgent"  # 紧急


class Task(BaseModel):
    """任务模型 - 面试考点：与用户和分类的关联关系"""
    __tablename__ = "tasks"
    __table_args__ = {'extend_existing': True}
    
    title = Column(String(255), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务描述")
    due_date = Column(DateTime, nullable=True, comment="截止日期")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="任务状态")
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, comment="任务优先级")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="用户ID")
    category_id = Column(ForeignKey("categories.id"), nullable=False, comment="分类ID")
    workspace_id = Column(ForeignKey("workspaces.id"), nullable=True, comment="工作空间ID（NULL=个人任务）")
    assignee_id = Column(ForeignKey("users.id"), nullable=True, comment="指派给谁")
    is_team_wide = Column(Boolean, default=False, comment="团队公开任务，全员可见可编辑")

    user = relationship("User", backref="tasks", foreign_keys=[user_id])
    category = relationship("Category", back_populates="tasks", foreign_keys=[category_id])
    tags = relationship("Tag", secondary="task_tags", back_populates="tasks")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_tasks")
    # 多人分配（M2M）
    assignees = relationship("User", secondary="task_assignees", backref="assigned_tasks_m2m")
    
    @property
    def assignee_nickname(self):
        if self.assignee:
            return self.assignee.nickname
        return None

    @property
    def assignee_nicknames(self):
        return [a.nickname or a.email for a in self.assignees] if self.assignees else []

    @property
    def completed_count(self):
        return len(self.completions) if self.completions else 0

    @property
    def total_members(self):
        return getattr(self, '_total_members_cache', 0)

    def __repr__(self):
        """字符串表示 - 面试考点：便于调试"""
        return f"<Task(id={self.id}, title={self.title}, status={self.status}, priority={self.priority}, user_id={self.user_id}, category_id={self.category_id})>"