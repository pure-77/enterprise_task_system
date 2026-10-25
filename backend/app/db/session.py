from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.base import Base

# 创建同步引擎 - 面试考点：使用pymysql驱动连接MySQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # 禁止 SQL 日志输出
)

# 创建会话工厂 - 面试考点：使用sessionmaker管理数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """获取数据库会话 - 面试考点：依赖注入模式，确保会话正确关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """获取数据库会话（非生成器版本，用于Celery任务等非请求上下文）"""
    return SessionLocal()


def init_db():
    """初始化数据库 — 仅创建缺失的表，不做运行时 ALTER TABLE
    历史的 ALTER TABLE / 索引创建逻辑已移除：
      - 列已存在于模型定义中，新库 create_all 会自动创建
      - 已有库的列早已补齐，无需每次启动检查
      - 后续结构变更应使用 Alembic 迁移管理
    """
    # 导入所有模型以确保表被注册到 metadata
    from app.models.user import User  # noqa: F401
    from app.models.workspace import Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity  # noqa: F401
    from app.models.category import Category  # noqa: F401
    from app.models.task import Task  # noqa: F401
    from app.models.tag import Tag  # noqa: F401
    from app.models.task_tags import task_tags  # noqa: F401
    from app.models.task_completion import TaskCompletion  # noqa: F401
    from app.models.task_assignee import task_assignees  # noqa: F401
    from app.modules.org.models import Department, Position, AuditLog  # noqa: F401
    from app.modules.im.models import Conversation, ConversationMember, Message, MessageRead  # noqa: F401
    from app.modules.notification.models import Notification, NotificationSetting  # noqa: F401
    from app.modules.approval.models import ApprovalTemplate, ApprovalInstance, ApprovalNode, ApprovalCC  # noqa: F401
    from app.modules.calendar.models import Event, EventAttendee, EventReminder  # noqa: F401
    from app.modules.attendance.models import AttendanceRule, AttendanceRecord, AttendanceStats  # noqa: F401
    from app.modules.announcement.models import Announcement, AnnouncementRead  # noqa: F401
    from app.modules.file.models import FileFolder, File  # noqa: F401
    from app.modules.knowledge.models import KnowledgeDocument, KnowledgeChunk  # noqa: F401

    Base.metadata.create_all(bind=engine)
