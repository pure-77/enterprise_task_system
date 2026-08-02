"""OA审批模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional


class TemplateCreate(BaseModel):
    workspace_id: int
    name: str = Field(..., min_length=1, max_length=100)
    form_schema: dict = Field(..., description="表单字段定义")
    flow_schema: dict = Field(..., description="审批流程定义")
    category: str = Field("custom", description="leave/expense/travel/overtime/custom")
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)


class ApprovalSubmit(BaseModel):
    template_id: int
    title: str = Field(..., min_length=1, max_length=255)
    form_data: dict = Field(default_factory=dict)


class ApprovalAction(BaseModel):
    node_id: int
    comment: Optional[str] = Field(None, max_length=500)


class TransferAction(BaseModel):
    node_id: int
    to_user_id: int


class CCAdd(BaseModel):
    user_ids: list[int]
