"""知识库模块 — 数据模型（RAG 索引元数据）

向量本体存 Chroma（backend/data/chroma），这两张表存元数据：
- knowledge_documents：一个来源（File / Announcement / Message）一行，记录索引状态
- knowledge_chunks：分片元数据，便于重建与词法兜底
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey

from app.db.base import BaseModel


class KnowledgeDocument(BaseModel):
    """知识库索引文档：一个 File / Announcement / Message 对应一行"""
    __tablename__ = "knowledge_documents"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, comment="所属空间")
    source_type = Column(String(20), nullable=False, comment="来源类型: file/announcement/im")
    source_id = Column(Integer, nullable=False, comment="来源ID: File.id/Announcement.id/Message.id")
    title = Column(String(255), nullable=True, comment="来源标题")
    content_hash = Column(String(64), nullable=True, comment="正文MD5，用于跳过重复索引")
    status = Column(String(20), nullable=False, default="pending",
                    comment="状态: pending/indexed/failed/unsupported")
    chunk_count = Column(Integer, nullable=False, default=0, comment="分片数")
    error_msg = Column(Text, nullable=True, comment="失败原因")
    created_by = Column(Integer, nullable=True, comment="上传者/发布者/发送者")


class KnowledgeChunk(BaseModel):
    """知识库分片元数据"""
    __tablename__ = "knowledge_chunks"
    __table_args__ = {'extend_existing': True}

    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
                         nullable=False, comment="所属文档ID")
    chunk_index = Column(Integer, nullable=False, comment="分片序号")
    point_id = Column(String(64), nullable=False, comment="Chroma 向量 id（source_type:source_id:chunk_index）")
    content = Column(Text, nullable=False, comment="分片正文")
    char_count = Column(Integer, nullable=False, default=0, comment="字符数")
