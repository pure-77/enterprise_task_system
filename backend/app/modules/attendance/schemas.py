"""考勤模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import time


class RuleCreate(BaseModel):
    workspace_id: int
    name: str = Field(..., max_length=100)
    work_start: time
    work_end: time
    flexible_minutes: int = 0
    work_days: str = "1,2,3,4,5"


class CheckInOut(BaseModel):
    rule_id: int
    remark: Optional[str] = Field(None, max_length=255)
