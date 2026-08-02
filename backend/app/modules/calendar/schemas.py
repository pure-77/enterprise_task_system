"""日程日历模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EventCreate(BaseModel):
    workspace_id: int
    title: str = Field(..., min_length=1, max_length=255)
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    is_all_day: bool = False
    color: Optional[str] = Field(None, max_length=7)
    event_type: str = "normal"
    task_id: Optional[int] = None
    recurrence_rule: Optional[str] = Field(None, max_length=255, description="RFC 5545 规则")
    attendee_ids: Optional[list[int]] = None
    remind_minutes: Optional[list[int]] = Field(None, description="提前提醒分钟数")


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_all_day: Optional[bool] = None
    color: Optional[str] = None


class AttendeeUpdate(BaseModel):
    status: str = Field(..., description="accepted/declined/tentative")
