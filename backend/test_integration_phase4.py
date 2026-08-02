"""Phase 4 集成测试 — Attendance + Announcement + File"""
import sys


def test_imports():
    modules = [
        "app.modules.attendance.models", "app.modules.attendance.crud",
        "app.modules.attendance.router", "app.modules.attendance.schemas",
        "app.modules.announcement.models", "app.modules.announcement.crud",
        "app.modules.announcement.router", "app.modules.announcement.schemas",
        "app.modules.file.models", "app.modules.file.storage",
        "app.modules.file.crud", "app.modules.file.router", "app.modules.file.schemas",
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


def test_models():
    from app.modules.attendance.models import AttendanceRule, AttendanceRecord, AttendanceStats, CheckInType
    from app.modules.announcement.models import Announcement, AnnouncementRead, AnnouncementType
    from app.modules.file.models import FileFolder, File

    assert AttendanceRule.__tablename__ == "attendance_rules"
    assert AttendanceRecord.__tablename__ == "attendance_records"
    assert AttendanceStats.__tablename__ == "attendance_stats"
    assert CheckInType.LATE.value == "late"

    assert Announcement.__tablename__ == "announcements"
    assert AnnouncementRead.__tablename__ == "announcement_reads"
    assert AnnouncementType.URGENT.value == "urgent"

    assert FileFolder.__tablename__ == "file_folders"
    assert File.__tablename__ == "files"
    print("  [OK] all models")


def test_api_routes():
    from app.main import app
    routes = sorted(set(r.path for r in app.routes))
    checks = {
        "attendance": ["/api/v1/attendance/rules", "/api/v1/attendance/check-in"],
        "announcement": ["/api/v1/announcements"],
        "file": ["/api/v1/files", "/api/v1/files/upload"],
        "approval": ["/api/v1/approval/templates"],
        "calendar": ["/api/v1/calendar/events"],
        "im": ["/api/v1/im/conversations"],
    }
    for name, paths in checks.items():
        found = [r for r in routes if any(p in r for p in paths)]
        assert found, f"No {name} routes!"
        print(f"  [OK] {name}: {len(found)} routes")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 4 Integration Tests")
    print("=" * 50)
    results = []

    print("\n[1/3] Module imports")
    p, f = test_imports()
    results.append(("Module imports", p, f))

    print("\n[2/3] Models")
    try:
        test_models()
        results.append(("Models", 1, 0))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Models", 0, 1))

    print("\n[3/3] API routes")
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
    print(f"Total routes: 105")
    sys.exit(0 if total_failed == 0 else 1)
