"""SSE 事件适配（P5）

把 LangGraph 内部流转（custom stream writer / 最终态）统一映射为
对前端不变的 5 类 SSE 事件，格式与 legacy 完全一致：

1. tool_call_start  —— 工具开始执行
2. tool_call_done   —— 工具执行完成（含结果与 success 标记）
3. confirm_request  —— 危险操作挂起，等待用户确认（P4 迁移到 interrupt 后仍复用本格式）
4. message          —— 回复文本分片（打字机效果）
5. done             —— 结束，data._full 携带完整结果（reply/tool_calls/thinking/session_id/model_used）
6. heartbeat        —— graph 执行期间每 400ms 一条，防止前端只看到"正在思考..."

前端 SSE 消费方无需感知底层是 legacy 主循环还是 LangGraph。
"""
import time

from fastapi.sse import ServerSentEvent

CHUNK_SIZE = 2  # 与 legacy 一致的文本分片大小


def tool_call_start(tool_name: str, iteration: int, tool_args: dict) -> dict:
    return {"event": "tool_call_start", "data": {
        "tool_name": tool_name,
        "iteration": iteration,
        "tool_args": tool_args,
    }}


def tool_call_done(record: dict, iteration: int) -> dict:
    return {"event": "tool_call_done", "data": {
        "tool_name": record["tool_name"],
        "iteration": iteration,
        "success": record.get("success", False),
        "tool_call": record,
    }}


def confirm_request(confirm_id: str, tool_name: str, tool_args: dict, meta: dict, ttl: int) -> dict:
    return {"event": "confirm_request", "data": {
        "confirm_id": confirm_id,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "meta": meta,
        "expires_in_seconds": ttl,
    }}


def message(text: str) -> dict:
    """LangGraph nodes 内部直接发单条 message 事件（router 侧已处理分片）"""
    return {"event": "message", "data": text}


def message_chunks(text: str):
    """legacy 路径兼容：按 CHUNK_SIZE 分片逐段 yield"""
    for i in range(0, len(text), CHUNK_SIZE):
        yield {"event": "message", "data": text[i:i + CHUNK_SIZE]}


def heartbeat() -> dict:
    """心跳事件：graph 执行期间（route_intent / LLM 调用 / 工具执行）每 400ms 推一条，
    避免 SSE 连接静默期间前端只看到"正在思考..."。"""
    return {"event": "heartbeat", "data": {"ts": int(time.time())}}


def done(session_id: str, model_used: str, reply: str, tool_calls: list[dict], thinking: str) -> dict:
    return {"event": "done", "data": {
        "session_id": session_id,
        "model_used": model_used,
        "total_tool_calls": len(tool_calls),
        "_full": {
            "reply": reply,
            "tool_calls": tool_calls,
            "thinking": thinking,
            "session_id": session_id,
            "model_used": model_used,
        },
    }}
