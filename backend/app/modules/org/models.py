"""组织架构模块 — 数据模型（Department, Position, AuditLog）"""
from sqlalchemy import Column, String, Integer, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import BaseModel


class Department(BaseModel):
    """部门模型 — 支持无限层级树形结构（物化路径）"""
    __tablename__ = "departments"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, comment="所属工作空间")
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True, comment="父部门ID，NULL=根部门")
    name = Column(String(100), nullable=False, comment="部门名称")
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="部门负责人")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序序号")
    path = Column(String(500), nullable=True, comment="物化路径，如 /1/3/15")

    # 自引用关系
    parent = relationship("Department", remote_side="Department.id", backref="children")
    leader = relationship("User", foreign_keys=[leader_id], backref="led_departments")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="departments")

    def __repr__(self):
        return f"<Department(id={self.id}, name={self.name}, path={self.path})>"


class Position(BaseModel):
    """职位模型"""
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, comment="所属工作空间")
    name = Column(String(50), nullable=False, comment="职位名称")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序序号")

    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="positions")

    def __repr__(self):
        return f"<Position(id={self.id}, name={self.name})>"


class AuditLog(BaseModel):
    """全平台审计日志 — 记录所有模块的写操作"""
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, comment="所属空间（NULL=系统级）")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="操作人ID（NULL=系统操作）")
    module = Column(String(50), nullable=False, comment="模块: task/im/approval/org/...")
    action = Column(String(50), nullable=False, comment="操作: create/update/delete/login/export/...")
    target_type = Column(String(50), nullable=True, comment="目标类型: task/department/member/...")
    target_id = Column(Integer, nullable=True, comment="目标ID")
    detail = Column(JSON, nullable=True, comment="变更详情")
    ip_address = Column(String(45), nullable=True, comment="操作IP")
    user_agent = Column(String(500), nullable=True, comment="用户设备信息")

    user = relationship("User", foreign_keys=[user_id], backref="audit_logs")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, module={self.module}, action={self.action})>"
