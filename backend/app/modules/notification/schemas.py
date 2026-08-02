"""通知中心模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional


class NotificationReadMark(BaseModel):
    notification_ids: Optional[list[int]] = Field(None, description="标记为已读的通知ID列表，不传则全部已读")


class SettingUpdate(BaseModel):
    in_app: Optional[bool] = None
    push: Optional[bool] = None
    email: Optional[bool] = None
