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
    """初始化数据库 - 面试考点：创建所有表结构"""
    # 导入所有模型以确保表被创建 - 面试考点：模型导入顺序很重要
    from app.models.user import User
    from app.models.workspace import Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity
    from app.models.category import Category
    from app.models.task import Task
    from app.models.tag import Tag
    from app.models.task_tags import task_tags
    from app.models.task_completion import TaskCompletion
    from app.models.task_assignee import task_assignees
    from app.modules.org.models import Department, Position, AuditLog
    from app.modules.im.models import Conversation, ConversationMember, Message, MessageRead
    from app.modules.notification.models import Notification, NotificationSetting
    from app.modules.approval.models import ApprovalTemplate, ApprovalInstance, ApprovalNode, ApprovalCC
    from app.modules.calendar.models import Event, EventAttendee, EventReminder
    from app.modules.attendance.models import AttendanceRule, AttendanceRecord, AttendanceStats
    from app.modules.announcement.models import Announcement, AnnouncementRead
    from app.modules.file.models import FileFolder, File
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 修复categories表结构 - 添加is_active字段
    try:
        from sqlalchemy import text
        conn = engine.connect()
        
        # 检查is_active字段是否存在
        result = conn.execute(text("SHOW COLUMNS FROM categories LIKE 'is_active'"))
        column_exists = result.fetchone()
        
        if not column_exists:
            # 添加is_active字段
            conn.execute(text("ALTER TABLE categories ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活'"))
            conn.commit()
            print("[OK] 已添加is_active字段到categories表")
        
        # 修复tasks表结构 - 添加is_active字段
        result = conn.execute(text("SHOW COLUMNS FROM tasks LIKE 'is_active'"))
        column_exists = result.fetchone()
        
        if not column_exists:
            # 添加is_active字段
            conn.execute(text("ALTER TABLE tasks ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活'"))
            conn.commit()
            print("[OK] 已添加is_active字段到tasks表")
        
        # 修复tasks表结构 - 添加priority字段
        result = conn.execute(text("SHOW COLUMNS FROM tasks LIKE 'priority'"))
        column_exists = result.fetchone()

        if not column_exists:
            # 添加priority字段
            conn.execute(text("ALTER TABLE tasks ADD COLUMN priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium' NOT NULL COMMENT '任务优先级'"))
            conn.commit()
            print("[OK] 已添加priority字段到tasks表")

        # 修复tasks表结构 - 添加is_team_wide字段
        result = conn.execute(text("SHOW COLUMNS FROM tasks LIKE 'is_team_wide'"))
        column_exists = result.fetchone()

        if not column_exists:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN is_team_wide BOOLEAN DEFAULT FALSE COMMENT '团队公开任务，全员可见可编辑'"))
            conn.commit()
            print("[OK] 已添加is_team_wide字段到tasks表")

        # 创建task_completions表（团队任务完成追踪）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_completions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL COMMENT '任务ID',
                user_id INT NOT NULL COMMENT '完成人ID',
                completed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '完成时间',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE KEY uk_task_user (task_id, user_id)
            )
        """))
        conn.commit()
        print("[OK] 已创建task_completions表")

        # 创建task_assignees表（多人任务分配）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_assignees (
                task_id INT NOT NULL COMMENT '任务ID',
                user_id INT NOT NULL COMMENT '被分配人ID',
                PRIMARY KEY (task_id, user_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        conn.commit()
        # print("[OK] 已创建task_assignees表")

        conn.close()
    except Exception as e:
        print(f"修复表结构时出错: {e}")
