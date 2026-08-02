from sqlalchemy import Column, String, DateTime
from app.db.base import BaseModel


class User(BaseModel):
    """用户模型 - 面试考点：继承BaseModel，包含公共字段"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    email = Column(String(255), unique=True, index=True, nullable=False, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="加密密码")
    nickname = Column(String(100), nullable=False, comment="昵称")
    avatar = Column(String(500), nullable=True, comment="头像URL")
    real_name = Column(String(50), nullable=True, comment="真实姓名")
    mobile = Column(String(20), nullable=True, comment="手机号")
    avatar_thumb = Column(String(500), nullable=True, comment="头像缩略图URL")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip = Column(String(45), nullable=True, comment="最后登录IP")
    
    def __repr__(self):
        """字符串表示 - 面试考点：便于调试"""
        return f"<User(id={self.id}, email={self.email}, nickname={self.nickname})>"
