from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.workspace import InvitationResponse
from app.crud.workspace import workspace_invitation, workspace_member, workspace_activity
from app.models.workspace import InvitationStatus
from app.crud.user import user as user_crud
from app.api.v1.task import get_current_user_id

router = APIRouter()


@router.get("", response_model=list[InvitationResponse])
def get_my_invitations(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return workspace_invitation.get_user_invitations(db, user_id, user.email)


@router.get("/pending-count")
def get_pending_count(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    count = workspace_invitation.get_pending_count(db, user_id, user.email)
    return {"count": count}


@router.post("/{invitation_id}/accept")
def accept_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    inv = workspace_invitation.get_by_id(db, invitation_id)
    if not inv or inv.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=404, detail="邀请不存在或已处理")

    user = user_crud.get(db, user_id)
    if inv.invitee_email != user.email and inv.invitee_id != user_id:
        raise HTTPException(status_code=403, detail="该邀请不属于你")

    workspace_invitation.accept(db, inv, user_id)
    workspace_member.add_member(db, inv.workspace_id, user_id, inv.role)
    workspace_activity.add(db, inv.workspace_id, user_id, "member_joined", "member",
                           user_id, '{"role": "' + inv.role.value + '"}')
    return {"message": "已加入空间"}


@router.post("/{invitation_id}/reject")
def reject_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    inv = workspace_invitation.get_by_id(db, invitation_id)
    if not inv or inv.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=404, detail="邀请不存在或已处理")

    user = user_crud.get(db, user_id)
    if inv.invitee_email != user.email and inv.invitee_id != user_id:
        raise HTTPException(status_code=403, detail="该邀请不属于你")

    workspace_invitation.reject(db, inv)
    # 添加邀请被拒绝的活动日志，让发起方可以看到
    workspace_activity.add(db, inv.workspace_id, user_id, "invitation_rejected", "invitation",
                           invitation_id, '{"email": "' + inv.invitee_email + '"}')
    return {"message": "已拒绝邀请"}
