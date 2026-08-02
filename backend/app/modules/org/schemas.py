"""组织架构模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ---------- Department ----------
class DepartmentCreate(BaseModel):
    workspace_id: int = Field(..., description="工作空间ID")
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    parent_id: Optional[int] = Field(None, description="父部门ID")
    leader_id: Optional[int] = Field(None, description="部门负责人ID")
    sort_order: int = Field(0, description="排序序号")


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    leader_id: Optional[int] = None
    sort_order: Optional[int] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    sort_order: int = 0
    path: Optional[str] = None
    member_count: int = 0
    children: Optional[list["DepartmentResponse"]] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- Position ----------
class PositionCreate(BaseModel):
    workspace_id: int
    name: str = Field(..., min_length=1, max_length=50)
    sort_order: int = 0


class PositionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = None


class PositionResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    sort_order: int = 0
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- Member ----------
class MemberUpdate(BaseModel):
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    employee_no: Optional[str] = Field(None, max_length=50)
    real_name: Optional[str] = Field(None, max_length=50)
    mobile: Optional[str] = Field(None, max_length=20)
    join_date: Optional[date] = None
    status: Optional[str] = None


class MemberResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: int
    role: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    employee_no: Optional[str] = None
    real_name: Optional[str] = None
    email: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    mobile: Optional[str] = None
    join_date: Optional[str] = None
    status: str = "active"

    model_config = {"from_attributes": True}
