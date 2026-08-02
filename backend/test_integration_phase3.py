"""Phase 3 集成测试 — Approval + Calendar"""
import sys


def test_imports():
    modules = [
        "app.modules.approval.models",
        "app.modules.approval.flow_engine",
        "app.modules.approval.router",
        "app.modules.approval.schemas",
        "app.modules.calendar.models",
        "app.modules.calendar.recurrence",
        "app.modules.calendar.crud",
        "app.modules.calendar.router",
        "app.modules.calendar.schemas",
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


def test_approval_models():
    from app.modules.approval.models import (
        ApprovalTemplate, ApprovalInstance, ApprovalNode, ApprovalCC,
        ApprovalStatus, NodeStatus
    )
    assert ApprovalTemplate.__tablename__ == "approval_templates"
    assert ApprovalInstance.__tablename__ == "approval_instances"
    assert ApprovalStatus.PENDING.value == "pending"
    assert NodeStatus.APPROVED.value == "approved"
    print("  [OK] approval models")


def test_calendar_models():
    from app.modules.calendar.models import Event, EventAttendee, EventReminder
    assert Event.__tablename__ == "events"
    assert EventAttendee.__tablename__ == "event_attendees"
    assert EventReminder.__tablename__ == "event_reminders"
    print("  [OK] calendar models")


def test_recurrence():
    from datetime import datetime
    from app.modules.calendar.recurrence import build_rule_string, parse_recurrence

    rule = build_rule_string("WEEKLY", interval=1, count=4)
    assert "FREQ=WEEKLY" in rule
    assert "COUNT=4" in rule

    start = datetime(2026, 8, 1, 9, 0, 0)
    end = datetime(2026, 8, 31, 23, 59, 59)
    dates = parse_recurrence(rule, start, end)
    assert len(dates) == 4
    print("  [OK] recurrence")


def test_api_routes():
    from app.main import app
    routes = sorted(set(r.path for r in app.routes))

    checks = {
        "approval": ["/api/v1/approval/templates", "/api/v1/approval/instances"],
        "calendar": ["/api/v1/calendar/events"],
        "im": ["/api/v1/im/conversations"],
        "org": ["/api/v1/org/departments"],
    }
    for name, paths in checks.items():
        found = [r for r in routes if any(p in r for p in paths)]
        assert found, f"No {name} routes!"
        print(f"  [OK] {name}: {len(found)} routes")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 3 Integration Tests")
    print("=" * 50)

    results = []

    print("\n[1/5] Module imports")
    p, f = test_imports()
    results.append(("Module imports", p, f))

    print("\n[2/5] Approval models")
    try:
        test_approval_models()
        results.append(("Approval models", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Approval models", 0, 1))

    print("\n[3/5] Calendar models")
    try:
        test_calendar_models()
        results.append(("Calendar models", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Calendar models", 0, 1))

    print("\n[4/5] Recurrence engine")
    try:
        test_recurrence()
        results.append(("Recurrence engine", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Recurrence engine", 0, 1))

    print("\n[5/5] API routes")
    try:
        test_api_routes()
        results.append(("API routes", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("API routes", 0, 1))

    print("\n" + "=" * 50)
    print("Summary:")
    total_passed = sum(r[1] for r in results)
    total_failed = sum(r[2] for r in results)
    for name, p, f in results:
        print(f"  {'[OK]' if f == 0 else '[FAIL]'} {name}")
    print(f"\nTotal: {total_passed} passed, {total_failed} failed")

    sys.exit(0 if total_failed == 0 else 1)
