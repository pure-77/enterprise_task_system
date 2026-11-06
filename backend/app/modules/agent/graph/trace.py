"""P6 可观测性 — 轻量全链路 trace（零外部依赖）

设计取舍：
- Langfuse / LangSmith 都需要外网或自建服务；本机环境（内网 + 无 Docker）不可靠，
  因此用「结构化 JSONL」实现等价的链路可观测能力，后续可平滑替换为 Langfuse。
- 每次 Agent 执行落一条记录，记录内按发生顺序排列 span：

    kind=node —— 图节点（route_intent / agent / tools）
    kind=llm  —— 模型调用（模型名、耗时、prompt/completion/total tokens）
    kind=tool —— 工具执行（工具名、参数键、danger_level、success）
    kind=mcp  —— MCP 端点请求（方法、路径、状态码、耗时）

- 落盘：settings.AGENT_TRACE_DIR（默认 backend/logs/agent_trace），按天分文件
  trace-YYYY-MM-DD.jsonl。trace 写入失败绝不影响主流程。
- 聚合：aggregate_trace() 供 GET /api/v1/agent/trace/stats 按用户/空间统计 token 与耗时。
"""
import json
import logging
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("agent.trace")


def _trace_dir() -> Path:
    p = Path(settings.AGENT_TRACE_DIR)
    if not p.is_absolute():
        # 约定：相对路径基于 backend/（进程 cwd）
        p = Path.cwd() / p
    return p


def _today_file() -> Path:
    d = _trace_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"trace-{time.strftime('%Y-%m-%d')}.jsonl"


def _append(record: dict) -> None:
    """追加一行 JSON。任何异常都吞掉，trace 不能影响业务。"""
    try:
        with _today_file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        logger.debug(f"[Trace] 写入失败（忽略）: {e}")


class TraceRecorder:
    """单次 Agent 执行的 span 采集器"""

    def __init__(
        self,
        user_id: int,
        workspace_id: int | None,
        session_id: str,
        engine: str,
        message: str = "",
    ):
        self.run_id = uuid.uuid4().hex
        self.user_id = user_id
        self.workspace_id = workspace_id or 0
        self.session_id = session_id
        self.engine = engine
        self.message = message[:200]
        self.started_at = time.time()
        self.spans: list[dict] = []

    @contextmanager
    def span(self, name: str, kind: str, **attrs):
        """采集一段耗时。用法：
            with trace.span("llm.call", "llm", iteration=3) as sp:
                resp = await ...
                sp["attrs"].update({"total_tokens": ...})
        """
        start = time.time()
        span = {
            "name": name,
            "kind": kind,
            "offset_ms": int((start - self.started_at) * 1000),
            "duration_ms": 0,
            "attrs": dict(attrs),
        }
        try:
            yield span
        except Exception as e:
            span["error"] = f"{type(e).__name__}: {e}"
            raise
        finally:
            span["duration_ms"] = int((time.time() - start) * 1000)
            self.spans.append(span)

    def add_span(self, name: str, kind: str, duration_ms: int, offset_ms: int = 0,
                 attrs: dict | None = None, error: str | None = None) -> None:
        """手工补一条 span（用于不方便包上下文管理器的场景）"""
        span = {
            "name": name,
            "kind": kind,
            "offset_ms": offset_ms,
            "duration_ms": duration_ms,
            "attrs": attrs or {},
        }
        if error:
            span["error"] = error
        self.spans.append(span)

    # ---- 便捷方法（避免调用方各写一套计算） ----
    def record_llm_usage(self, span: dict, usage: dict | None, model: str, extra: dict | None = None):
        usage = usage or {}
        span["attrs"].update({
            "model": model,
            "prompt_tokens": int(usage.get("input_tokens") or 0),
            "completion_tokens": int(usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        })
        if extra:
            span["attrs"].update(extra)

    def tokens(self) -> dict:
        prompt = completion = total = 0
        llm_calls = 0
        for s in self.spans:
            if s["kind"] != "llm":
                continue
            a = s.get("attrs") or {}
            llm_calls += 1
            prompt += int(a.get("prompt_tokens") or 0)
            completion += int(a.get("completion_tokens") or 0)
            total += int(a.get("total_tokens") or 0)
        return {
            "llm_calls": llm_calls,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    def finish(self, status: str = "ok", **extra) -> dict:
        """收尾并落盘，返回本次记录（便于测试断言）"""
        tok = self.tokens()
        record = {
            "kind": "run",
            "run_id": self.run_id,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engine": self.engine,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "message": self.message,
            "status": status,
            "duration_ms": int((time.time() - self.started_at) * 1000),
            "tokens": tok,
            "tool_calls": sum(1 for s in self.spans if s["kind"] == "tool"),
            "spans": self.spans,
        }
        record.update(extra)
        if settings.AGENT_TRACE_ENABLED:
            _append(record)
        return record


def record_mcp_request(method: str, path: str, status_code: int, duration_ms: int, user_id: int | None = None):
    """MCP 端点请求的独立 trace 记录（无 run 上下文，便于排查 MCP 侧调用）"""
    if not settings.AGENT_TRACE_ENABLED:
        return
    _append({
        "kind": "mcp",
        "run_id": uuid.uuid4().hex,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": method,
        "path": path,
        "status": status_code,
        "duration_ms": duration_ms,
        "user_id": user_id,
    })


# ==================== 聚合（token 成本按用户/空间统计） ====================
def _iter_runs(days: int):
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    d = _trace_dir()
    if not d.exists():
        return
    for f in sorted(d.glob("trace-*.jsonl")):
        # 文件名形如 trace-2026-11-05.jsonl，直接按字符串比较日期
        date_part = f.stem.replace("trace-", "")
        if date_part < cutoff:
            continue
        try:
            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("kind") == "run":
                        yield rec
        except Exception as e:
            logger.debug(f"[Trace] 读取 {f.name} 失败（忽略）: {e}")


def _empty_bucket() -> dict:
    return {
        "runs": 0,
        "errors": 0,
        "tool_calls": 0,
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "duration_ms": 0,
        "_durations": [],
    }


def _accumulate(bucket: dict, rec: dict) -> None:
    tok = rec.get("tokens") or {}
    bucket["runs"] += 1
    if rec.get("status") == "error":
        bucket["errors"] += 1
    bucket["tool_calls"] += int(rec.get("tool_calls") or 0)
    bucket["total_tokens"] += int(tok.get("total_tokens") or 0)
    bucket["prompt_tokens"] += int(tok.get("prompt_tokens") or 0)
    bucket["completion_tokens"] += int(tok.get("completion_tokens") or 0)
    bucket["duration_ms"] += int(rec.get("duration_ms") or 0)
    bucket["_durations"].append(int(rec.get("duration_ms") or 0))


def _finalize(bucket: dict) -> dict:
    durations = sorted(bucket.pop("_durations"))
    runs = bucket["runs"]
    bucket["avg_duration_ms"] = int(bucket["duration_ms"] / runs) if runs else 0
    bucket["p95_duration_ms"] = (
        durations[min(len(durations) - 1, int(len(durations) * 0.95))] if durations else 0
    )
    return bucket


def aggregate_trace(days: int = 7, user_id: int | None = None) -> dict:
    """按 user / workspace 聚合 trace（days 为回溯天数）"""
    total = _empty_bucket()
    by_user: dict[int, dict] = {}
    by_workspace: dict[int, dict] = {}
    by_session: dict[str, dict] = {}

    for rec in _iter_runs(days):
        if user_id is not None and rec.get("user_id") != user_id:
            continue
        _accumulate(total, rec)

        uid = int(rec.get("user_id") or 0)
        wid = int(rec.get("workspace_id") or 0)
        sid = rec.get("session_id") or ""

        for buckets, key in ((by_user, uid), (by_workspace, wid), (by_session, sid)):
            b = buckets.setdefault(key, _empty_bucket())
            _accumulate(b, rec)

    top_sessions = sorted(
        by_session.items(), key=lambda kv: kv[1]["duration_ms"], reverse=True
    )[:10]

    return {
        "days": days,
        "total": _finalize(total),
        "by_user": [{"user_id": k, **_finalize(v)} for k, v in sorted(by_user.items())],
        "by_workspace": [{"workspace_id": k, **_finalize(v)} for k, v in sorted(by_workspace.items())],
        "by_session": [{"session_id": k, **_finalize(v)} for k, v in top_sessions],
    }
