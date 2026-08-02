"""OA审批模块 — 数据模型"""
from sqlalchemy import Column, String, Text, Integer, Integer, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    RECALLED = "recalled"


class NodeStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TRANSFERRED = "transferred"
    AUTO_PASSED = "auto_passed"


class ApprovalTemplate(BaseModel):
    """审批模板"""
    __tablename__ = "approval_templates"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, comment="所属空间")
    name = Column(String(100), nullable=False, comment="模板名称")
    icon = Column(String(50), nullable=True, comment="图标")
    description = Column(Text, nullable=True, comment="说明")
    form_schema = Column(JSON, nullable=True, comment="表单字段定义")
    flow_schema = Column(JSON, nullable=True, comment="审批流程定义")
    category = Column(String(50), default="custom", comment="分类: leave/expense/travel/overtime/custom")
    is_builtin = Column(Boolean, default=False, comment="是否系统内置模板")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    creator = relationship("User", foreign_keys=[created_by])


class ApprovalInstance(BaseModel):
    """审批实例"""
    __tablename__ = "approval_instances"
    __table_args__ = {'extend_existing': True}

    template_id = Column(Integer, ForeignKey("approval_templates.id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="申请人")
    title = Column(String(255), nullable=False, comment="审批标题")
    form_data = Column(JSON, nullable=True, comment="填写的表单数据")
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    current_node_sort = Column(Integer, default=0, comment="当前审批节点序号")
    submitted_at = Column(Text, nullable=True)
    completed_at = Column(Text, nullable=True)

    template = relationship("ApprovalTemplate", foreign_keys=[template_id], backref="instances")
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    applicant = relationship("User", foreign_keys=[applicant_id], backref="approval_applications")
    nodes = relationship("ApprovalNode", back_populates="instance", cascade="all, delete-orphan",
                         order_by="ApprovalNode.sort_order")
    cc_list = relationship("ApprovalCC", back_populates="instance", cascade="all, delete-orphan")


class ApprovalNode(BaseModel):
    """审批节点记录"""
    __tablename__ = "approval_nodes"
    __table_args__ = {'extend_existing': True}

    instance_id = Column(Integer, ForeignKey("approval_instances.id"), nullable=False)
    node_name = Column(String(100), nullable=False, comment="节点名称")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="审批人")
    status = Column(Enum(NodeStatus), default=NodeStatus.PENDING, nullable=False)
    comment = Column(Text, nullable=True, comment="审批意见")
    acted_at = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, comment="节点顺序")

    instance = relationship("ApprovalInstance", back_populates="nodes")
    approver = relationship("User", foreign_keys=[approver_id], backref="approval_tasks")


class ApprovalCC(BaseModel):
    """审批抄送"""
    __tablename__ = "approval_cc"
    __table_args__ = {'extend_existing': True}

    instance_id = Column(Integer, ForeignKey("approval_instances.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_read = Column(Boolean, default=False)

    instance = relationship("ApprovalInstance", back_populates="cc_list")
    user = relationship("User", foreign_keys=[user_id])
