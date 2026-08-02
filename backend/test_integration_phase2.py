"""Phase 2 集成测试 — IM + Notification + WebSocket"""
import sys


def test_imports():
    """验证所有新模块导入正常"""
    modules = [
        "app.modules.im.models",
        "app.modules.im.crud",
        "app.modules.im.router",
        "app.modules.im.schemas",
        "app.modules.notification.models",
        "app.modules.notification.crud",
        "app.modules.notification.router",
        "app.modules.notification.schemas",
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


def test_im_models():
    """验证 IM 模型定义"""
    from app.modules.im.models import (
        Conversation, ConversationMember, Message, MessageRead,
        ConversationType, MessageType, MemberRole
    )
    assert Conversation.__tablename__ == "conversations"
    assert ConversationMember.__tablename__ == "conversation_members"
    assert Message.__tablename__ == "messages"
    assert MessageRead.__tablename__ == "message_reads"

    # 验证枚举
    assert ConversationType.SINGLE.value == "single"
    assert ConversationType.GROUP.value == "group"
    assert MessageType.TEXT.value == "text"

    # 验证复合主键
    assert MessageRead.__table__.primary_key.columns.keys() == ["message_id", "user_id"]
    print("  [OK] im models")


def test_notification_models():
    """验证通知模型"""
    from app.modules.notification.models import Notification, NotificationSetting, NotificationType
    assert Notification.__tablename__ == "notifications"
    assert NotificationSetting.__tablename__ == "notification_settings"
    assert NotificationType.TASK.value == "task"
    print("  [OK] notification models")


def test_api_routes():
    """验证所有路由注册"""
    from app.main import app
    routes = sorted(set(r.path for r in app.routes))

    checks = {
        "im": ["/api/v1/im/conversations", "/api/v1/im/conversations/{conv_id}/messages"],
        "notification": ["/api/v1/notification/notifications", "/api/v1/notification/settings"],
        "websocket": ["/api/v1/ws"],
        "org": ["/api/v1/org/departments"],
        "task": ["/api/v1/tasks"],
        "auth": ["/api/v1/auth/login"],
    }

    for name, paths in checks.items():
        found = [r for r in routes if any(ep in r for ep in paths)]
        if not found:
            print(f"  [FAIL] No {name} routes!")
            return False
        print(f"  [OK] {name}: {len(found)} routes")

    return True


def test_websocket_publish():
    """验证 WebSocket 发布函数可导入"""
    from app.api.v1.websocket import publish_im_message, publish_notification, publish_task_event
    # 不实际调用 Redis，只验证函数存在
    assert callable(publish_im_message)
    assert callable(publish_notification)
    assert callable(publish_task_event)
    print("  [OK] websocket publishers")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 2 Integration Tests")
    print("=" * 50)

    results = []

    print("\n[1/5] Module imports")
    p, f = test_imports()
    results.append(("Module imports", p, f))

    print("\n[2/5] IM models")
    try:
        test_im_models()
        results.append(("IM models", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("IM models", 0, 1))

    print("\n[3/5] Notification models")
    try:
        test_notification_models()
        results.append(("Notification models", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Notification models", 0, 1))

    print("\n[4/5] API routes")
    try:
        ok = test_api_routes()
        results.append(("API routes", 1 if ok else 0, 0 if ok else 1))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("API routes", 0, 1))

    print("\n[5/5] WebSocket publishers")
    try:
        test_websocket_publish()
        results.append(("WebSocket publishers", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("WebSocket publishers", 0, 1))

    print("\n" + "=" * 50)
    print("Summary:")
    total_passed = sum(r[1] for r in results)
    total_failed = sum(r[2] for r in results)
    for name, p, f in results:
        status = "[OK]" if f == 0 else "[FAIL]"
        print(f"  {status} {name}")
    print(f"\nTotal: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print("\nSome tests failed!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All Phase 2 integration tests passed!")
