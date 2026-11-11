"""LangGraph 引擎运行器（P2）

对外契约与 legacy AgentService 完全一致：
- chat_stream：yield 同样的 tool_call_start / tool_call_done / confirm_request / message / done 事件
- chat：聚合为 AgentChatResponse
- 记忆加载/保存、MySQL 会话持久化、审计日志：与 legacy 相同语义

差异点（有意收敛）：
- 编排主循环由图拓扑承担（route_intent → agent ⇄ tools）
- 图片多模态（image_url）暂不在迁移范围，直接委托 legacy 引擎执行
"""
import json
import logging
import time
import uuid
import asyncio
from datetime import datetime
from typing import Optional

import anyio
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Command

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.agent_audit import AgentAuditLog
from app.models.user import User
from app.modules.agent.graph import streaming
from app.modules.agent.graph.builder import build_graph
from app.modules.agent.graph.checkpointer import get_checkpointer
from app.modules.agent.graph.llm import ChatLLMWithFallback
from app.modules.agent.graph.trace import TraceRecorder
from app.modules.agent.memory import AgentMemory, build_ops_digest, format_ops_context
from app.modules.agent.long_memory import extract_and_store, retrieve_context
from app.modules.agent.store import get_store
from app.modules.agent.schemas import AgentChatResponse, AgentToolCall
from app.modules.agent.session_service import AgentSessionService

logger = logging.getLogger("agent.graph.runner")

_CONFIRM_TTL_SECONDS = 300
_CONFIRM_PENDING_REPLY = (
    "该操作属于高风险操作，已暂停等待你在确认卡片上确认。"
    "确认后才会执行；取消或 5 分钟内未处理则不会执行。"
)


async def _delete_thread(checkpointer, thread_id: str) -> None:
    """清理本轮 thread 的图状态（未中断的轮次用完即弃，避免 InMemorySaver 无限增长）"""
    if checkpointer is None:
        return
    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception as e:
        logger.debug(f"[Graph] 清理 thread={thread_id} 失败（忽略）: {e}")


def _history_to_lc(h: dict):
    """把 Redis 记忆里的 OpenAI 格式消息转成 LangChain Message（结构同 legacy 清洗后数据）"""
    role = h.get("role")
    if role == "system":
        return SystemMessage(content=h.get("content") or "")
    if role == "user":
        return HumanMessage(content=h.get("content") or "")
    if role == "assistant":
        kwargs = {}
        tcs = h.get("tool_calls") or []
        if tcs:
            converted = []
            for tc in tcs:
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except Exception:
                    args = {}
                converted.append({"id": tc["id"], "name": tc["function"]["name"], "args": args})
            kwargs["tool_calls"] = converted
        return AIMessage(content=h.get("content") or "", **kwargs)
    if role == "tool":
        return ToolMessage(content=h.get("content") or "", tool_call_id=h.get("tool_call_id") or "")
    return None


def _build_system_prompt(user: User, workspace_id: Optional[int]) -> str:
    """构造 system prompt（含时间/用户/空间上下文），chat 与 resume 共用"""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return settings.AGENT_SYSTEM_PROMPT + f"""

【上下文】
- 现在时间: {now.strftime('%Y-%m-%d %H:%M:%S')} ({weekdays[now.weekday()]})
- 用户ID: {user.id}
- 当前操作空间: workspace_id={workspace_id} (0=个人模式)
- 日期推断: 用户说"明天"=今天+1天, "后天"=+2天, "下周"=本周一+7天, 直接使用上面的"现在时间"推算即可, 不要询问用户。
- 时间推断: 用户说"6点"/"下午6点"=18:00, "早上6点"=06:00, "中午12点"=12:00。
- 所有工具调用都在这个空间范围内执行，无需询问用户要在哪个空间操作。"""


class LangGraphAgentService:
    """LangGraph 版 Agent 服务（与 legacy 同签名、同事件流）"""

    def __init__(
        self,
        user: User,
        workspace_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ):
        self.user = user
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.memory = AgentMemory(workspace_id, user.id, session_id)
        self.context = {"user": user, "workspace_id": workspace_id}

    async def chat(self, user_message: str, image_url: Optional[str] = None) -> AgentChatResponse:
        final_reply = ""
        final_data = None
        final_tool_calls: list[AgentToolCall] = []

        async for event in self.chat_stream(user_message, image_url):
            ev = event["event"]
            if ev == "tool_call_done":
                final_tool_calls.append(AgentToolCall(**event["data"]["tool_call"]))
            elif ev == "message":
                final_reply += event["data"]
            elif ev == "done":
                final_data = event["data"]["_full"]

        if final_data is None:
            return AgentChatResponse(
                reply=final_reply or "抱歉，处理失败，请重试。",
                tool_calls=final_tool_calls,
                session_id=self.session_id or f"user:{self.user.id}",
                model_used="unknown",
            )

        return AgentChatResponse(
            reply=final_data["reply"],
            tool_calls=final_tool_calls or [AgentToolCall(**tc) for tc in final_data["tool_calls"]],
            thinking=final_data["thinking"],
            session_id=final_data["session_id"],
            model_used=final_data["model_used"],
        )

    async def chat_stream(self, user_message: str, image_url: Optional[str] = None):
        # 多模态图片走 legacy（VL 链路不在本次迁移范围）
        if image_url:
            from app.modules.agent.legacy.service import AgentService as LegacyAgentService
            legacy = LegacyAgentService(self.user, self.workspace_id, self.session_id)
            async for event in legacy.chat_stream(user_message, image_url):
                yield event
            return

        start_time = time.time()
        thinking_fragments: list[str] = []
        max_iterations = settings.AGENT_MAX_TOOL_ITERATIONS

        # ---------- Step 1: 加载记忆 + 构造初始 messages（同 legacy） ----------
        history = await self.memory.load_with_summary()
        base_system_prompt = _build_system_prompt(self.user, self.workspace_id)

        # 历史清洗逻辑与 legacy 相同（必须有合法 role，剔除损坏的 tool_calls 结构）
        VALID_ROLES = {"system", "user", "assistant", "tool"}
        cleaned_history = []
        for h in history:
            if not isinstance(h, dict) or h.get("role") not in VALID_ROLES:
                continue
            if h["role"] == "assistant" and h.get("tool_calls"):
                valid_tcs = [
                    tc for tc in h["tool_calls"]
                    if (isinstance(tc, dict) and tc.get("id") and tc.get("type") == "function"
                        and isinstance(tc.get("function"), dict) and tc["function"].get("name"))
                ]
                if valid_tcs:
                    h["tool_calls"] = valid_tcs
                elif "tool_calls" in h:
                    del h["tool_calls"]
            cleaned_history.append(h)

        # 上轮工具调用记录（Redis 短期记忆里的 ops 字段）并入 system prompt，
        # 让模型跨轮能看到"上一轮实际查了什么、拿到什么"，避免因上下文空缺而自我怀疑。
        # 放在 base_system_prompt 里，route_intent 替换 system 消息时才不会丢。
        ops_context = format_ops_context(cleaned_history)
        if ops_context:
            base_system_prompt = f"{base_system_prompt}\n\n{ops_context}"

        # 跨会话长期记忆：按当前问题语义检索该用户的稳定信息（偏好/身份/明确要求记住的事）
        memory_context = await retrieve_context(self.user.id, user_message)
        if memory_context:
            base_system_prompt = f"{base_system_prompt}\n\n{memory_context}"

        messages = [SystemMessage(content=base_system_prompt, id="sys_prompt")]
        for h in cleaned_history:
            lc = _history_to_lc(h)
            if lc is not None:
                messages.append(lc)
        messages.append(HumanMessage(content=user_message))

        # ---------- Step 2~4: 交给图执行（route_intent → agent ⇄ tools） ----------
        resolved_session_key = self.session_id or f"user:{self.user.id}"
        # P4: 每轮对话使用独立 thread_id。
        # 原因：interrupt 会让该 thread 的 state 以「AIMessage(tool_calls) 无配对 ToolMessage」结尾，
        # 若下一轮复用同一 thread，OpenAI 会报 400。会话连续性由 MySQL/Redis 记忆保证，
        # checkpoint 只服务于「本轮中断 → 确认恢复」。
        thread_id = f"{resolved_session_key}#{uuid.uuid4().hex[:10]}"
        llm = ChatLLMWithFallback()
        # P6: 全链路 trace（节点 / LLM token / 工具耗时），落盘 JSONL，失败不影响主流程
        trace = TraceRecorder(
            user_id=self.user.id,
            workspace_id=self.workspace_id,
            session_id=resolved_session_key,
            engine="langgraph",
            message=user_message,
        )
        exec_ctx = {
            "user": self.user,
            "workspace_id": self.workspace_id,
            "session_key": resolved_session_key,
            "thread_id": thread_id,
            "message": user_message,
            "base_system_prompt": base_system_prompt,
            "tool_context": self.context,
            "llm": llm,
            "trace": trace,
        }
        # P3: 接入 checkpointer，thread_id 每轮独立（见上）
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer, store=get_store())
        config = {
            "configurable": {"thread_id": thread_id, "exec_ctx": exec_ctx},
            # P4: tools 每个 super-step 只跑一个工具，递归上限需按工具数放大
            "recursion_limit": max_iterations * 8 + 10,
        }
        graph_input_messages = messages

        final_state: dict = {}
        graph_error: Optional[Exception] = None
        interrupted = False
        pending_confirms: list[dict] = []
        pending_records: list[dict] = []

        # ---------- 立即让 SSE 有第一个字节 + 后台心跳 ----------
        # graph.astream 内部 route_intent + agent_node.ainvoke 同步阻塞期间，
        # 前端必须持续收到事件才不会只显示"正在思考..."。
        yield streaming.heartbeat()
        hb_queue: asyncio.Queue[dict] = asyncio.Queue()
        hb_stop = asyncio.Event()

        async def _heartbeat_loop():
            while not hb_stop.is_set():
                try:
                    hb_queue.put_nowait(streaming.heartbeat())
                except asyncio.QueueFull:
                    pass
                await asyncio.sleep(0.4)

        hb_task = asyncio.create_task(_heartbeat_loop())

        try:
            async for mode, chunk in graph.astream(
                {"messages": graph_input_messages, "iteration": 0, "tool_records": []},
                config=config,
                stream_mode=["values", "custom", "updates"],
            ):
                # ---------- Drain heartbeat queue（graph 事件之间确保心跳能及时下发） ----------
                while not hb_queue.empty():
                    try:
                        yield hb_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                if mode == "values":
                    final_state = chunk
                elif mode == "updates":
                    # P4: 图因 interrupt 暂停 → 在这里统一发确认卡片。
                    # 放在流处理层而非节点内，resume 重放节点时不会重复推送。
                    raw = chunk.get("__interrupt__") if isinstance(chunk, dict) else None
                    if raw:
                        interrupted = True
                        iteration = final_state.get("iteration", 0)
                        for item in raw:
                            payload = getattr(item, "value", item)
                            if not isinstance(payload, dict) or not payload.get("confirm_id"):
                                continue
                            pending_confirms.append(payload)
                            # 与 legacy 事件顺序一致：先 tool_call_start，再 confirm_request
                            yield streaming.tool_call_start(
                                payload["tool_name"],
                                iteration,
                                payload.get("tool_args") or {},
                            )
                            yield streaming.confirm_request(
                                payload["confirm_id"],
                                payload["tool_name"],
                                payload.get("tool_args") or {},
                                payload.get("meta") or {},
                                payload.get("expires_in_seconds", _CONFIRM_TTL_SECONDS),
                            )
                            # pending 记录不落 checkpoint（interrupt 前的 super-step 更新被丢弃），
                            # 这里补齐一条与 legacy 完全一致的挂起记录
                            pending_result = json.dumps({
                                "success": False,
                                "pending_confirmation": True,
                                "confirm_id": payload["confirm_id"],
                                "tool_name": payload["tool_name"],
                                "expires_in_seconds": payload.get("expires_in_seconds", _CONFIRM_TTL_SECONDS),
                                "message": "该操作为高风险操作，已暂停并等待用户在确认卡片上确认。"
                                           "请告知用户：确认后才会执行；用户取消或超时未处理则不会执行。",
                            }, ensure_ascii=False)
                            record = {
                                "tool_name": payload["tool_name"],
                                "arguments": payload.get("tool_args") or {},
                                "result": pending_result[:4000],
                                "success": False,
                            }
                            pending_records.append(record)
                            yield streaming.tool_call_done(record, iteration)
                            thinking_fragments.append(
                                f"⛔ 高风险工具挂起待确认: {payload['tool_name']}"
                            )
                else:
                    # custom 事件已是 legacy 事件结构，直接转发；顺手积累 thinking
                    yield chunk
                    if chunk.get("event") == "tool_call_start":
                        thinking_fragments.append(f"🔧 执行工具: {chunk['data']['tool_name']}")
        except Exception as e:
            logger.error(f"[Graph] 图执行失败: {e}")
            graph_error = e
        finally:
            hb_stop.set()
            hb_task.cancel()
            try:
                await hb_task
            except (asyncio.CancelledError, Exception):
                pass

        # ---------- Step 5: 汇总最终回复（对齐 legacy Case B / 轮次耗尽分支） ----------
        if graph_error is not None:
            final_reply = f"抱歉，AI 引擎暂时不可用，请稍后重试。\n(错误信息: {graph_error})"
            intent_group = "unknown"
        else:
            intent_group = final_state.get("intent_group", "unknown")
            last_msgs = final_state.get("messages") or []
            last_ai = next((m for m in reversed(last_msgs) if isinstance(m, AIMessage)), None)
            final_reply = (
                last_ai.content
                if last_ai is not None and isinstance(last_ai.content, str)
                else ""
            )
            if not final_reply:
                if interrupted:
                    # 图停在确认点：给用户明确的等待确认提示（不是轮次耗尽兜底）
                    final_reply = _CONFIRM_PENDING_REPLY
                elif last_ai is not None and getattr(last_ai, "tool_calls", None):
                    # 轮次耗尽时 LLM 最后一条还在发工具调用 → legacy 的兜底文案
                    final_reply = "抱歉，我处理了很多步骤但还是没能完全回答你的问题。你能说得更具体一些吗？"
                else:
                    final_reply = "抱歉，我暂时无法回答这个问题。"
            thinking_fragments.append("⏸ 等待用户确认" if interrupted else "✅ 最终回复")

        tool_records = list(final_state.get("tool_records") or []) + pending_records
        tool_calls_record = [AgentToolCall(**r) for r in tool_records]
        model_used = final_state.get("model_used") or llm.last_model
        iteration = final_state.get("iteration", 0)
        logger.info(
            f"[Graph] 完成: iterations={iteration}, tool_calls={len(tool_records)}, "
            f"model={model_used}, intent={intent_group}"
        )

        # ---------- Step 6: 保存记忆（同 legacy） ----------
        # 同时把本轮工具调用压成 ops 摘要存入短期记忆，供下一轮注入上下文
        ops_digest = build_ops_digest(tool_records)
        await anyio.to_thread.run_sync(
            lambda: self.memory.save(
                user_message, final_reply, image_url, ops=ops_digest or None
            )
        )

        # ---------- Step 7: 持久化到 MySQL（同 legacy） ----------
        def _persist_to_mysql() -> Optional[int]:
            db = SessionLocal()
            try:
                session_title = user_message[:20] if len(user_message) >= 20 else user_message
                db_session = AgentSessionService.get_or_create_session(
                    db,
                    user=self.user,
                    workspace_id=self.workspace_id or 0,
                    session_key=resolved_session_key,
                    title=session_title,
                )
                AgentSessionService.append_message(
                    db, db_session,
                    role="user", content=user_message,
                )
                AgentSessionService.append_message(
                    db, db_session,
                    role="assistant", content=final_reply,
                    tool_calls=[tc.model_dump() for tc in tool_calls_record] if tool_calls_record else None,
                    thinking=thinking_fragments[-1] if thinking_fragments else None,
                )
                db_session.model_used = model_used
                db.commit()
                return db_session.id
            finally:
                db.close()

        try:
            _db_session_id = await anyio.to_thread.run_sync(_persist_to_mysql)
            logger.info(f"[AgentSession] 已持久化 session={_db_session_id}")
        except Exception as e:
            logger.warning(f"[AgentSession] MySQL 持久化失败（不影响主流程）: {e}")

        # ---------- Step 8: 审计日志（同 legacy） ----------
        duration_ms = int((time.time() - start_time) * 1000)
        success_count = sum(1 for tc in tool_calls_record if tc.success)
        fail_count = len(tool_calls_record) - success_count

        def _write_audit() -> None:
            db = SessionLocal()
            try:
                db.add(AgentAuditLog(
                    user_id=self.user.id,
                    workspace_id=self.workspace_id or 0,
                    session_id=resolved_session_key[:64],
                    user_message=user_message,
                    tool_calls=[tc.model_dump() for tc in tool_calls_record],
                    tool_call_count=len(tool_calls_record),
                    success_count=success_count,
                    fail_count=fail_count,
                    reply=final_reply[:2000],
                    model_used=model_used,
                    intent_group=intent_group or "unknown",
                    duration_ms=duration_ms,
                ))
                db.commit()
            finally:
                db.close()

        try:
            await anyio.to_thread.run_sync(_write_audit)
            logger.info(f"[AgentAudit] 已记录: tool_calls={len(tool_calls_record)}, duration={duration_ms}ms, intent={intent_group}")
        except Exception as e:
            logger.warning(f"[AgentAudit] 写入失败（不影响主流程）: {e}")

        # ---------- 输出：message chunks + done（格式收敛到 graph.streaming，P5） ----------
        for ev in streaming.message_chunks(final_reply):
            yield ev

        yield streaming.done(
            session_id=resolved_session_key,
            model_used=model_used,
            reply=final_reply,
            tool_calls=[tc.model_dump() for tc in tool_calls_record],
            thinking="\n".join(thinking_fragments),
        )

        # 跨会话长期记忆抽取：放在 reply 已下发之后，不增加用户感知延迟。
        # 只记录稳定事实（偏好/身份/明确要求记住的事），一次性任务与查询结果不入库。
        # 中断（等待确认）的轮次本轮没有实质结论，跳过抽取。
        if not interrupted:
            try:
                await extract_and_store(
                    self.user.id, self.workspace_id or 0, user_message, final_reply
                )
            except Exception as e:
                logger.warning(f"[LongMemory] 本轮抽取异常（忽略）: {e}")

        # P4: 未中断的轮次用完即清理 thread（中断的保留，等待 /confirm resume）
        if not interrupted:
            await _delete_thread(checkpointer, thread_id)

        # P6: 收尾 trace（含 token / 节点 / 工具耗时）
        trace.finish(
            status="interrupted" if interrupted else ("error" if graph_error else "ok"),
            intent_group=intent_group,
            iterations=iteration,
            model_used=model_used,
            reply_chars=len(final_reply),
        )

    # ============================================================
    # P4: interrupt 恢复（供 POST /agent/confirm 调用）
    # ============================================================
    async def resume_confirmation(self, approved: bool, thread_id: Optional[str] = None) -> dict:
        """从 danger 工具的 interrupt 恢复图执行。

        thread_id 必须与触发 interrupt 的那一轮一致（由 Redis 确认映射携带），
        缺省时回退到会话 key（兼容无映射场景）。

        与 legacy 的差异：工具执行由 graph 完成，但**不**在这里做记忆/MySQL 持久化，
        会话回写沿用 router 里既有的 _writeback_conversation，保持前端契约不变。

        Returns:
            {"reply", "tool_records", "interrupted", "pending_confirms", "error"}
        """
        resolved_session_key = self.session_id or f"user:{self.user.id}"
        thread_id = thread_id or resolved_session_key
        llm = ChatLLMWithFallback()
        trace = TraceRecorder(
            user_id=self.user.id,
            workspace_id=self.workspace_id,
            session_id=resolved_session_key,
            engine="langgraph",
            message="[confirm resume]",
        )
        exec_ctx = {
            "user": self.user,
            "workspace_id": self.workspace_id,
            "session_key": resolved_session_key,
            "thread_id": thread_id,
            "message": "",
            "base_system_prompt": _build_system_prompt(self.user, self.workspace_id),
            "tool_context": self.context,
            "llm": llm,
            "trace": trace,
        }
        checkpointer = await get_checkpointer()
        graph = build_graph(checkpointer=checkpointer, store=get_store())
        config = {
            "configurable": {"thread_id": thread_id, "exec_ctx": exec_ctx},
            "recursion_limit": settings.AGENT_MAX_TOOL_ITERATIONS * 8 + 10,
        }

        final_state: dict = {}
        pending: list[dict] = []
        interrupted = False
        try:
            async for mode, chunk in graph.astream(
                Command(resume={"approved": approved}),
                config=config,
                stream_mode=["values", "updates"],
            ):
                if mode == "values":
                    final_state = chunk
                elif mode == "updates":
                    raw = chunk.get("__interrupt__") if isinstance(chunk, dict) else None
                    if raw:
                        # 同一批 tool_calls 里还有下一个危险操作 → 再次挂起
                        interrupted = True
                        for item in raw:
                            payload = getattr(item, "value", item)
                            if isinstance(payload, dict):
                                pending.append(payload)
        except Exception as e:
            logger.error(f"[Graph] resume 执行失败: {e}")
            # 最常见原因是 InMemorySaver 里该 thread 已不存在（服务重启/多 worker）
            return {
                "reply": f"确认失败：会话的待确认状态已失效，请重新发起对话。({e})",
                "tool_records": [],
                "interrupted": False,
                "pending_confirms": [],
                "error": str(e),
            }

        last_msgs = final_state.get("messages") or []
        last_ai = next((m for m in reversed(last_msgs) if isinstance(m, AIMessage)), None)
        reply = (
            last_ai.content if last_ai is not None and isinstance(last_ai.content, str) else ""
        )
        if not reply:
            reply = _CONFIRM_PENDING_REPLY if interrupted else (
                "已处理确认请求。" if approved else "已取消该高风险操作，未执行任何变更。"
            )

        tool_records = final_state.get("tool_records") or []
        logger.info(
            f"[Graph] resume 完成: approved={approved}, interrupted={interrupted}, "
            f"tool_calls={len(tool_records)}"
        )
        if not interrupted:
            await _delete_thread(checkpointer, thread_id)
        trace.finish(
            status="interrupted" if interrupted else "ok",
            approved=approved,
            iterations=final_state.get("iteration", 0),
            model_used=llm.last_model,
        )
        return {
            "reply": reply,
            "tool_records": tool_records,
            "interrupted": interrupted,
            "pending_confirms": pending,
            "error": None,
        }
