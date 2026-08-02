"""即时通讯模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConversationCreate(BaseModel):
    workspace_id: int = Field(..., description="工作空间ID")
    type: str = Field(..., description="会话类型: single/group")
    peer_id: Optional[int] = Field(None, description="单聊对方用户ID（type=single时必填）")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="群聊名称（type=group时必填）")
    member_ids: Optional[list[int]] = Field(None, description="初始成员ID列表（type=group时必填）")
    avatar: Optional[str] = Field(None, max_length=500, description="群聊头像URL")


class MessageCreate(BaseModel):
    msg_type: str = Field("text", description="消息类型: text/image/file")
    content: str = Field(..., min_length=1, description="消息内容")
    reply_to_id: Optional[int] = Field(None, description="引用回复的消息ID")


class ReadMark(BaseModel):
    message_ids: Optional[list[int]] = Field(None, description="标记为已读的消息ID列表，不传则全部已读")


class MemberAdd(BaseModel):
    user_id: int = Field(..., description="要添加的用户ID")


class MuteToggle(BaseModel):
    is_muted: bool = Field(..., description="是否全员禁言")
