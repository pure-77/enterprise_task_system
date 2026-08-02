"""文件管理模块 — 数据模型"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import BaseModel


class FileFolder(BaseModel):
    """文件夹"""
    __tablename__ = "file_folders"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("file_folders.id"), nullable=True)
    name = Column(String(200), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    parent = relationship("FileFolder", remote_side="FileFolder.id", backref="children")
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    creator = relationship("User", foreign_keys=[created_by])


class File(BaseModel):
    """文件"""
    __tablename__ = "files"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("file_folders.id"), nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    size = Column(BigInteger, default=0, comment="文件大小(字节)")
    mime_type = Column(String(100), nullable=True)
    path = Column(String(500), nullable=True, comment="存储路径")
    version = Column(Integer, default=1)

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    folder = relationship("FileFolder", foreign_keys=[folder_id], backref="files")
    uploader = relationship("User", foreign_keys=[uploader_id])
