from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """分类基础模型 - 面试考点：定义公共字段"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    color: str = Field(..., min_length=1, max_length=20, description="分类颜色")


class CategoryCreate(CategoryBase):
    """分类创建模型 - 面试考点：创建分类时的数据验证"""
    @validator('name')
    def name_not_empty(cls, v):
        """验证分类名称不能为空 - 面试考点：自定义验证器"""
        if not v or not v.strip():
            raise ValueError('分类名称不能为空')
        return v


class CategoryUpdate(BaseModel):
    """分类更新模型 - 面试考点：部分字段可选"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="分类名称")
    color: Optional[str] = Field(None, min_length=1, max_length=20, description="分类颜色")
    
    @validator('name')
    def name_not_empty(cls, v):
        """验证分类名称不能为空 - 面试考点：自定义验证器"""
        if v and not v.strip():
            raise ValueError('分类名称不能为空')
        return v


class CategoryResponse(CategoryBase):
    """分类响应模型 - 面试考点：返回给前端的数据"""
    id: int
    user_id: int
    workspace_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # 面试考点：支持ORM模型转换


class CategoryWithTaskCount(CategoryResponse):
    """带任务数量的分类响应模型 - 面试考点：扩展响应模型"""
    task_count: int = 0  # 任务数量