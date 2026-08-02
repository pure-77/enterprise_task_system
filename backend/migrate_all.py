"""============================================================
  一键数据库迁移脚本
  用法: cd backend && PYTHONPATH=. python migrate_all.py
  安全: 可重复执行，已存在的表/字段自动跳过
  ============================================================"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.db.base import Base
from app.db.session import engine


# ============================================================
# Step 1: 创建所有新表
# ============================================================
def create_all_tables():
    print("=" * 50)
    print("[Step 1] Creating all new tables...")
    print("=" * 50)

    # 导入所有模型（确保 SQLAlchemy 发现所有表定义）
    from app.models.user import User                          # users (existing)
    from app.models.category import Category                  # categories (existing)
    from app.models.task import Task                          # tasks (existing)
    from app.models.tag import Tag                            # tags (existing)
    from app.models.task_tags import task_tags                # task_tags (existing)
    from app.models.task_completion import TaskCompletion     # task_completions (existing)
    from app.models.task_assignee import task_assignees       # task_assignees (existing)
    from app.models.workspace import (                        # workspaces + members + invitations + activities (existing)
        Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity)

    from app.modules.org.models import Department, Position, AuditLog
    from app.modules.im.models import Conversation, ConversationMember, Message, MessageRead
    from app.modules.notification.models import Notification, NotificationSetting
    from app.modules.approval.models import ApprovalTemplate, ApprovalInstance, ApprovalNode, ApprovalCC
    from app.modules.calendar.models import Event, EventAttendee, EventReminder
    from app.modules.attendance.models import AttendanceRule, AttendanceRecord, AttendanceStats
    from app.modules.announcement.models import Announcement, AnnouncementRead
    from app.modules.file.models import FileFolder, File

    # create_all 只创建不存在的表
    Base.metadata.create_all(bind=engine)

    conn = engine.connect()
    existing = [row[0] for row in conn.execute(text("SHOW TABLES")).fetchall()]
    conn.close()

    expected = [
        "users", "categories", "tasks", "tags", "task_tags", "task_completions",
        "task_assignees", "workspaces", "workspace_members", "workspace_invitations",
        "workspace_activities",
        # Phase 1
        "departments", "positions", "audit_logs",
        # Phase 2
        "conversations", "conversation_members", "messages", "message_reads",
        "notifications", "notification_settings",
        # Phase 3
        "approval_templates", "approval_instances", "approval_nodes", "approval_cc",
        "events", "event_attendees", "event_reminders",
        # Phase 4
        "attendance_rules", "attendance_records", "attendance_stats",
        "announcements", "announcement_reads",
        "file_folders", "files",
    ]
    for t in expected:
        status = "[OK]" if t in existing else "[MISSING]"
        print(f"  {status} {t}")

    print(f"\n  Total tables: {len(existing)}")


# ============================================================
# Step 2: 给已有表添加新字段
# ============================================================
def alter_existing_tables():
    print("\n" + "=" * 50)
    print("[Step 2] Adding new columns to existing tables...")
    print("=" * 50)

    conn = engine.connect()

    # --- users 表 ---
    user_cols = {
        "real_name":      "VARCHAR(50) NULL COMMENT '真实姓名'",
        "mobile":         "VARCHAR(20) NULL COMMENT '手机号'",
        "avatar_thumb":   "VARCHAR(500) NULL COMMENT '头像缩略图'",
        "last_login_at":  "DATETIME NULL COMMENT '最后登录时间'",
        "last_login_ip":  "VARCHAR(45) NULL COMMENT '最后登录IP'",
    }
    _add_columns(conn, "users", user_cols)

    # --- workspace_members 表 ---
    member_cols = {
        "department_id": "BIGINT NULL COMMENT '所属部门ID'",
        "position_id":   "BIGINT NULL COMMENT '职位ID'",
        "employee_no":   "VARCHAR(50) NULL COMMENT '工号'",
        "real_name":     "VARCHAR(50) NULL COMMENT '真实姓名'",
        "mobile":        "VARCHAR(20) NULL COMMENT '手机号'",
        "join_date":     "DATE NULL COMMENT '入职日期'",
        "status":        "VARCHAR(20) DEFAULT 'active' NOT NULL COMMENT '成员状态'",
    }
    _add_columns(conn, "workspace_members", member_cols)

    conn.close()


def _add_columns(conn, table: str, columns: dict):
    existing_cols = set()
    try:
        result = conn.execute(text(f"SHOW COLUMNS FROM {table}"))
        existing_cols = {row[0] for row in result.fetchall()}
    except Exception:
        print(f"  [SKIP] Table '{table}' does not exist yet")
        return

    for col_name, col_def in columns.items():
        if col_name in existing_cols:
            print(f"  [SKIP] {table}.{col_name} (already exists)")
        else:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                print(f"  [OK]   {table}.{col_name}")
            except Exception as e:
                print(f"  [ERR] {table}.{col_name}: {e}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    create_all_tables()
    alter_existing_tables()

    print("\n" + "=" * 50)
    print("Migration complete! Restart the backend server.")
    print("=" * 50)
