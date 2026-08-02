"""Phase 1 集成测试 — 验证所有功能正常"""
import sys


def test_imports():
    """验证所有模块导入正常"""
    modules = [
        "app.main",
        "app.core.config",
        "app.core.security",
        "app.core.exceptions",
        "app.db.session",
        "app.db.redis_client",
        "app.modules.task.models",
        "app.modules.task.router",
        "app.modules.org.models",
        "app.modules.org.crud",
        "app.modules.org.router",
        "app.modules.org.schemas",
        "app.middleware.response_handler",
        "app.middleware.audit_log",
        "app.shared.response",
    ]
    passed, failed = 0, 0
    for mod in modules:
        try:
            __import__(mod)
            print(f"  [OK] {mod}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {mod}: {e}")
            failed += 1
    return passed, failed


def test_response_utils():
    """验证统一响应工具"""
    from app.shared.response import success_response, error_response, paginated_response
    assert success_response({"x": 1})["code"] == 0
    assert error_response(40401, "Not found")["code"] == 40401
    page = paginated_response([], 100, 1, 20)
    assert page["data"]["total_pages"] == 5
    print("  [OK] response_utils")


def test_exceptions():
    """验证新旧异常类"""
    from app.core.exceptions import (
        ResourceNotFoundError, PermissionDeniedError, UnauthorizedError,
        NotFoundException, EmailAlreadyExistsException,
    )
    e1 = ResourceNotFoundError(resource="部门")
    assert e1.code == 40401
    assert "部门" in e1.err_message
    e2 = PermissionDeniedError()
    assert e2.code == 40301
    e3 = UnauthorizedError()
    assert e3.code == 40101
    # 旧版兼容
    e4 = NotFoundException()
    assert e4.status_code == 404
    e5 = EmailAlreadyExistsException()
    assert e5.status_code == 409
    print("  [OK] exceptions")


def test_org_models():
    """验证 Organization 模型定义"""
    from app.modules.org.models import Department, Position, AuditLog
    assert Department.__tablename__ == "departments"
    assert Position.__tablename__ == "positions"
    assert AuditLog.__tablename__ == "audit_logs"
    print("  [OK] org models")


def test_api_routes():
    """验证 API 路由注册"""
    from app.main import app
    routes = sorted(set(r.path for r in app.routes))

    checks = {
        "org": ["/api/v1/org/departments", "/api/v1/org/positions", "/api/v1/org/members"],
        "task": ["/api/v1/tasks"],
        "auth": ["/api/v1/auth/login", "/api/v1/auth/register"],
        "health": ["/health"],
    }

    for name, expected_paths in checks.items():
        found = [r for r in routes if any(ep in r for ep in expected_paths)]
        print(f"  {name}: {len(found)} routes")
        if not found:
            print(f"    [FAIL] No {name} routes found!")
            return False

    print("  [OK] api routes")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1 Integration Tests")
    print("=" * 50)

    results = []

    print("\n[1/5] Module imports")
    p, f = test_imports()
    results.append(("Module imports", p, f))

    print("\n[2/5] Response utils")
    try:
        test_response_utils()
        results.append(("Response utils", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Response utils", 0, 1))

    print("\n[3/5] Exceptions")
    try:
        test_exceptions()
        results.append(("Exceptions", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Exceptions", 0, 1))

    print("\n[4/5] Org models")
    try:
        test_org_models()
        results.append(("Org models", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Org models", 0, 1))

    print("\n[5/5] API routes")
    try:
        ok = test_api_routes()
        results.append(("API routes", 1 if ok else 0, 0 if ok else 1))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("API routes", 0, 1))

    print("\n" + "=" * 50)
    print("Summary:")
    total_passed = sum(r[1] for r in results)
    total_failed = sum(r[2] for r in results)
    for name, p, f in results:
        status = "[OK]" if f == 0 else "[FAIL]"
        print(f"  {status} {name}")
    print(f"\nTotal: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print("\n[FAIL] Some tests failed!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All Phase 1 integration tests passed!")
