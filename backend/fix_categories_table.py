import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("开始修复数据库表结构...")

try:
    from app.db.session import engine
    from sqlalchemy import text
    
    conn = engine.connect()
    
    # 检查is_active字段是否存在
    result = conn.execute(text("SHOW COLUMNS FROM categories LIKE 'is_active'"))
    column_exists = result.fetchone()
    
    if not column_exists:
        # 添加is_active字段
        conn.execute(text("ALTER TABLE categories ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活'"))
        conn.commit()
        print("✓ 已添加is_active字段到categories表")
    else:
        print("✓ is_active字段已存在，无需修改")
    
    conn.close()
    print("\n数据库表结构修复完成！")
    
except Exception as e:
    print(f"✗ 数据库表结构修复失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)