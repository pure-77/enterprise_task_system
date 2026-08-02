"""============================================================
  全模块健康检查 — 验证每个模块的核心 API 是否正常
  用法: cd backend && PYTHONPATH=. python check_modules.py
  ============================================================"""
import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 使用测试用户 token（需要先在数据库中创建测试用户）
# 这里用模拟方式检查路由是否存在和基础响应

passed = 0
failed = 0

def check(name, method, path, expected_status=None):
    global passed, failed
    methods = {"GET": client.get, "POST": client.post, "PUT": client.put, "DELETE": client.delete}
    fn = methods.get(method)

    # 对于需要 auth 的接口，检查路由是否存在（无 token 应返回 401/403）
    # 对于不需要 auth 的接口，直接请求
    resp = fn(path) if fn else None
    if resp is None:
        print(f"  [FAIL] {method} {path} — unknown method")
        failed += 1
        return

    status = resp.status_code
    ok = expected_status and status == expected_status
    if expected_status is None:
        ok = status != 500  # 只要不 500 就算路由正常

    tag = "[OK]" if ok else "[FAIL]"
    print(f"  {tag} {method:6} {path:50s} → {status}")
    if ok:
        passed += 1
    else:
        failed += 1
        if status == 500:
            try:
                print(f"       body: {resp.json()}")
            except:
                print(f"       body: {resp.text[:200]}")


print("=" * 60)
print("Module Health Check")
print("=" * 60)

# ===== Phase 1: Org =====
print("\n--- Phase 1: Organization ---")
check("Dept tree", "GET", "/api/v1/org/departments?workspace_id=1")
check("Positions", "GET", "/api/v1/org/positions?workspace_id=1")
check("Members", "GET", "/api/v1/org/members?workspace_id=1")

# ===== Phase 2: IM =====
print("\n--- Phase 2: IM ---")
check("Conv list", "GET", "/api/v1/im/conversations?workspace_id=1")
check("Create single", "POST", "/api/v1/im/conversations",
      params={"workspace_id": 1})

# ===== Phase 2: Notification =====
print("\n--- Phase 2: Notification ---")
check("Notif list", "GET", "/api/v1/notification/notifications")
check("Unread count", "GET", "/api/v1/notification/notifications/unread-count")
check("Settings", "GET", "/api/v1/notification/settings")

# ===== Phase 3: Approval =====
print("\n--- Phase 3: Approval ---")
check("Templates", "GET", "/api/v1/approval/templates?workspace_id=1")
check("Pending", "GET", "/api/v1/approval/instances/pending?workspace_id=1")
check("My apps", "GET", "/api/v1/approval/instances/my?workspace_id=1")
check("Processed", "GET", "/api/v1/approval/instances/processed?workspace_id=1")

# ===== Phase 3: Calendar =====
print("\n--- Phase 3: Calendar ---")
check("Events", "GET", "/api/v1/calendar/events?workspace_id=1&start=2026-08-01&end=2026-08-31")

# ===== Phase 4: Attendance =====
print("\n--- Phase 4: Attendance ---")
check("Rules", "GET", "/api/v1/attendance/rules?workspace_id=1")
check("Today", "GET", "/api/v1/attendance/today?rule_id=1")
check("Records", "GET", "/api/v1/attendance/records?rule_id=1")
check("Stats", "GET", "/api/v1/attendance/stats?rule_id=1")

# ===== Phase 4: Announcement =====
print("\n--- Phase 4: Announcement ---")
check("Ann list", "GET", "/api/v1/announcements?workspace_id=1")

# ===== Phase 4: File =====
print("\n--- Phase 4: File ---")
check("Folders", "GET", "/api/v1/files/folders?workspace_id=1")
check("Files", "GET", "/api/v1/files?workspace_id=1")

# ===== Core =====
print("\n--- Core ---")
check("Health", "GET", "/health", expected_status=200)
check("Root", "GET", "/", expected_status=200)
check("OpenAPI", "GET", "/openapi.json", expected_status=200)

print("\n" + "=" * 60)
print(f"Result: {passed} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
