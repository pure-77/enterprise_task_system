"""系统配置模型 — 键值对存储，用于动态密钥管理等"""
from sqlalchemy import Column, String, Text
from app.db.base import BaseModel


class SystemConfig(BaseModel):
    """系统配置表 — 存储 JWT 密钥等运行时配置，避免硬编码在 .env 中"""
    __tablename__ = "system_config"

    config_key = Column(String(100), unique=True, nullable=False, index=True, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    description = Column(String(200), nullable=True, comment="描述说明")
