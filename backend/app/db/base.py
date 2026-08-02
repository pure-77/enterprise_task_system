from datetime import datetime
import pytz
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取当前北京时区时间"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


class BaseModel(Base):
    """模型基类 - 面试考点：所有模型继承此基类，统一公共字段"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    created_at = Column(DateTime, default=get_beijing_time, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time, nullable=False, comment="更新时间")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
