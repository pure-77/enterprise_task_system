from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import BaseModel
from datetime import datetime


class Tag(BaseModel):
    """标签模型 - 面试考点：任务标签管理"""
    __tablename__ = "tags"
    __table_args__ = {'extend_existing': True}
    
    name = Column(String(50), nullable=False, comment="标签名称")
    color = Column(String(20), nullable=False, default="#409EFF", comment="标签颜色")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="用户ID")
    workspace_id = Column(ForeignKey("workspaces.id"), nullable=True, comment="工作空间ID（NULL=个人标签）")

    tasks = relationship("Task", secondary="task_tags", back_populates="tags")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="tags")
    
    def __repr__(self):
        """字符串表示 - 面试考点：便于调试"""
        return f"<Tag(id={self.id}, name={self.name}, color={self.color})>"