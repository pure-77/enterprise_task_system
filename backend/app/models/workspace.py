from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, Date
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Workspace(BaseModel):
    __tablename__ = "workspaces"
    __table_args__ = {'extend_existing': True}

    name = Column(String(100), nullable=False, comment="空间名称")
    description = Column(Text, nullable=True, comment="空间描述")
    owner_id = Column(ForeignKey("users.id"), nullable=False, comment="创建者ID")

    owner = relationship("User", backref="owned_workspaces", foreign_keys=[owner_id])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(BaseModel):
    __tablename__ = "workspace_members"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(ForeignKey("workspaces.id"), nullable=False, comment="空间ID")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="用户ID")
    role = Column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False, comment="角色")
    department_id = Column(ForeignKey("departments.id"), nullable=True, comment="所属部门ID")
    position_id = Column(ForeignKey("positions.id"), nullable=True, comment="职位ID")
    employee_no = Column(String(50), nullable=True, comment="工号")
    real_name = Column(String(50), nullable=True, comment="真实姓名（冗余）")
    mobile = Column(String(20), nullable=True, comment="手机号（冗余）")
    join_date = Column(Date, nullable=True, comment="入职日期")
    status = Column(String(20), default="active", nullable=False, comment="成员状态: active/leave/suspended")

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", backref="workspace_memberships", foreign_keys=[user_id])
    # department/position relationship 注释掉，org router 里手动查（避免跨模块 mapper 初始化顺序问题）
    # department = relationship("Department", foreign_keys=[department_id])
    # position = relationship("Position", foreign_keys=[position_id])


class WorkspaceInvitation(BaseModel):
    __tablename__ = "workspace_invitations"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(ForeignKey("workspaces.id"), nullable=False, comment="空间ID")
    inviter_id = Column(ForeignKey("users.id"), nullable=False, comment="邀请人ID")
    invitee_id = Column(ForeignKey("users.id"), nullable=True, comment="被邀请人ID（已注册用户）")
    invitee_email = Column(String(255), nullable=False, comment="被邀请人邮箱")
    role = Column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False, comment="赋予角色")
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False, comment="邀请状态")

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    inviter = relationship("User", foreign_keys=[inviter_id], backref="sent_invitations")
    invitee = relationship("User", foreign_keys=[invitee_id], backref="received_invitations")


class WorkspaceActivity(BaseModel):
    __tablename__ = "workspace_activities"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(ForeignKey("workspaces.id"), nullable=False, comment="空间ID")
    user_id = Column(ForeignKey("users.id"), nullable=False, comment="操作用户ID")
    action = Column(String(50), nullable=False, comment="操作类型: task_created/task_completed/member_joined等")
    target_type = Column(String(50), nullable=True, comment="目标类型: task/member/category")
    target_id = Column(Integer, nullable=True, comment="目标ID")
    detail = Column(Text, nullable=True, comment="操作详情JSON")

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    user = relationship("User", foreign_keys=[user_id])
