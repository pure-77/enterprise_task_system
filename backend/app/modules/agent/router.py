"""Agent 模块 — API 路由端点"""
import asyncio
import uuid
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.db.redis_client import get_redis
from app.modules.agent.memory import AgentMemory
from app.modules.agent.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    PlanConfirmRequest,
)
from app.modules.agent.service import AgentService
from app.modules.agent.tool_registry import ToolRegistry
from app.modules.agent.session_service import AgentSessionService

logger = logging.getLogger("agent.router")

router = APIRouter()

# 任务计划相关常量（与 tools/task_tools.py 保持一致）
_PLAN_REDIS_PREFIX = "agent:plan:"
_PLAN_CONFIRMED_TTL = 600


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Agent 对话端点 — 自然语言操作企业办公平台

    支持：
    - 单轮/多轮对话（自动维护 Redis 记忆）
    - 多模态（图片输入，需前端传 image_url 在扩展字段里）
    - 强制重置记忆（reset_memory=true）

    请求体：
    ```json
    {
        "message": "帮我创建一个任务：写周报，明天下午6点截止",
        "workspace_id": 1,
        "session_id": "可选，不传则用 user_id",
        "reset_memory": false
    }
    ```
    """
    # session_id 生成策略：
    # - 前端传了就用（对应 MySQL session_key）
    # - 没传 → 用稳定的 workspace:user key（同一空间的对话不丢）
    # - 不再每次生成新 UUID（否则刷新/重连就"失忆"）
    workspace_id = request.workspace_id if request.workspace_id and request.workspace_id > 0 else 0
    session_id = request.session_id or f"ws-{workspace_id}-user-{current_user.id}"

    agent = AgentService(
        user=current_user,
        workspace_id=workspace_id,
        session_id=session_id,
    )

    # 重置记忆
    if request.reset_memory:
        agent.memory.clear()

    try:
        # 多模态：image_url 已在请求模型中声明
        image_url = request.image_url

        response = await agent.chat(
            user_message=request.message,
            image_url=image_url,
        )
        return response

    except Exception as e:
        logger.exception("[Agent] /chat 端点异常")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent 服务异常: {str(e)}",
        )


@router.post("/chat/stream")
async def agent_chat_stream(
    request: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Agent 对话（SSE 流式输出）

    与 /chat 完全相同的逻辑，但通过 SSE (Server-Sent Events) 格式逐字推送回复，
    实现打字机效果。内部仍先跑完所有 tool_calls（工具调用不能流式），
    然后把最终自然语言回复逐字推给前端。

    SSE 事件类型：
    - event: tool_call  → 工具执行（一次性 JSON）
    - event: message    → LLM 自然语言回复（多次逐字推送）
    - event: done       → 结束标记
    - event: error      → 错误
    """
    # 构造 AgentService（复用 /chat 逻辑）
    workspace_id = request.workspace_id if request.workspace_id and request.workspace_id > 0 else 0
    session_id = request.session_id or f"ws-{workspace_id}-user-{current_user.id}"

    agent = AgentService(
        user=current_user,
        workspace_id=workspace_id,
        session_id=session_id,
    )
    if request.reset_memory:
        agent.memory.clear()

    image_url = request.image_url

    async def sse_generator():
        # B2: 改用 chat_stream async generator，边跑边 yield SSE 事件
        # H4: 捕获 asyncio.CancelledError，正确标识客户端中断
        collected_tool_calls = []
        try:
            async for event_data in agent.chat_stream(
                user_message=request.message,
                image_url=image_url,
            ):
                ev = event_data["event"]
                data = event_data["data"]

                if ev == "tool_call_start":
                    # 新事件：工具开始执行（前端可选择处理或忽略）
                    continue  # 暂时不单独推，等 done 时聚合推 tool_call 列表
                elif ev == "tool_call_done":
                    # 收集完整 tool_call，等 done 前一次性推 event: tool_call
                    tc_dict = data["tool_call"]
                    tc_dict["meta"] = ToolRegistry.get_tool_meta(data["tool_name"])
                    collected_tool_calls.append(tc_dict)
                elif ev == "message":
                    # 逐字符自然语言回复，直接推
                    yield f"event: message\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif ev == "done":
                    # done 前先推聚合的 tool_call 列表（兼容原前端协议）
                    if collected_tool_calls:
                        yield f"event: tool_call\ndata: {json.dumps(collected_tool_calls, ensure_ascii=False)}\n\n"
                    # 推 done 事件（带完整元数据）
                    done_payload = {
                        "session_id": data.get("session_id", ""),
                        "model_used": data.get("model_used", ""),
                        "total_tool_calls": data.get("total_tool_calls", len(collected_tool_calls)),
                    }
                    yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            # H4: 客户端断开连接，agent.chat_stream() 后台可能还在跑，
            # 但 generator 被取消后结果会被丢弃。日志里正确标识这种情况不算错误。
            logger.info("[Agent] SSE 连接被客户端中断")
            raise  # 必须 re-raise CancelledError，让 ASGI server 正确清理

        except Exception as e:
            logger.exception("[Agent] /chat/stream 异常")
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.get("/tools")
async def list_agent_tools(
    current_user: User = Depends(get_current_user),
):
    """列出当前已注册的所有 Agent 工具（调试/前端展示用）"""
    return {
        "total": len(ToolRegistry.list_tools()),
        "tools": ToolRegistry.list_tools(),
        "groups": ToolRegistry.get_group_names(),
    }


@router.delete("/memory")
async def clear_agent_memory(
    workspace_id: int = None,
    session_id: str = None,
    current_user: User = Depends(get_current_user),
):
    """清空 Agent 对话记忆"""
    memory = AgentMemory(
        workspace_id=workspace_id,
        user_id=current_user.id,
        session_id=session_id,
    )
    memory.clear()
    return {"message": "记忆已清空", "key": memory.key}


# ==================== 会话持久化（MySQL）====================

@router.get("/sessions")
async def list_sessions(
    workspace_id: int = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出用户的 Agent 会话（MySQL 持久化，跨设备同步）"""
    sessions = AgentSessionService.list_sessions(db, current_user, workspace_id, limit)
    return {
        "total": len(sessions),
        "sessions": [
            {
                "id": s.id,
                "session_key": s.session_key,
                "title": s.title or "新对话",
                "workspace_id": s.workspace_id,
                "message_count": s.message_count,
                "model_used": s.model_used,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    limit: int = 200,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定会话的完整消息历史"""
    messages = AgentSessionService.get_messages(db, current_user, session_id, limit)

    def _with_meta(raw_tool_calls):
        """历史会话补 meta（icon/action/danger_level），避免前端展示时元数据缺失"""
        if not raw_tool_calls:
            return None
        try:
            tcs = json.loads(raw_tool_calls)
        except Exception:
            return None
        if not isinstance(tcs, list):
            return None
        for tc in tcs:
            if isinstance(tc, dict) and tc.get("tool_name"):
                tc.setdefault("meta", ToolRegistry.get_tool_meta(tc["tool_name"]))
        return tcs

    return {
        "total": len(messages),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "seq": m.seq,
                "image_url": m.image_url,
                "tool_calls": _with_meta(m.tool_calls),
                "thinking": m.thinking,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除会话（级联删除所有消息）"""
    ok = AgentSessionService.delete_session(db, current_user, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或无权删除")
    return {"message": "已删除"}


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_message(
    session_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除单条消息"""
    ok = AgentSessionService.delete_message(db, current_user, session_id, message_id)
    if not ok:
        raise HTTPException(status_code=404, detail="消息不存在或无权删除")
    return {"message": "已删除"}


# ==================== 任务规划（plan_tasks）确认 / 取消 ====================

def _load_pending_plan(plan_id: str, current_user: User) -> dict:
    """从 Redis 读取待确认计划并做归属/状态校验，失败抛对应 HTTPException"""
    try:
        r = get_redis()
    except Exception as e:
        logger.warning(f"[AgentPlan] Redis 不可用: {e}")
        raise HTTPException(status_code=503, detail="规划服务暂不可用（Redis 未连接），请稍后重试")

    raw = r.get(f"{_PLAN_REDIS_PREFIX}{plan_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="计划不存在或已过期（计划仅保留 30 分钟），请重新让我规划")
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="计划数据损坏，请重新让我规划")

    if plan.get("user_id") != current_user.id:
        # 不暴露他人计划是否存在
        raise HTTPException(status_code=403, detail="无权操作该计划")
    if plan.get("status") != "pending":
        status_text = {"confirmed": "该计划已确认并创建", "cancelled": "该计划已取消"}.get(
            plan.get("status"), "该计划已处理")
        raise HTTPException(status_code=409, detail=status_text)
    return plan


def _build_plan_summary(goal: str, created: list, failed: list) -> str:
    """生成确定性的确认结果摘要（不额外消耗 LLM 调用）"""
    lines = [f"✅ 已按计划「{goal}」创建 {len(created)} 个任务："]
    for i, item in enumerate(created, 1):
        lines.append(f"{i}. 「{item['title']}」(任务 #{item['task_id']})")
    if failed:
        lines.append(f"\n⚠️ {len(failed)} 个任务创建失败：")
        for item in failed:
            lines.append(f"- 「{item['title']}」：{item['error']}")
    return "\n".join(lines)


@router.post("/plans/{plan_id}/confirm")
async def confirm_plan(
    plan_id: str,
    request: PlanConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    确认任务计划 → 批量创建任务

    复用 ToolRegistry 的 create_task 执行，保证与对话中创建任务完全一致的
    权限校验、通知推送、空间动态、缓存失效等副作用；写操作不重试，杜绝重复创建。
    """
    plan = _load_pending_plan(plan_id, current_user)
    all_tasks: list = plan.get("tasks") or []

    # 勾选下标校验
    if request.task_indexes is None:
        selected = list(all_tasks)
    else:
        valid_indexes = {t.get("index") for t in all_tasks}
        bad = [i for i in request.task_indexes if i not in valid_indexes]
        if bad:
            raise HTTPException(status_code=400, detail=f"非法的任务下标: {bad}")
        selected = [t for t in all_tasks if t.get("index") in set(request.task_indexes)]
    if not selected:
        raise HTTPException(status_code=400, detail="未勾选任何任务，无需创建；可直接取消计划")

    ws = plan.get("workspace_id")
    context = {"user": current_user, "workspace_id": ws}

    # 逐个创建（写操作绝不并行/重试，避免重复任务与重复通知）
    created: list[dict] = []
    failed: list[dict] = []
    for item in selected:
        args = {
            "title": item["title"],
            "description": item.get("description"),
            "deadline": item.get("deadline"),
            "priority": item.get("priority") or "medium",
            "assignee_id": item.get("assignee_id"),
        }
        result_raw = await ToolRegistry.execute("create_task", args, context)
        try:
            result = json.loads(result_raw or "{}")
        except json.JSONDecodeError:
            result = {"success": False, "error": "创建结果解析失败"}
        if result.get("success"):
            created.append({
                "index": item.get("index"),
                "title": item["title"],
                "task_id": result.get("task_id"),
                "message": result.get("message"),
            })
        else:
            failed.append({
                "index": item.get("index"),
                "title": item["title"],
                "error": result.get("error") or "未知错误",
            })

    # 标记计划已消费（保留 10 分钟供前端展示终态），即使 Redis 更新失败也不影响创建结果
    try:
        r = get_redis()
        plan["status"] = "confirmed"
        plan["confirmed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plan["result"] = {"created_count": len(created), "failed_count": len(failed)}
        r.setex(f"{_PLAN_REDIS_PREFIX}{plan_id}", _PLAN_CONFIRMED_TTL,
                json.dumps(plan, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"[AgentPlan] 更新计划终态失败（不影响创建结果）: {e}")

    # 回写会话（MySQL 历史 + Redis 短期记忆），失败不影响主流程
    goal = plan.get("goal", "")
    user_echo = f"📋 确认执行任务计划：{goal}"
    summary = _build_plan_summary(goal, created, failed)
    ws0 = ws or 0
    session_key = request.session_id or f"ws-{ws0}-user-{current_user.id}"
    try:
        db_session = AgentSessionService.get_or_create_session(
            db, user=current_user, workspace_id=ws0,
            session_key=session_key, title=goal[:20] or "任务计划",
        )
        AgentSessionService.append_message(db, db_session, role="user", content=user_echo)
        AgentSessionService.append_message(db, db_session, role="assistant", content=summary)
        AgentMemory(ws0, current_user.id, session_key).save(user_echo, summary)
    except Exception as e:
        logger.warning(f"[AgentPlan] 会话回写失败（不影响创建结果）: {e}")

    return {
        "success": len(failed) == 0,
        "plan_id": plan_id,
        "goal": goal,
        "total": len(selected),
        "created_count": len(created),
        "failed_count": len(failed),
        "created": created,
        "failed": failed,
        "summary": summary,
    }


@router.post("/plans/{plan_id}/cancel")
async def cancel_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
):
    """取消任务计划（不会创建任何任务）"""
    plan = _load_pending_plan(plan_id, current_user)
    r = get_redis()
    plan["status"] = "cancelled"
    r.setex(f"{_PLAN_REDIS_PREFIX}{plan_id}", _PLAN_CONFIRMED_TTL,
            json.dumps(plan, ensure_ascii=False))
    return {"success": True, "plan_id": plan_id, "message": "计划已取消，未创建任何任务"}
