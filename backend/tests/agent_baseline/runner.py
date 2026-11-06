"""P0 基线固化 — Agent 行为用例 Runner

用法（在项目根目录）:
    .venv\\Scripts\\python.exe backend\\tests\\agent_baseline\\runner.py [--case task-001] [--no-clean]

说明：
- 直接在进程内调用 AgentService.chat_stream，收集全部事件后做结构化断言
- 不断言完整文案（LLM 输出不稳定），只断言：工具名命中 / 关键参数 / success / 回复关键词 / 危险操作挂起
- danger 级工具（delete_* / approve / reject）正确行为是「挂起待确认」，用 expect_confirm=true 断言
- 每条用例使用独立 session_id（baseline-{id}-{run_id}），结束后自动清理 MySQL 会话与 Redis 记忆
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal          # noqa: E402
from app.db.redis_client import get_redis        # noqa: E402
from app.models.user import User                 # noqa: E402
from app.modules.agent.service import AgentService  # noqa: E402
from app.modules.agent.tools import register_all_tools  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

CASES_FILE = Path(__file__).parent / "cases.jsonl"
RESULT_FILE = Path(__file__).parent / "last_run.json"
RUN_ID = str(int(time.time()))[-6:]
DEFAULT_USER_ID = 1

_user_cache: dict[int, User] = {}


def get_user(user_id: int) -> User:
    if user_id not in _user_cache:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise RuntimeError(f"测试用户 id={user_id} 不存在")
            db.expunge(user)
            _user_cache[user_id] = user
        finally:
            db.close()
    return _user_cache[user_id]


def load_cases() -> list[dict]:
    cases = []
    for line in CASES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(json.loads(line))
    return cases


def _render(text, run_id: str):
    if isinstance(text, str):
        return text.replace("{run_id}", run_id)
    return text


def _match_args(expected: dict, actual: dict) -> list[str]:
    """关键参数断言：字符串 contains、其余相等比较。返回失败原因列表"""
    errs = []
    for k, v in expected.items():
        av = actual.get(k)
        if isinstance(v, str):
            if av is None or v not in str(av):
                errs.append(f"参数 {k}: 期望包含 {v!r}, 实际 {av!r}")
        else:
            if av != v:
                errs.append(f"参数 {k}: 期望 {v!r}, 实际 {av!r}")
    return errs


async def run_case(case: dict) -> dict:
    cid = case["id"]
    user = get_user(case.get("user_id", DEFAULT_USER_ID))
    workspace_id = case.get("workspace_id")
    session_id = f"baseline-{cid}-{RUN_ID}"
    message = _render(case["message"], RUN_ID)

    svc = AgentService(user=user, workspace_id=workspace_id, session_id=session_id)

    tool_calls: list[dict] = []
    confirms: list[dict] = []
    reply = ""
    full: dict = {}
    error: str | None = None

    try:
        async for ev in svc.chat_stream(message):
            name = ev.get("event")
            data = ev.get("data") or {}
            if name == "tool_call_done":
                tool_calls.append(data.get("tool_call") or {})
            elif name == "confirm_request":
                confirms.append(data)
            elif name == "message":
                reply += str(data)
            elif name == "done":
                full = data.get("_full") or {}
            elif name == "error":
                error = str(data)
    except Exception as e:  # 服务层异常直接判失败
        error = f"{type(e).__name__}: {e}"

    if not reply and full.get("reply"):
        reply = full["reply"]

    # ---------- 断言 ----------
    failures: list[str] = []
    called = [tc.get("tool_name") for tc in tool_calls]

    if error:
        failures.append(f"执行异常: {error}")

    for t in case.get("expect_tools", []):
        if t not in called:
            failures.append(f"工具未命中: {t} (实际调用: {called})")

    for t in case.get("forbidden", []):
        if t in called:
            failures.append(f"调用了禁止的工具: {t}")

    expect_tools = case.get("expect_tools", [])
    if case.get("expect_args") and expect_tools:
        target = next((tc for tc in tool_calls if tc.get("tool_name") == expect_tools[0]), None)
        if target:
            failures += _match_args(_render(case["expect_args"], RUN_ID), target.get("arguments") or {})

    if "expect_success" in case and expect_tools:
        target = next((tc for tc in tool_calls if tc.get("tool_name") == expect_tools[0]), None)
        if target and bool(target.get("success")) != bool(case["expect_success"]):
            result_preview = str(target.get("result"))[:200]
            failures.append(
                f"success 断言失败: 期望 {case['expect_success']}, 实际 {target.get('success')} | {result_preview}"
            )

    if case.get("expect_confirm"):
        hit = any(c.get("tool_name") == expect_tools[0] for c in confirms) if expect_tools else bool(confirms)
        if not hit:
            failures.append(f"危险操作未挂起确认 (confirm_request 事件: {confirms})")

    # 回复关键词：OR 语义 —— 至少命中一个（LLM 措辞不稳定，硬匹配全部关键词会误报）
    kws = case.get("expect_reply_keywords", [])
    if kws and not any(kw in reply for kw in kws):
        failures.append(f"回复未命中任一关键词: {kws} (回复: {reply[:80]!r})")

    return {
        "id": cid,
        "pass": not failures,
        "failures": failures,
        "called_tools": called,
        "tool_success": {tc.get("tool_name"): tc.get("success") for tc in tool_calls},
        "confirm_events": [c.get("tool_name") for c in confirms],
        "reply_preview": reply[:120],
        "model": full.get("model_used"),
    }


def cleanup():
    """清理本次运行产生的 MySQL 会话/消息 与 Redis 记忆 key"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text(
            "DELETE m FROM agent_message m JOIN agent_session s ON m.session_id = s.id "
            "WHERE s.session_key LIKE 'baseline-%'"
        ))
        db.execute(text("DELETE FROM agent_session WHERE session_key LIKE 'baseline-%'"))
        db.commit()
    finally:
        db.close()
    try:
        r = get_redis()
        for key in r.scan_iter("agent:memory:session:baseline-*"):
            r.delete(key)
            r.delete(f"{key}:summary")
    except Exception:
        pass


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="只运行指定 id 的用例")
    parser.add_argument("--no-clean", action="store_true", help="不清理测试会话数据")
    args = parser.parse_args()

    register_all_tools()

    cases = load_cases()
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"未找到用例: {args.case}")
            return 2

    print(f"[Baseline] run_id={RUN_ID}, 共 {len(cases)} 条用例\n")
    results = []
    for i, case in enumerate(cases, 1):
        t0 = time.time()
        try:
            r = await run_case(case)
        except Exception as e:
            r = {"id": case["id"], "pass": False, "failures": [f"runner 异常: {e}"],
                 "called_tools": [], "tool_success": {}, "confirm_events": [], "reply_preview": "", "model": None}
        dt = time.time() - t0
        results.append(r)
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"[{i:02d}/{len(cases)}] {mark} {r['id']} ({dt:.1f}s) tools={r['called_tools']}")
        for f in r["failures"]:
            print(f"         └─ {f}")

    passed = sum(1 for r in results if r["pass"])
    print(f"\n[Baseline] 通过 {passed}/{len(results)}")

    RESULT_FILE.write_text(json.dumps(
        {"run_id": RUN_ID, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
         "passed": passed, "total": len(results), "results": results},
        ensure_ascii=False, indent=2,
    ), encoding="utf-8")
    print(f"[Baseline] 结果已写入 {RESULT_FILE}")

    if not args.no_clean:
        cleanup()
        print("[Baseline] 测试会话数据已清理")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
