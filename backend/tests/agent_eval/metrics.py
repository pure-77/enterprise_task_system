"""P6 评测指标定义

与 P0 基线的区别：基线只判 pass/fail，这里额外量化「质量维度」，用于对比不同引擎/改动：
- Tool Selection Accuracy：该调的工具调了没、有没有多调
- Arg Accuracy：关键参数（title / task_id / deadline 等）是否正确
- Task Success Rate：工具执行是否真正成功（写操作查库语义）
- Avg Turns / P95 Latency：效率与体验
- Hallucinated Tool Rate：是否调用了不存在的工具

所有指标都以「单条用例」为最小单位，避免 LLM 文案波动影响结论。
"""


def analyze_case(
    case: dict,
    tool_calls: list[dict],
    confirms: list[dict],
    reply: str,
    error: str | None,
    latency_ms: int,
    known_tools: set[str] | None = None,
) -> dict:
    """计算单条用例的指标，返回可直接汇总的 dict"""
    expected = list(case.get("expect_tools") or [])
    forbidden = set(case.get("forbidden") or [])
    allow_extra = set(case.get("allow_extra") or [])
    called = [tc.get("tool_name") for tc in tool_calls if tc.get("tool_name")]
    called_set = set(called)

    # 臆造工具：调了不在 ToolRegistry 里的名字
    hallucinated = sorted(called_set - known_tools) if known_tools else []

    # 工具选择（对齐 P0 基线语义）：期望工具全中 + 无禁止 + 无臆造
    # 「多调」单独作为 over-call 指标统计，不与 selection 混在一起（否则把合理的多步查询误判为错误）
    if case.get("expect_no_tools"):
        selection_ok = not called and not error
        extras = []
    else:
        extras = sorted(called_set - set(expected) - allow_extra)
        selection_ok = (
            error is None
            and all(t in called_set for t in expected)
            and not (forbidden & called_set)
            and not hallucinated
        )

    # 参数准确率：只对「有 expect_args 且命中了目标工具」的用例计算
    arg_ok = None
    if expected and case.get("expect_args"):
        target = next((tc for tc in tool_calls if tc.get("tool_name") == expected[0]), None)
        if target is not None:
            arg_ok = True
            for k, v in case["expect_args"].items():
                actual = (target.get("arguments") or {}).get(k)
                if isinstance(v, str):
                    if actual is None or v not in str(actual):
                        arg_ok = False
                elif actual != v:
                    arg_ok = False

    # 任务完成率：优先看工具执行 success，其次回复关键词 / 挂起确认
    success_ok = None
    if "expect_success" in case and expected:
        target = next((tc for tc in tool_calls if tc.get("tool_name") == expected[0]), None)
        if target is not None:
            success_ok = bool(target.get("success")) == bool(case["expect_success"])
    elif case.get("expect_confirm"):
        success_ok = bool(confirms)
    elif case.get("expect_reply_keywords"):
        success_ok = any(k in (reply or "") for k in case["expect_reply_keywords"])

    turns = max([int(tc.get("iteration") or 0) for tc in tool_calls] or [0])

    return {
        "id": case["id"],
        "group": case.get("group", "unknown"),
        "selection_ok": bool(selection_ok),
        "arg_ok": arg_ok,
        "success_ok": success_ok,
        "hallucinated": hallucinated,
        "expected": expected,
        "called": called,
        "extra": extras,
        "turns": turns,
        "latency_ms": latency_ms,
        "error": error,
        "reply_preview": (reply or "")[:120],
    }


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    values = sorted(values)
    idx = min(len(values) - 1, int(len(values) * 0.95))
    return values[idx]


def summarize(results: list[dict]) -> dict:
    """汇总指标（只统计有意义的用例，避免分母为 0）"""
    total = len(results)
    sel = [r for r in results if r["selection_ok"] is not None]
    arg = [r for r in results if r["arg_ok"] is not None]
    suc = [r for r in results if r["success_ok"] is not None]
    lat = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    turns = [r["turns"] for r in results]

    def ratio(ok_count: int, denom: int):
        """无分母时返回 None（报表显示 n/a），避免把「未评估」误读成 0%"""
        return round(ok_count / denom, 3) if denom else None

    return {
        "total": total,
        "tool_selection_accuracy": ratio(sum(1 for r in sel if r["selection_ok"]), len(sel)),
        "arg_accuracy": ratio(sum(1 for r in arg if r["arg_ok"]), len(arg)),
        "task_success_rate": ratio(sum(1 for r in suc if r["success_ok"]), len(suc)),
        "over_call_rate": ratio(sum(1 for r in results if r["extra"]), total),
        "hallucinated_tool_rate": ratio(sum(1 for r in results if r["hallucinated"]), total),
        "avg_turns": round(sum(turns) / total, 2) if total else 0.0,
        "avg_latency_ms": int(sum(lat) / len(lat)) if lat else 0,
        "p95_latency_ms": _p95(lat),
        "error_rate": ratio(sum(1 for r in results if r["error"]), total),
    }


def diff_against(baseline: dict, current: list[dict]) -> dict:
    """与上一次评测结果对比：找出回退（pass→fail）与修复（fail→pass）"""
    prev = {r["id"]: r for r in (baseline.get("results") or [])}
    regressions, fixes = [], []
    for r in current:
        p = prev.get(r["id"])
        if not p:
            continue
        was = bool(p.get("selection_ok"))
        now = bool(r.get("selection_ok"))
        if was and not now:
            regressions.append({"id": r["id"], "was": p.get("called"), "now": r.get("called")})
        elif not was and now:
            fixes.append({"id": r["id"], "was": p.get("called"), "now": r.get("called")})
    return {"regressions": regressions, "fixes": fixes,
            "baseline_time": baseline.get("time"), "baseline_total": baseline.get("summary", {}).get("total")}
