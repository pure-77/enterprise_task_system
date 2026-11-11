"""LangGraph 节点实现（P2 / P4）

节点语义与 legacy 主循环逐段对齐：
- route_intent：关键字/LLM 两级意图识别 + 工具集过滤（含降级为全量的兜底）
- agent：调 LLM（DeepSeek 优先、失败降级 Qwen），轮次 +1
- tools：**每个 super-step 只执行一个工具调用**；danger 级走 interrupt() 暂停，等待确认后 resume

为什么 tools 一次只执行一个工具（P4 关键）：
  LangGraph 的 interrupt 在 resume 时会**重放整个节点**。若一个节点内先执行普通工具 A
  （有副作用），再对危险工具 B 调 interrupt，则 resume 重放会把 A 再执行一遍。
  因此改成「一个 super-step 一个工具」，重放时当前节点只有「一个危险工具的确认」，
  interrupt 之前不做任何业务副作用（只写一次幂等的 Redis 映射），A 已落 checkpoint 不会被重跑。

SSE 事件通过 get_stream_writer 以 legacy 相同的事件结构发出，runner 直接转发。
confirm_request 事件不在这里发——由 runner 从 __interrupt__ 信号统一发出，
避免 resume 重放时重复推送确认卡片。
"""
import hashlib
import json
import logging
import time

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from langgraph.types import interrupt

from app.core.config import settings
from app.db.redis_client import get_redis
from app.modules.agent.graph import streaming
from app.modules.agent.legacy.service import _llm_classify_intent, _route_intent
from app.modules.agent.legacy.tool_registry import ToolRegistry

logger = logging.getLogger("agent.graph.nodes")

_CONFIRM_TTL_SECONDS = 300
_CONFIRM_REDIS_PREFIX = "agent:confirm:"


def _exec_ctx(config: RunnableConfig) -> dict:
    return config["configurable"]["exec_ctx"]


def _find_last_ai_with_tool_calls(messages) -> AIMessage | None:
    """倒序找最近一条带 tool_calls 的 AI 消息（tools 节点追加 ToolMessage 后末条不再是 AI）"""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            return m
    return None


def _executed_tool_ids(messages) -> set[str]:
    """已经产出 ToolMessage 的 tool_call_id 集合"""
    return {
        m.tool_call_id
        for m in messages
        if isinstance(m, ToolMessage) and m.tool_call_id
    }


def _judge_success(exec_result: str) -> bool:
    """success 判定逻辑与 legacy 完全一致"""
    try:
        parsed = json.loads(exec_result or "{}")
        if "success" in parsed:
            return bool(parsed["success"])
        if "error" in parsed:
            return False
        return True
    except (json.JSONDecodeError, TypeError):
        return "error" not in (exec_result or "").lower()


def _make_confirm_id(session_key: str, tool_call_id: str) -> str:
    """确定性 confirm_id：resume 重放时保持不变，前端契约仍是 16 位 hex"""
    return hashlib.md5(f"{session_key}:{tool_call_id}".encode()).hexdigest()[:16]


async def _execute_tool(ctx: dict, tool_name: str, parsed_args: dict, iteration: int) -> str:
    """执行工具并采集 trace span（P6）；无 trace 时走原路径，零额外开销"""
    arguments = json.dumps(parsed_args, ensure_ascii=False)
    trace = ctx.get("trace")
    if trace is None:
        return await ToolRegistry.execute(tool_name, arguments, ctx["tool_context"])

    meta = ToolRegistry.get_tool_meta(tool_name) or {}
    with trace.span(
        tool_name, "tool",
        iteration=iteration,
        danger_level=meta.get("danger_level", "safe"),
        argument_keys=sorted(parsed_args.keys()),
    ) as sp:
        result = await ToolRegistry.execute(tool_name, arguments, ctx["tool_context"])
        sp["attrs"]["success"] = _judge_success(result)
        sp["attrs"]["result_preview"] = (result or "")[:200]
        return result


# ---------- 意图识别节点（对齐 legacy Step 2） ----------
async def route_intent(state: dict, config: RunnableConfig):
    ctx = _exec_ctx(config)
    trace = ctx.get("trace")
    t0 = time.time()
    user_message = ctx["message"]

    intent_groups = _route_intent(user_message)
    if intent_groups == "llm_classify":
        intent_groups = await _llm_classify_intent(user_message)

    # 工具集过滤（含 legacy 的各级降级逻辑）
    if not intent_groups:
        tools = ToolRegistry.get_all_schemas()
        intent_group = "all"
    elif len(intent_groups) == 1:
        group = intent_groups[0]
        if group in ("general", "unknown"):
            tools = ToolRegistry.get_all_schemas()
            intent_group = "all"
        else:
            tools = ToolRegistry.get_schemas_by_group(group)
            if not tools:
                logger.warning(f"[Graph] 分组 {group} 无已注册工具，降级为全量 tools")
                tools = ToolRegistry.get_all_schemas()
                intent_group = "all"
            else:
                intent_group = group
    else:
        tools = ToolRegistry.get_schemas_by_groups(intent_groups)
        intent_group = "multi:" + "+".join(intent_groups)
        if not tools:
            logger.warning(f"[Graph] 分组 {intent_groups} 均无已注册工具，降级为全量 tools")
            tools = ToolRegistry.get_all_schemas()
            intent_group = "all"

    logger.info(f"[Graph] intent_group={intent_group}, tools_count={len(tools)}")
    if trace is not None:
        trace.add_span(
            "route_intent", "node", int((time.time() - t0) * 1000),
            attrs={"intent_group": intent_group, "tools_count": len(tools)},
        )

    # 把本轮可用工具清单注入 system prompt（与 legacy 相同的防臆造约束）
    tool_names = [t["function"]["name"] for t in tools]
    sys_prompt = ctx["base_system_prompt"]
    if tool_names:
        sys_prompt += (
            "\n\n【本轮可用工具】\n"
            + ", ".join(tool_names)
            + "\n只允许调用上面列出的工具；如果用户需要的能力不在其中，"
              "请如实告知当前不具备该能力，不要臆造工具名。"
        )

    return {
        "tools": tools,
        "intent_group": intent_group,
        "messages": [SystemMessage(content=sys_prompt, id="sys_prompt")],
    }


# ---------- LLM 节点（对齐 legacy 主循环 LLM 调用 + 降级） ----------
async def agent_node(state: dict, config: RunnableConfig):
    import time as _t
    ctx = _exec_ctx(config)
    writer = get_stream_writer()
    trace = ctx.get("trace")
    tools = state.get("tools") or []
    iteration = state.get("iteration", 0) + 1
    logger.info(f"[Graph] agent 调用 LLM, iteration={iteration}, tools={len(tools)}")

    # 流式调用：边收 token 边推 SSE（token 级打字机），最终累积完整 AIMessage 给 LangGraph State
    llm = ctx["llm"]

    # 手动建 span（不再用 with trace.span 因为流式循环里不方便计时）
    llm_span: dict | None = None
    llm_t0: float | None = None
    if trace is not None:
        llm_t0 = _t.time()
        llm_span = {
            "name": "agent.llm",
            "kind": "llm",
            "offset_ms": int((_t.time() - getattr(trace, "_start_time", _t.time())) * 1000),
            "duration_ms": 0,
            "attrs": {"iteration": iteration, "tools_available": len(tools)},
        }

    try:
        gen = llm.astream_collect(state["messages"], tool_schemas=tools or None)
        async for text_piece in gen:
            if text_piece:
                writer(streaming.message(text_piece))
        resp = llm._last_aimessage
        if resp is None:
            raise RuntimeError("LLM 未返回任何内容")
    finally:
        if llm_span is not None and llm_t0 is not None:
            llm_span["duration_ms"] = int((_t.time() - llm_t0) * 1000)
            trace.spans.append(llm_span)

    if llm_span is not None:
        trace.record_llm_usage(
            llm_span,  # 正确的 span dict，带 attrs 键
            getattr(resp, "usage_metadata", None),
            ctx["llm"].last_model,
            {
                "tools_available": len(tools),
                "tool_calls_requested": len(getattr(resp, "tool_calls", []) or []),
            },
        )

    return {
        "messages": [resp],
        "iteration": iteration,
        "model_used": ctx["llm"].last_model,
    }


def should_continue(state: dict) -> str:
    """agent 之后的条件边：有工具调用且未超轮次 → tools；否则结束"""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None) and state.get("iteration", 0) < settings.AGENT_MAX_TOOL_ITERATIONS:
        return "tools"
    return "end"


def next_tool_step(state: dict) -> str:
    """tools 之后的条件边：同一条 AI 消息还有未执行的工具 → 继续 tools，否则回 agent"""
    last_ai = _find_last_ai_with_tool_calls(state["messages"])
    if last_ai is None:
        return "agent"
    executed = _executed_tool_ids(state["messages"])
    if any(tc.get("id") not in executed for tc in last_ai.tool_calls):
        return "tools"
    return "agent"


# ---------- 工具执行节点（P4：单工具 + danger 走 interrupt） ----------
async def tools_node(state: dict, config: RunnableConfig):
    ctx = _exec_ctx(config)
    writer = get_stream_writer()
    iteration = state.get("iteration", 0)

    last_ai = _find_last_ai_with_tool_calls(state["messages"])
    if last_ai is None:
        logger.warning("[Graph] tools 节点未找到带 tool_calls 的 AI 消息")
        return {}

    executed = _executed_tool_ids(state["messages"])
    pending = [tc for tc in last_ai.tool_calls if tc.get("id") not in executed]
    if not pending:
        return {}

    # 本 super-step 只处理第一个待执行工具（见模块 docstring 的 P4 说明）
    tc = pending[0]
    tool_name = tc["name"]
    parsed_args = tc.get("args") or {}
    meta = ToolRegistry.get_tool_meta(tool_name) or {}
    danger_level = meta.get("danger_level", "safe")

    # ---- danger 级：interrupt 暂停，等待用户确认（P4） ----
    if danger_level == "danger":
        thread_id = ctx.get("thread_id") or ctx["session_key"]
        confirm_id = _make_confirm_id(thread_id, tc["id"])
        pending_action = {
            "confirm_id": confirm_id,
            "session_key": ctx["session_key"],
            "thread_id": thread_id,
            "tool_call_id": tc["id"],
            "user_id": ctx["user"].id,
            "workspace_id": ctx["workspace_id"] or 0,
            "tool_name": tool_name,
            "tool_args": parsed_args,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        # 写 Redis 映射（resume 重放时会重复写同一个 key，幂等；_CONFIRM_TTL 与 legacy 一致）
        try:
            get_redis().setex(
                f"{_CONFIRM_REDIS_PREFIX}{confirm_id}",
                _CONFIRM_TTL_SECONDS,
                json.dumps(pending_action, ensure_ascii=False),
            )
        except Exception as e:
            # Redis 不可用 → 安全降级：拒绝执行危险操作（与 legacy 一致）
            logger.error(f"[Graph] 危险操作挂起失败（Redis 不可用），拒绝执行 {tool_name}: {e}")
            exec_result = json.dumps({
                "success": False,
                "error": "确认服务暂不可用（存储未连接），出于安全考虑该高风险操作未执行，请稍后重试",
            }, ensure_ascii=False)
            record = {
                "tool_name": tool_name,
                "arguments": parsed_args,
                "result": exec_result[:4000],
                "success": False,
            }
            writer(streaming.tool_call_done(record, iteration))
            return {
                "messages": [ToolMessage(content=exec_result, tool_call_id=tc["id"], name=tool_name)],
                "tool_records": [record],
            }

        # 挂起前不发 writer 事件：节点抛出 GraphInterrupt 时本 super-step 的流输出会被丢弃，
        # tool_call_start / confirm_request 统一由 runner 从 __interrupt__ 信号发出。
        # 图在此暂停；resume 时本节点重放，interrupt() 直接返回确认结果
        wait_start = time.time()
        decision = interrupt({
            "confirm_id": confirm_id,
            "tool_name": tool_name,
            "tool_args": parsed_args,
            "meta": meta,
            "expires_in_seconds": _CONFIRM_TTL_SECONDS,
        })
        approved = bool(decision.get("approved")) if isinstance(decision, dict) else False
        if ctx.get("trace") is not None:
            ctx["trace"].add_span(
                "hitl.confirm", "hitl", int((time.time() - wait_start) * 1000),
                attrs={"tool_name": tool_name, "approved": approved, "confirm_id": confirm_id},
            )

        if not approved:
            exec_result = json.dumps({
                "success": False,
                "cancelled": True,
                "tool_name": tool_name,
                "message": "用户已取消该高风险操作，未执行任何变更。",
            }, ensure_ascii=False)
            record = {
                "tool_name": tool_name,
                "arguments": parsed_args,
                "result": exec_result[:4000],
                "success": False,
            }
            writer(streaming.tool_call_done(record, iteration))
            return {
                "messages": [ToolMessage(content=exec_result, tool_call_id=tc["id"], name=tool_name)],
                "tool_records": [record],
            }

        # 已确认 → 真正执行（写操作不重试）
        writer(streaming.tool_call_start(tool_name, iteration, parsed_args))
        exec_result = await _execute_tool(ctx, tool_name, parsed_args, iteration)
        record = {
            "tool_name": tool_name,
            "arguments": parsed_args,
            "result": (exec_result or "")[:4000],
            "success": _judge_success(exec_result),
        }
        writer(streaming.tool_call_done(record, iteration))
        return {
            "messages": [ToolMessage(content=exec_result or "", tool_call_id=tc["id"], name=tool_name)],
            "tool_records": [record],
        }

    # ---- 普通工具：执行并回喂 ----
    writer(streaming.tool_call_start(tool_name, iteration, parsed_args))
    exec_result = await _execute_tool(ctx, tool_name, parsed_args, iteration)
    record = {
        "tool_name": tool_name,
        "arguments": parsed_args,
        "result": (exec_result or "")[:4000],
        "success": _judge_success(exec_result),
    }
    writer(streaming.tool_call_done(record, iteration))
    return {
        "messages": [ToolMessage(content=exec_result or "", tool_call_id=tc["id"], name=tool_name)],
        "tool_records": [record],
    }
