import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("开始初始化数据库表结构...")

# 导入必要的模块
try:
    from app.db.base import Base
    from app.models import User, Category, Task, Tag, Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity
    from app.db.session import engine
    print("✓ 导入模块成功")
except Exception as e:
    print(f"✗ 导入模块失败: {e}")
    sys.exit(1)

# 创建所有表
try:
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建成功")
    print("  - users表")
    print("  - categories表")
    print("  - tasks表")
    print("  - tags表")
    print("  - task_tags表")
    print("  - workspaces表")
    print("  - workspace_members表")
    print("  - workspace_invitations表")
    print("  - workspace_activities表")
except Exception as e:
    print(f"✗ 数据库表创建失败: {e}")
    sys.exit(1)

print("\n数据库初始化完成！")