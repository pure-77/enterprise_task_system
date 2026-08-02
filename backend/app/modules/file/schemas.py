"""文件管理模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional


class FolderCreate(BaseModel):
    workspace_id: int
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[int] = None


class FileMove(BaseModel):
    folder_id: Optional[int] = None
