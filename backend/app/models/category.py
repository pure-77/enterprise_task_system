from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import BaseModel


class Category(BaseModel):
    """分类模型 - 面试考点：与用户和任务的关联关系"""
    __tablename__ = "categories"
    __table_args__ = {'extend_existing': True}
    
    name = Column(String(100), nullable=False, comment="分类名称")
    color = Column(String(20), nullable=False, comment="分类颜色")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="用户ID")
    workspace_id = Column(ForeignKey("workspaces.id"), nullable=True, comment="工作空间ID（NULL=个人分类）")

    user = relationship("User", backref="categories", foreign_keys=[user_id])
    tasks = relationship("Task", back_populates="category", cascade="all, delete-orphan")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="categories")
    
    def __repr__(self):
        """字符串表示 - 面试考点：便于调试"""
        return f"<Category(id={self.id}, name={self.name}, color={self.color}, user_id={self.user_id})>"