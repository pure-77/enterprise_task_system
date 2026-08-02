"""执行表结构变更 — users 和 workspace_members 新增字段"""
from sqlalchemy import text
from app.db.session import engine


def run_migration():
    conn = engine.connect()

    # users 表新增字段
    user_columns = [
        ("real_name", "VARCHAR(50) NULL COMMENT '真实姓名'"),
        ("mobile", "VARCHAR(20) NULL COMMENT '手机号'"),
        ("avatar_thumb", "VARCHAR(500) NULL COMMENT '头像缩略图'"),
        ("last_login_at", "DATETIME NULL COMMENT '最后登录时间'"),
        ("last_login_ip", "VARCHAR(45) NULL COMMENT '最后登录IP'"),
    ]
    for col_name, col_def in user_columns:
        result = conn.execute(text(f"SHOW COLUMNS FROM users LIKE '{col_name}'"))
        if not result.fetchone():
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
            conn.commit()
            print(f"[OK] users.{col_name} added")
        else:
            print(f"[SKIP] users.{col_name} already exists")

    # workspace_members 表新增字段
    member_columns = [
        ("department_id", "BIGINT NULL COMMENT '所属部门ID'"),
        ("position_id", "BIGINT NULL COMMENT '职位ID'"),
        ("employee_no", "VARCHAR(50) NULL COMMENT '工号'"),
        ("real_name", "VARCHAR(50) NULL COMMENT '真实姓名'"),
        ("mobile", "VARCHAR(20) NULL COMMENT '手机号'"),
        ("join_date", "DATE NULL COMMENT '入职日期'"),
        ("status", "VARCHAR(20) DEFAULT 'active' NOT NULL COMMENT '成员状态'"),
    ]
    for col_name, col_def in member_columns:
        result = conn.execute(text(f"SHOW COLUMNS FROM workspace_members LIKE '{col_name}'"))
        if not result.fetchone():
            conn.execute(text(f"ALTER TABLE workspace_members ADD COLUMN {col_name} {col_def}"))
            conn.commit()
            print(f"[OK] workspace_members.{col_name} added")
        else:
            print(f"[SKIP] workspace_members.{col_name} already exists")

    conn.close()
    print("\n[Migration complete]")


if __name__ == "__main__":
    run_migration()
