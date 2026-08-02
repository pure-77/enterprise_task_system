import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("开始执行工作空间功能数据库迁移...")

try:
    from app.db.base import Base
    from app.db.session import engine
    from sqlalchemy import inspect, text

    from app.models import User, Category, Task, Tag
    from app.models.workspace import Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity

    print("模块导入成功")

    # 创建新表
    Base.metadata.create_all(bind=engine)
    print("新表创建完成: workspaces, workspace_members, workspace_invitations, workspace_activities")

    inspector = inspect(engine)

    # 为现有表添加新列（如果不存在）
    with engine.connect() as conn:
        # tasks 表
        task_cols = [c['name'] for c in inspector.get_columns('tasks')]
        if 'workspace_id' not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN workspace_id INTEGER"))
            conn.execute(text("ALTER TABLE tasks ADD FOREIGN KEY (workspace_id) REFERENCES workspaces(id)"))
            print("tasks.workspace_id 列已添加")
        else:
            print("tasks.workspace_id 列已存在，跳过")
        if 'assignee_id' not in task_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN assignee_id INTEGER"))
            conn.execute(text("ALTER TABLE tasks ADD FOREIGN KEY (assignee_id) REFERENCES users(id)"))
            print("tasks.assignee_id 列已添加")
        else:
            print("tasks.assignee_id 列已存在，跳过")
        conn.commit()

        # categories 表
        cat_cols = [c['name'] for c in inspector.get_columns('categories')]
        if 'workspace_id' not in cat_cols:
            conn.execute(text("ALTER TABLE categories ADD COLUMN workspace_id INTEGER"))
            conn.execute(text("ALTER TABLE categories ADD FOREIGN KEY (workspace_id) REFERENCES workspaces(id)"))
            print("categories.workspace_id 列已添加")
        else:
            print("categories.workspace_id 列已存在，跳过")
        conn.commit()

        # tags 表
        tag_cols = [c['name'] for c in inspector.get_columns('tags')]
        if 'workspace_id' not in tag_cols:
            conn.execute(text("ALTER TABLE tags ADD COLUMN workspace_id INTEGER"))
            conn.execute(text("ALTER TABLE tags ADD FOREIGN KEY (workspace_id) REFERENCES workspaces(id)"))
            print("tags.workspace_id 列已添加")
        else:
            print("tags.workspace_id 列已存在，跳过")
        conn.commit()

    print("\n数据库迁移完成!")

except Exception as e:
    print(f"迁移失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
