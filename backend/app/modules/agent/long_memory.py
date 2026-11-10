"""Agent 跨会话长期记忆（基于 LangGraph Store）

职责：
- retrieve_context：按当前用户消息语义检索相关长期记忆，注入 system prompt
- extract_and_store：每轮结束后用 LLM 抽取稳定事实（偏好/身份/明确要求记住的事）写入 Store

命名空间 ("user_memory", user_id) → 天然跨会话、跨工作空间；
存储后端见 store/mysql_store.py（MySQL 持久化，重启不丢）。
"""
import json
import logging
from datetime import datetime

from app.core.config import settings
from app.modules.agent.store import get_store

logger = logging.getLogger("agent.long_memory")

_KINDS = ("preference", "profile", "instruction", "object")
_MAX_ADD_PER_TURN = 5
_MERGE_SCORE = 0.85  # 相似度达到该阈值 → 交给 LLM 合并，而不是简单丢弃
_EXTRACT_PROMPT = """你是长期记忆管理器。根据这一轮对话，判断哪些信息值得跨会话长期记住。

只记录：
- 用户稳定的偏好/习惯（如"偏好先做重要任务"）
- 用户身份/角色/负责范围（如"负责后端开发"）
- 用户明确要求记住的内容
- 长期有效的常用对象（如"常用工作空间：研发组"）

不要记录：一次性的任务/日程/查询结果、临时状态、常识、寒暄。

如果用户明确要求忘记某事，把要删除的关键词放入 delete。

严格输出 JSON：{"add": [{"text": "...", "kind": "preference|profile|instruction|object"}], "delete": ["关键词"]}
没有则输出 {"add": [], "delete": []}。不要输出任何解释。"""


def _namespace(user_id: int) -> tuple:
    return ("user_memory", str(user_id))


def format_memory_context(items: list) -> str:
    """把检索到的记忆条目拼成可注入 system prompt 的文本"""
    lines = []
    for item in items:
        value = getattr(item, "value", None) or {}
        text = str(value.get("text") or "").strip()
        if text:
            lines.append(f"- {text}")
    if not lines:
        return ""
    return (
        "【长期记忆】以下是你在以往会话中了解到的关于当前用户的稳定信息，"
        "可作为事实依据；不要向用户复述这份记录。\n" + "\n".join(lines)
    )


async def retrieve_context(user_id: int, query: str) -> str:
    """语义检索与当前问题相关的长期记忆；失败不影响主流程"""
    if not settings.AGENT_LONG_MEMORY_ENABLED or not (query or "").strip():
        return ""
    try:
        items = await get_store().asearch(
            _namespace(user_id),
            query=query,
            limit=settings.AGENT_LONG_MEMORY_TOP_K,
        )
        return format_memory_context(items)
    except Exception as e:
        logger.warning(f"[LongMemory] 检索失败（忽略）: {e}")
        return ""


async def extract_and_store(
    user_id: int,
    workspace_id: int,
    user_message: str,
    reply: str,
) -> int:
    """从本轮对话抽取稳定事实并写入 Store，返回新增条数"""
    if not settings.AGENT_LONG_MEMORY_ENABLED:
        return 0

    payload = await _extract(user_message, reply)
    if payload is None:
        return 0

    store = get_store()
    ns = _namespace(user_id)
    added = 0
    merged = 0

    # ---- 删除 ----
    for keyword in payload.get("delete") or []:
        keyword = str(keyword).strip()
        if not keyword:
            continue
        try:
            hits = await store.asearch(ns, query=keyword, limit=5)
            for hit in hits:
                text = str((hit.value or {}).get("text") or "")
                if ((hit.score or 0) >= 0.80) or (keyword in text):
                    await store.aput(ns, hit.key, None, index=False)
        except Exception as e:
            logger.warning(f"[LongMemory] 删除记忆失败: {e}")

    # ---- 新增 / 合并 ----
    for fact in (payload.get("add") or [])[:_MAX_ADD_PER_TURN]:
        if not isinstance(fact, dict):
            continue
        text = str(fact.get("text") or "").strip()
        if not text or len(text) > 200:
            continue
        kind = fact.get("kind") if fact.get("kind") in _KINDS else "object"
        try:
            existing = await store.asearch(ns, query=text, limit=3)

            # 完全一致 → 直接跳过
            if any(
                str((hit.value or {}).get("text") or "").strip() == text
                for hit in existing
            ):
                continue

            # 语义相近 → 用 LLM 把新旧两条重写成一条更完整的表述，覆盖原条目
            best = existing[0] if existing else None
            if best and (best.score or 0) >= _MERGE_SCORE:
                old_text = str((best.value or {}).get("text") or "").strip()
                merged_text = await _merge_memory(old_text, text)
                if merged_text and merged_text != old_text:
                    old_value = dict(best.value or {})
                    old_value.update({
                        "text": merged_text,
                        "kind": old_value.get("kind") or kind,
                        "workspace_id": workspace_id or 0,
                        "source": "merged",
                        "merged_at": datetime.now().isoformat(timespec="seconds"),
                    })
                    await store.aput(ns, best.key, old_value)
                    merged += 1
                    continue
                if merged_text == old_text:
                    continue
                # 合并失败 → 退化为独立新增，避免丢失信息

            await store.aput(ns, f"m_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{added}", {
                "text": text,
                "kind": kind,
                "workspace_id": workspace_id or 0,
                "source": "auto",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            })
            added += 1
        except Exception as e:
            logger.warning(f"[LongMemory] 写入记忆失败: {e}")

    if added or merged:
        logger.info(
            f"[LongMemory] 新增 {added} 条、合并 {merged} 条长期记忆, user={user_id}"
        )
        await _enforce_limit(ns)
    return added


async def _extract(user_message: str, reply: str) -> dict | None:
    """调用 LLM 抽取记忆；任何异常返回 None"""
    try:
        from app.modules.agent.legacy.llm_provider import get_llm

        llm = get_llm(has_image=False)
        resp = await llm.chat(
            messages=[
                {"role": "system", "content": _EXTRACT_PROMPT},
                {"role": "user", "content": f"用户：{user_message[:1000]}\n助手：{reply[:1000]}"},
            ],
            temperature=0.0,
        )
        return _parse_json(resp.choices[0].message.content)
    except Exception as e:
        logger.warning(f"[LongMemory] 抽取失败（忽略）: {e}")
        return None


async def _merge_memory(old: str, new: str) -> str | None:
    """把新旧两条相似记忆合并成一条更完整的表述；失败返回 None"""
    if not old:
        return new
    try:
        from app.modules.agent.legacy.llm_provider import get_llm

        llm = get_llm(has_image=False)
        resp = await llm.chat(
            messages=[{
                "role": "user",
                "content": (
                    "合并下面两条关于同一用户的信息，输出一条更准确、更完整的中文陈述。\n"
                    "要求：保留不冲突的细节，冲突时以「新」为准；不超过 80 字；"
                    "只输出合并后的一句话，不要解释、不要加引号。\n\n"
                    f"旧：{old}\n新：{new}"
                ),
            }],
            temperature=0.0,
        )
        text = (resp.choices[0].message.content or "").strip().strip("`\"'“”")
        text = text.splitlines()[0].strip() if text else ""
        return text[:200] or None
    except Exception as e:
        logger.warning(f"[LongMemory] 合并失败（退化为新增）: {e}")
        return None


def _parse_json(content: str) -> dict | None:
    """容错解析：去掉 ```json 围栏，截取最外层 {...}"""
    if not content:
        return None
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("add"), list):
        data["add"] = []
    if not isinstance(data.get("delete"), list):
        data["delete"] = []
    return data


async def _enforce_limit(ns: tuple) -> None:
    """单用户记忆条数上限，超出删除最旧条目"""
    limit = settings.AGENT_LONG_MEMORY_MAX_ITEMS
    try:
        items = await get_store().asearch(ns, limit=limit + 50)
        for item in items[limit:]:
            await get_store().aput(ns, item.key, None, index=False)
    except Exception as e:
        logger.warning(f"[LongMemory] 清理超额记忆失败: {e}")
