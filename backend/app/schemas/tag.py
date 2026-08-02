from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TagBase(BaseModel):
    """标签基础模型 - 面试考点：Pydantic模型用于数据验证"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    color: str = Field("#409EFF", description="标签颜色")


class TagCreate(TagBase):
    """创建标签模型 - 面试考点：继承基础模型"""
    pass


class TagUpdate(BaseModel):
    """更新标签模型 - 面试考点：所有字段可选"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="标签名称")
    color: Optional[str] = Field(None, description="标签颜色")


class TagResponse(TagBase):
    """标签响应模型 - 面试考点：包含ID和创建时间"""
    id: int
    user_id: int
    workspace_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True