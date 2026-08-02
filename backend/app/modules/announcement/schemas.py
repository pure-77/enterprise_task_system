"""企业公告模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional


class AnnouncementCreate(BaseModel):
    workspace_id: int
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    type: str = "notice"
    is_pinned: bool = False
    is_must_read: bool = False
    publish_at: Optional[str] = None
    expire_at: Optional[str] = None
