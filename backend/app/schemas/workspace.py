from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.workspace import WorkspaceRole, InvitationStatus


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="空间名称")
    description: Optional[str] = Field(None, max_length=500, description="空间描述")


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="空间名称")
    description: Optional[str] = Field(None, max_length=500, description="空间描述")


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    member_count: int = 0
    role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceDetailResponse(WorkspaceResponse):
    owner_nickname: Optional[str] = None
    owner_avatar: Optional[str] = None


class WorkspaceMemberResponse(BaseModel):
    id: int
    user_id: int
    nickname: str = ""
    email: str = ""
    avatar: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateMemberRole(BaseModel):
    role: WorkspaceRole = Field(..., description="新角色")


class InvitationCreate(BaseModel):
    invitee_email: str = Field(..., max_length=255, description="被邀请人邮箱")
    role: WorkspaceRole = Field(WorkspaceRole.MEMBER, description="赋予角色")


class InvitationResponse(BaseModel):
    id: int
    workspace_id: int
    workspace_name: Optional[str] = None
    inviter_id: int
    inviter_nickname: Optional[str] = None
    invitee_id: Optional[int] = None
    invitee_email: str
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityResponse(BaseModel):
    id: int
    user_id: int
    user_nickname: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    detail: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
