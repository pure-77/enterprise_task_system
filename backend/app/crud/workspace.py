from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.workspace import (
    Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity,
    WorkspaceRole, InvitationStatus
)
from app.models.user import User
from app.models.category import Category
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceCRUD:
    """工作空间CRUD"""

    def create(self, db: Session, obj_in: WorkspaceCreate, user_id: int) -> Workspace:
        workspace = Workspace(
            name=obj_in.name,
            description=obj_in.description,
            owner_id=user_id
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        # 创建者自动成为Owner成员
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role=WorkspaceRole.OWNER
        )
        db.add(member)

        # 自动创建默认分类"未分类"
        default_category = Category(
            name="未分类",
            color="#909399",
            user_id=user_id,
            workspace_id=workspace.id
        )
        db.add(default_category)

        # 记录活动
        activity = WorkspaceActivity(
            workspace_id=workspace.id,
            user_id=user_id,
            action="workspace_created",
            detail='{"name": "' + workspace.name + '"}'
        )
        db.add(activity)

        db.commit()
        db.refresh(workspace)
        return workspace

    def get_by_id(self, db: Session, workspace_id: int) -> Optional[Workspace]:
        return db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.is_active == True
        ).first()

    def get_user_workspaces(self, db: Session, user_id: int) -> List[dict]:
        results = db.query(
            Workspace, WorkspaceMember.role, User.nickname, User.avatar
        ).outerjoin(
            WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id
        ).outerjoin(
            User, User.id == Workspace.owner_id
        ).filter(
            WorkspaceMember.user_id == user_id,
            Workspace.is_active == True
        ).order_by(Workspace.created_at.desc()).all()

        # 一次性查询所有 workspace 的成员数量，避免 N+1
        from sqlalchemy import func
        member_counts = db.query(
            WorkspaceMember.workspace_id,
            func.count(WorkspaceMember.id)
        ).filter(
            WorkspaceMember.is_active == True
        ).group_by(WorkspaceMember.workspace_id).all()
        member_count_map = {ws_id: count for ws_id, count in member_counts}

        workspace_list = []
        for ws, role, owner_nickname, owner_avatar in results:
            workspace_list.append({
                "id": ws.id,
                "name": ws.name,
                "description": ws.description,
                "owner_id": ws.owner_id,
                "owner_nickname": owner_nickname or "匿名用户",
                "owner_avatar": owner_avatar,
                "member_count": member_count_map.get(ws.id, 0),
                "role": role.value if role else None,
                "created_at": ws.created_at,
                "updated_at": ws.updated_at,
            })
        return workspace_list

    def update(self, db: Session, workspace: Workspace, obj_in: WorkspaceUpdate) -> Workspace:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workspace, field, value)
        db.commit()
        db.refresh(workspace)
        return workspace

    def delete(self, db: Session, workspace: Workspace) -> Workspace:
        workspace.is_active = False
        db.commit()
        return workspace


class WorkspaceMemberCRUD:
    """成员管理CRUD"""

    def get_members(self, db: Session, workspace_id: int) -> List[dict]:
        results = db.query(
            WorkspaceMember, User.nickname, User.email, User.avatar
        ).join(
            User, User.id == WorkspaceMember.user_id
        ).filter(
            WorkspaceMember.workspace_id == workspace_id
        ).order_by(WorkspaceMember.created_at.asc()).all()

        return [{
            "id": member.id,
            "user_id": member.user_id,
            "nickname": nickname,
            "email": email,
            "avatar": avatar,
            "role": member.role.value,
            "created_at": member.created_at,
        } for member, nickname, email, avatar in results]

    def get_member(self, db: Session, workspace_id: int, user_id: int) -> Optional[WorkspaceMember]:
        return db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()

    def add_member(self, db: Session, workspace_id: int, user_id: int, role: WorkspaceRole = WorkspaceRole.MEMBER) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    def update_role(self, db: Session, member: WorkspaceMember, role: WorkspaceRole) -> WorkspaceMember:
        member.role = role
        db.commit()
        db.refresh(member)
        return member

    def remove_member(self, db: Session, member: WorkspaceMember):
        db.delete(member)
        db.commit()

    def get_member_count(self, db: Session, workspace_id: int) -> int:
        return db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id
        ).count()


class WorkspaceInvitationCRUD:
    """邀请管理CRUD"""

    def create(self, db: Session, workspace_id: int, inviter_id: int, invitee_email: str, role: WorkspaceRole) -> WorkspaceInvitation:
        # 查找已注册用户
        invitee = db.query(User).filter(User.email == invitee_email).first()

        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            inviter_id=inviter_id,
            invitee_id=invitee.id if invitee else None,
            invitee_email=invitee_email,
            role=role,
            status=InvitationStatus.PENDING
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation

    def get_pending_by_workspace(self, db: Session, workspace_id: int) -> List[dict]:
        results = db.query(
            WorkspaceInvitation, User.nickname
        ).join(
            User, User.id == WorkspaceInvitation.inviter_id
        ).filter(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.status == InvitationStatus.PENDING
        ).order_by(WorkspaceInvitation.created_at.desc()).all()

        return [{
            "id": inv.id,
            "workspace_id": inv.workspace_id,
            "inviter_id": inv.inviter_id,
            "inviter_nickname": nickname,
            "invitee_id": inv.invitee_id,
            "invitee_email": inv.invitee_email,
            "role": inv.role.value,
            "status": inv.status.value,
            "created_at": inv.created_at,
        } for inv, nickname in results]

    def get_user_invitations(self, db: Session, user_id: int, user_email: str) -> List[dict]:
        results = db.query(
            WorkspaceInvitation, Workspace.name, User.nickname
        ).join(
            Workspace, Workspace.id == WorkspaceInvitation.workspace_id
        ).join(
            User, User.id == WorkspaceInvitation.inviter_id
        ).filter(
            WorkspaceInvitation.status == InvitationStatus.PENDING,
            (
                (WorkspaceInvitation.invitee_id == user_id) |
                (WorkspaceInvitation.invitee_email == user_email)
            )
        ).order_by(WorkspaceInvitation.created_at.desc()).all()

        return [{
            "id": inv.id,
            "workspace_id": inv.workspace_id,
            "workspace_name": ws_name,
            "inviter_id": inv.inviter_id,
            "inviter_nickname": inv_nick,
            "invitee_id": inv.invitee_id,
            "invitee_email": inv.invitee_email,
            "role": inv.role.value,
            "status": inv.status.value,
            "created_at": inv.created_at,
        } for inv, ws_name, inv_nick in results]

    def get_by_id(self, db: Session, invitation_id: int) -> Optional[WorkspaceInvitation]:
        return db.query(WorkspaceInvitation).filter(
            WorkspaceInvitation.id == invitation_id
        ).first()

    def accept(self, db: Session, invitation: WorkspaceInvitation, user_id: int) -> WorkspaceInvitation:
        invitation.status = InvitationStatus.ACCEPTED
        invitation.invitee_id = user_id
        db.commit()
        db.refresh(invitation)
        return invitation

    def reject(self, db: Session, invitation: WorkspaceInvitation) -> WorkspaceInvitation:
        invitation.status = InvitationStatus.REJECTED
        db.commit()
        db.refresh(invitation)
        return invitation

    def cancel(self, db: Session, invitation: WorkspaceInvitation):
        db.delete(invitation)
        db.commit()

    def get_pending_count(self, db: Session, user_id: int, user_email: str) -> int:
        return db.query(WorkspaceInvitation).filter(
            WorkspaceInvitation.status == InvitationStatus.PENDING,
            (
                (WorkspaceInvitation.invitee_id == user_id) |
                (WorkspaceInvitation.invitee_email == user_email)
            )
        ).count()


class WorkspaceActivityCRUD:
    """活动日志CRUD"""

    def add(self, db: Session, workspace_id: int, user_id: int, action: str,
            target_type: str = None, target_id: int = None, detail: str = None):
        activity = WorkspaceActivity(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail
        )
        db.add(activity)
        db.commit()

    def get_list(self, db: Session, workspace_id: int, limit: int = 50) -> List[dict]:
        results = db.query(
            WorkspaceActivity, User.nickname
        ).join(
            User, User.id == WorkspaceActivity.user_id
        ).filter(
            WorkspaceActivity.workspace_id == workspace_id
        ).order_by(WorkspaceActivity.created_at.desc()).limit(limit).all()

        return [{
            "id": act.id,
            "user_id": act.user_id,
            "user_nickname": nick,
            "action": act.action,
            "target_type": act.target_type,
            "target_id": act.target_id,
            "detail": act.detail,
            "created_at": act.created_at,
        } for act, nick in results]


workspace = WorkspaceCRUD()
workspace_member = WorkspaceMemberCRUD()
workspace_invitation = WorkspaceInvitationCRUD()
workspace_activity = WorkspaceActivityCRUD()
