from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceDetailResponse,
    WorkspaceMemberResponse, UpdateMemberRole, InvitationCreate, InvitationResponse,
    ActivityResponse
)
from app.crud.workspace import workspace, workspace_member, workspace_invitation, workspace_activity
from app.models.workspace import WorkspaceRole, Workspace, WorkspaceMember
from app.core.permissions import get_workspace_member, require_role
from app.crud.user import user as user_crud, user
from app.api.v1.task import get_current_user_id
from app.services.email_service import email_service
from app.services.cache_service import CacheService

router = APIRouter()

# ============ 工作空间 CRUD ============

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    obj_in: WorkspaceCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    ws = workspace.create(db, obj_in, user_id)
    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "owner_id": ws.owner_id,
        "member_count": 1,
        "role": "owner",
        "created_at": ws.created_at,
        "updated_at": ws.updated_at,
    }


@router.get("", response_model=list[WorkspaceDetailResponse])
def get_workspaces(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    return workspace.get_user_workspaces(db, user_id)


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    member = get_workspace_member(workspace_id, user_id, db)
    ws = workspace.get_by_id(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="空间不存在")
    owner = user_crud.get(db, ws.owner_id)
    member_count = workspace_member.get_member_count(db, workspace_id)
    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "owner_id": ws.owner_id,
        "owner_nickname": owner.nickname if owner else None,
        "owner_avatar": owner.avatar if owner else None,
        "member_count": member_count,
        "role": member.role.value if member else None,
        "created_at": ws.created_at,
        "updated_at": ws.updated_at,
    }


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    obj_in: WorkspaceUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    ws = workspace.get_by_id(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="空间不存在")
    ws = workspace.update(db, ws, obj_in)
    member_count = workspace_member.get_member_count(db, workspace_id)
    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "owner_id": ws.owner_id,
        "member_count": member_count,
        "role": None,
        "created_at": ws.created_at,
        "updated_at": ws.updated_at,
    }


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER], db)
    ws = workspace.get_by_id(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="空间不存在")
    workspace.delete(db, ws)
    return {"message": "空间已解散"}


# ============ 成员管理 ============

@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
def get_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    get_workspace_member(workspace_id, user_id, db)
    return workspace_member.get_members(db, workspace_id)


@router.put("/{workspace_id}/members/{target_user_id}/role")
def update_member_role(
    workspace_id: int,
    target_user_id: int,
    role_in: UpdateMemberRole,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    member = workspace_member.get_member(db, workspace_id, target_user_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role == WorkspaceRole.OWNER:
        raise HTTPException(status_code=400, detail="不能修改Owner的角色")
    if role_in.role == WorkspaceRole.OWNER:
        raise HTTPException(status_code=400, detail="不能将成员设置为Owner（需转让空间）")
    workspace_member.update_role(db, member, role_in.role)
    CacheService.delete_member_permission(workspace_id, target_user_id)
    return {"message": "角色修改成功"}


@router.delete("/{workspace_id}/members/{target_user_id}")
def remove_member(
    workspace_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    member = workspace_member.get_member(db, workspace_id, target_user_id)
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role == WorkspaceRole.OWNER:
        raise HTTPException(status_code=400, detail="不能移除Owner，请先转让空间或解散空间")
    workspace_member.remove_member(db, member)
    workspace_activity.add(db, workspace_id, user_id, "member_removed", "member", target_user_id)
    CacheService.delete_member_permission(workspace_id, target_user_id)
    return {"message": "成员已移除"}


@router.post("/{workspace_id}/members/leave")
def leave_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    member = get_workspace_member(workspace_id, user_id, db)
    if member.role == WorkspaceRole.OWNER:
        raise HTTPException(status_code=400, detail="Owner不能退出空间，请先转让或解散空间")
    workspace_member.remove_member(db, member)
    workspace_activity.add(db, workspace_id, user_id, "member_left", "member", user_id)
    CacheService.delete_member_permission(workspace_id, user_id)
    return {"message": "已退出空间"}


# ============ 邀请管理 ============

@router.post("/{workspace_id}/invitations", response_model=InvitationResponse)
def create_invitation(
    workspace_id: int,
    inv_in: InvitationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)

    # 查找被邀请用户，检查是否已是成员
    from app.models.user import User
    invitee = db.query(User).filter(User.email == inv_in.invitee_email).first()
    if not user.is_email_exists(db, inv_in.invitee_email):
        raise HTTPException(status_code=404,detail="该用户未注册")
    if invitee:
        already_member = workspace_member.get_member(db, workspace_id, invitee.id)
        if already_member:
            raise HTTPException(status_code=400, detail="该用户已是空间成员")

    inv = workspace_invitation.create(db, workspace_id, user_id, inv_in.invitee_email, inv_in.role)
    ws = workspace.get_by_id(db, workspace_id)
    inviter = user_crud.get(db, user_id)

    # 异步发送邀请邮件 — 投递到 Celery Worker
    inviter_name = inviter.nickname if inviter else "未知用户"
    from app.tasks.email_tasks import send_invitation_email
    send_invitation_email.delay(
        inv_in.invitee_email, ws.name, inviter_name, inv_in.role.value
    )

    return {
        "id": inv.id,
        "workspace_id": inv.workspace_id,
        "workspace_name": ws.name if ws else None,
        "inviter_id": inv.inviter_id,
        "inviter_nickname": inviter.nickname if inviter else None,
        "invitee_id": inv.invitee_id,
        "invitee_email": inv.invitee_email,
        "role": inv.role.value,
        "status": inv.status.value,
        "created_at": inv.created_at,
    }


@router.get("/{workspace_id}/invitations", response_model=list[InvitationResponse])
def get_workspace_invitations(
    workspace_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    return workspace_invitation.get_pending_by_workspace(db, workspace_id)


@router.delete("/{workspace_id}/invitations/{inv_id}")
def cancel_invitation(
    workspace_id: int,
    inv_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    require_role(workspace_id, user_id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    inv = workspace_invitation.get_by_id(db, inv_id)
    if not inv or inv.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="邀请不存在")
    workspace_invitation.cancel(db, inv)
    return {"message": "邀请已取消"}


# ============ 活动日志 ============

@router.get("/{workspace_id}/activities", response_model=list[ActivityResponse])
def get_activities(
    workspace_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    get_workspace_member(workspace_id, user_id, db)
    return workspace_activity.get_list(db, workspace_id, limit)
