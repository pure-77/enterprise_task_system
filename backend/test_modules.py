import sys
sys.path.append('d:\\Python Note\\web_server\\personal_task_system\\backend')

try:
    from app.core.config import settings
    print("✓ 配置模块加载成功")
    print(f"  数据库URL: {settings.DATABASE_URL}")
    print(f"  Redis URL: {settings.REDIS_URL}")
except Exception as e:
    print(f"✗ 配置模块加载失败: {e}")

try:
    from app.core.security import get_password_hash, verify_password
    print("✓ 安全模块加载成功")
    password = "test123"
    hashed = get_password_hash(password)
    print(f"  密码哈希: {hashed}")
    verified = verify_password(password, hashed)
    print(f"  密码验证: {verified}")
except Exception as e:
    print(f"✗ 安全模块加载失败: {e}")

try:
    from app.db.redis_client import get_redis
    r = get_redis()
    print("✓ Redis客户端加载成功")
    r.set("test_key", "test_value", ex=60)
    value = r.get("test_key")
    print(f"  Redis测试: {value}")
    r.delete("test_key")
except Exception as e:
    print(f"✗ Redis客户端加载失败: {e}")

try:
    from app.models.user import User
    print("✓ 用户模型加载成功")
except Exception as e:
    print(f"✗ 用户模型加载失败: {e}")

try:
    from app.schemas.user import UserCreate, VerifyCodeRequest
    print("✓ 数据模型加载成功")
except Exception as e:
    print(f"✗ 数据模型加载失败: {e}")

print("\n所有核心模块加载完成！")
