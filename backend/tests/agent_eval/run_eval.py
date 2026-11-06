"""P6 评测 Runner —— 一键跑评测并输出 markdown 对比报表

用法（项目根目录，cwd 必须是 backend 以便加载 .env）：
    .venv\\Scripts\\python.exe backend\\tests\\agent_eval\\run_eval.py
    .venv\\Scripts\\python.exe backend\\tests\\agent_eval\\run_eval.py --engine langgraph --group composite
    .venv\\Scripts\\python.exe backend\\tests\\agent_eval\\run_eval.py --case e-neg-001

用例来源：
- backend/tests/agent_baseline/cases.jsonl  （P0 基线 47 条，直接复用）
- backend/tests/agent_eval/cases.jsonl      （P6 扩充用例，合计 ≥80 条）

产出：
- backend/tests/agent_eval/reports/eval-<YYYYmmdd-HHMMSS>.md   （可视化报表）
- backend/tests/agent_eval/last_eval.json                      （机读结果，供下次对比）
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ---- 必须在导入 app 模块之前决定引擎（pydantic-settings 在 import 时读取 env）----
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--engine", default=None)
_known, _ = _pre.parse_known_args()
if _known.engine:
    os.environ["AGENT_ENGINE"] = _known.engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))
EVAL_DIR = Path(__file__).parent
sys.path.insert(0, str(EVAL_DIR))  # tests 目录没有 __init__.py，直接按文件名导入 metrics

from app.core.config import settings            # noqa: E402
from app.db.redis_client import get_redis        # noqa: E402
from app.db.session import SessionLocal          # noqa: E402
from app.models.user import User                 # noqa: E402
from app.modules.agent.legacy.tool_registry import ToolRegistry  # noqa: E402
from app.modules.agent.service import AgentService  # noqa: E402
from app.modules.agent.tools import register_all_tools  # noqa: E402
from metrics import analyze_case, diff_against, summarize  # noqa: E402

BASELINE_CASES = EVAL_DIR.parent / "agent_baseline" / "cases.jsonl"
EXTRA_CASES = EVAL_DIR / "cases.jsonl"
REPORT_DIR = EVAL_DIR / "reports"
RESULT_FILE = EVAL_DIR / "last_eval.json"

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


def _load_file(path: Path, source: str) -> list[dict]:
    cases = []
    if not path.exists():
        return cases
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        case = json.loads(line)
        case["_source"] = source
        cases.append(case)
    return cases


def load_cases() -> list[dict]:
    """复用 P0 基线用例 + 扩充用例（id 重复时以扩充用例为准）"""
    merged: dict[str, dict] = {}
    for c in _load_file(BASELINE_CASES, "baseline") + _load_file(EXTRA_CASES, "eval"):
        merged[c["id"]] = c
    return list(merged.values())


def render(value, run_id: str):
    if isinstance(value, str):
        return value.replace("{run_id}", run_id)
    if isinstance(value, list):
        return [render(v, run_id) for v in value]
    if isinstance(value, dict):
        return {k: render(v, run_id) for k, v in value.items()}
    return value


async def run_case(case: dict) -> tuple[dict, dict]:
    """执行单条用例，返回 (metrics 结果, 原始明细)"""
    cid = case["id"]
    user = get_user(case.get("user_id", DEFAULT_USER_ID))
    message = render(case["message"], RUN_ID)
    session_id = f"eval-{cid}-{RUN_ID}"

    svc = AgentService(user=user, workspace_id=case.get("workspace_id"), session_id=session_id)

    tool_calls: list[dict] = []
    confirms: list[dict] = []
    reply = ""
    error: str | None = None
    t0 = time.time()
    try:
        async for ev in svc.chat_stream(message):
            name = ev.get("event")
            data = ev.get("data") or {}
            if name == "tool_call_done":
                tc = dict(data.get("tool_call") or {})
                # iteration 在事件层，工具记录里没有 —— 轮次指标靠它计算
                tc["iteration"] = data.get("iteration", 0)
                tool_calls.append(tc)
            elif name == "confirm_request":
                confirms.append(data)
            elif name == "message":
                reply += str(data)
            elif name == "done":
                if not reply:
                    reply = ((data.get("_full") or {}).get("reply") or "")
            elif name == "error":
                error = str(data)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    latency_ms = int((time.time() - t0) * 1000)

    case = render(case, RUN_ID)
    known = {t["name"] for t in ToolRegistry.list_tools()} if hasattr(ToolRegistry, "list_tools") else None
    metrics = analyze_case(case, tool_calls, confirms, reply, error, latency_ms, known)
    raw = {
        "id": cid,
        "source": case.get("_source"),
        "group": case.get("group"),
        "message": message,
        "tool_success": {tc.get("tool_name"): tc.get("success") for tc in tool_calls},
        "confirm_events": [c.get("tool_name") for c in confirms],
        "reply_preview": reply[:150],
    }
    return metrics, raw


def _failure_reason(r: dict) -> str:
    reasons = []
    if r["error"]:
        reasons.append(f"异常: {r['error']}")
    if r["selection_ok"] is False:
        reasons.append(f"期望 {r['expected'] or '不调工具'} / 实际 {r['called']}")
    if r["arg_ok"] is False:
        reasons.append("关键参数不符")
    if r["success_ok"] is False:
        reasons.append("执行结果不符合预期")
    if r["hallucinated"]:
        reasons.append(f"臆造工具 {r['hallucinated']}")
    return "; ".join(reasons) or "-"


def _fmt_pct(value) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def build_markdown(results: list[dict], summary: dict, diff: dict, engine: str) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Agent 评测报告",
        "",
        f"- 时间：{ts}",
        f"- 引擎：`{engine}`（checkpointer=`{settings.AGENT_CHECKPOINTER}`）",
        f"- 用例：{summary['total']} 条（基线复用 + P6 扩充）",
        "",
        "## 总览",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| Tool Selection Accuracy | {_fmt_pct(summary['tool_selection_accuracy'])} |",
        f"| Arg Accuracy | {_fmt_pct(summary['arg_accuracy'])} |",
        f"| Task Success Rate | {_fmt_pct(summary['task_success_rate'])} |",
        f"| Over-call Rate | {_fmt_pct(summary.get('over_call_rate'))} |",
        f"| Hallucinated Tool Rate | {_fmt_pct(summary['hallucinated_tool_rate'])} |",
        f"| Avg Turns | {summary['avg_turns']} |",
        f"| Avg Latency | {summary['avg_latency_ms']} ms |",
        f"| P95 Latency | {summary['p95_latency_ms']} ms |",
        f"| Error Rate | {_fmt_pct(summary['error_rate'])} |",
        "",
        "## 分组表现",
        "",
        "| group | 用例 | 选择正确 | 成功 | 平均轮次 |",
        "|---|---|---|---|---|",
    ]

    groups: dict[str, list[dict]] = {}
    for r in results:
        groups.setdefault(r["group"] or "unknown", []).append(r)
    for g, rs in sorted(groups.items()):
        sel = sum(1 for r in rs if r["selection_ok"])
        evald = [r for r in rs if r["success_ok"] is not None]
        suc_text = f"{sum(1 for r in evald if r['success_ok']) / len(evald):.0%}" if evald else "n/a"
        avg_turns = sum(r["turns"] for r in rs) / len(rs)
        lines.append(f"| {g} | {len(rs)} | {sel}/{len(rs)} | {suc_text} | {avg_turns:.1f} |")

    fails = [r for r in results if not r["selection_ok"] or r["error"] or r["success_ok"] is False]
    lines += ["", f"## 未通过明细（{len(fails)} 条）", ""]
    if fails:
        lines += ["| id | group | 期望 | 实际 | 原因 |", "|---|---|---|---|---|"]
        for r in fails:
            lines.append(
                f"| {r['id']} | {r['group']} | {r['expected'] or '-'} | {r['called'] or '-'} | {_failure_reason(r)} |"
            )
    else:
        lines.append("无")

    over = [r for r in results if r["extra"]]
    lines += ["", f"## 多调用例（{len(over)} 条，selection 仍计为正确）", ""]
    if over:
        lines += ["| id | 期望 | 多调用了 |", "|---|---|---|"]
        for r in over:
            lines.append(f"| {r['id']} | {r['expected']} | {r['extra']} |")
    else:
        lines.append("无")

    lines += ["", "## 与上一次对比", ""]
    if not diff.get("baseline_time"):
        lines.append("上一次无可用结果（首次运行）")
    else:
        regs, fixes = diff.get("regressions") or [], diff.get("fixes") or []
        lines.append(f"- 基准：{diff['baseline_time']}（{diff.get('baseline_total')} 条）")
        lines.append(f"- 回退：{len(regs)} 条" + (f" → {', '.join(r['id'] for r in regs)}" if regs else ""))
        lines.append(f"- 修复：{len(fixes)} 条" + (f" → {', '.join(r['id'] for r in fixes)}" if fixes else ""))

    return "\n".join(lines) + "\n"


def cleanup():
    """清理本次评测产生的 MySQL 会话/消息 与 Redis 记忆 key"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text(
            "DELETE m FROM agent_message m JOIN agent_session s ON m.session_id = s.id "
            "WHERE s.session_key LIKE 'eval-%'"
        ))
        db.execute(text("DELETE FROM agent_session WHERE session_key LIKE 'eval-%'"))
        db.commit()
    finally:
        db.close()
    try:
        r = get_redis()
        for key in r.scan_iter("agent:memory:session:eval-*"):
            r.delete(key)
            r.delete(f"{key}:summary")
    except Exception:
        pass


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["legacy", "langgraph"], help="覆盖 AGENT_ENGINE")
    parser.add_argument("--group", help="只跑指定分组")
    parser.add_argument("--case", help="只跑指定用例 id")
    parser.add_argument("--limit", type=int, help="最多跑 N 条（快速冒烟）")
    parser.add_argument("--no-clean", action="store_true", help="不清理测试会话数据")
    parser.add_argument("--no-diff", action="store_true", help="不与上一次结果对比")
    args = parser.parse_args()

    register_all_tools()

    cases = load_cases()
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
    if args.group:
        cases = [c for c in cases if c.get("group") == args.group]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        print("没有匹配的用例")
        return 2

    engine = settings.AGENT_ENGINE
    print(f"[Eval] engine={engine}, cases={len(cases)}, run_id={RUN_ID}\n")

    results: list[dict] = []
    raws: list[dict] = []
    for i, case in enumerate(cases, 1):
        try:
            m, raw = await run_case(case)
        except Exception as e:
            m = {"id": case["id"], "group": case.get("group"), "selection_ok": False,
                 "arg_ok": None, "success_ok": False, "hallucinated": [], "expected": [],
                 "called": [], "extra": [], "turns": 0, "latency_ms": 0,
                 "error": f"runner 异常: {e}", "reply_preview": ""}
            raw = {"id": case["id"], "group": case.get("group")}
        results.append(m)
        raws.append(raw)
        mark = "PASS" if m["selection_ok"] else "FAIL"
        print(f"[{i:02d}/{len(cases)}] {mark} {m['id']} ({m['latency_ms']}ms) "
              f"expected={m['expected']} called={m['called']}")

    summary = summarize(results)

    prev = None
    if RESULT_FILE.exists() and not args.no_diff:
        try:
            prev = json.loads(RESULT_FILE.read_text(encoding="utf-8"))
        except Exception:
            prev = None
    diff = diff_against(prev or {}, results)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"eval-{time.strftime('%Y%m%d-%H%M%S')}.md"
    markdown = build_markdown(results, summary, diff, engine)
    report_path.write_text(markdown, encoding="utf-8")

    RESULT_FILE.write_text(json.dumps({
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_id": RUN_ID,
        "engine": engine,
        "summary": summary,
        "results": results,
        "raw": raws,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + markdown)
    print(f"[Eval] 报表: {report_path}")
    print(f"[Eval] 机读结果: {RESULT_FILE}")

    if not args.no_clean:
        cleanup()
        print("[Eval] 测试会话数据已清理")

    return 0 if summary["tool_selection_accuracy"] >= 0.9 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
