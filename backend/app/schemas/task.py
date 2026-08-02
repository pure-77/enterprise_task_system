from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.task import TaskStatus, TaskPriority
# FastAPI 的 Pydantic，本质上就是“更现代、更轻量、更类型化”的序列化器
# Python 世界里的数据结构 + 数据校验器
# JSON -> Python对象
# Python对象 -> JSON
class TaskBase(BaseModel):
    """任务基础模型 - 面试考点：Pydantic模型用于数据验证"""
    title: str = Field(..., min_length=1, max_length=255, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    category_id: int = Field(..., description="分类ID")
    tags: Optional[List[int]] = Field(None, description="标签ID列表")
    workspace_id: Optional[int] = Field(None, description="工作空间ID（NULL=个人任务）")
    assignee_id: Optional[int] = Field(None, description="指派给谁（单人）")
    assignee_ids: Optional[List[int]] = Field(None, description="指派给多人（ID列表）")
    is_team_wide: bool = Field(False, description="团队公开任务，全员可见可编辑")


class TaskCreate(TaskBase):
    """创建任务模型 - 面试考点：继承基础模型"""
    pass


class TaskUpdate(BaseModel):
    """更新任务模型 - 面试考点：所有字段可选"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    category_id: Optional[int] = Field(None, description="分类ID")
    tags: Optional[List[int]] = Field(None, description="标签ID列表")
    assignee_id: Optional[int] = Field(None, description="指派给谁")
    is_team_wide: Optional[bool] = Field(None, description="团队公开任务")
    assignee_ids: Optional[List[int]] = Field(None, description="指派给多人")


class TagResponse(BaseModel):
    """标签响应模型"""
    id: int
    name: str
    color: str
    
    class Config:
        from_attributes = True


class CompletionUser(BaseModel):
    """完成记录中的用户信息"""
    user_id: int
    nickname: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskResponse(TaskBase):
    """任务响应模型"""
    id: int
    status: TaskStatus
    user_id: int
    workspace_id: Optional[int] = None
    assignee_id: Optional[int] = None
    assignee_nickname: Optional[str] = None
    assignee_nicknames: Optional[List[str]] = []  # 多人分配名称
    is_team_wide: bool = False
    created_at: datetime
    updated_at: datetime
    # category_id: Optional[int] = None
    is_active: bool
    tags: Optional[List[TagResponse]] = []
    # 团队任务完成追踪
    completions: Optional[List[CompletionUser]] = []  # 已完成成员列表
    total_members: Optional[int] = 0  # workspace 总成员数
    completed_count: Optional[int] = 0  # 已完成人数

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应模型 - 面试考点：分页数据结构"""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskStatusUpdate(BaseModel):
    """任务状态更新模型 - 面试考点：专门用于状态更新"""
    status: TaskStatus = Field(..., description="任务状态")


class TaskBatchUpdate(BaseModel):
    """任务批量更新模型 - 面试考点：批量操作"""
    task_ids: list[int] = Field(..., description="任务ID列表")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    category_id: Optional[int] = Field(None, description="分类ID")


class TaskFilter(BaseModel):
    """任务筛选模型 - 面试考点：查询条件封装"""
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    category_id: Optional[int] = Field(None, description="分类ID")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    due_date_start: Optional[datetime] = Field(None, description="截止日期开始")
    due_date_end: Optional[datetime] = Field(None, description="截止日期结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")