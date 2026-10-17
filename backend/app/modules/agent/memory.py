"""Agent 模块 — 对话记忆管理（Redis）

设计思路：
- Redis List 存储每轮对话 [user_msg, assistant_msg, user_msg, assistant_msg, ...]
- Key: agent:memory:{workspace_id}:{user_id}  （不传 session_id 时）
      agent:memory:session:{session_id}         （传了 session_id 时）
- TTL: 24h（可配置），自动过期
- 只保留最近 N 轮（可配置），防止上下文过长
- 多模态图片只存 URL，不存 base64 原始数据
"""
import json
import logging
from typing import Optional

from app.db.redis_client import get_redis
from app.core.config import settings

logger = logging.getLogger("agent.memory")


class AgentMemory:
    """Redis 对话记忆"""

    def __init__(self, workspace_id: Optional[int] = None, user_id: int = None, session_id: Optional[str] = None):
        """
        Args:
            workspace_id: 当前 workspace ID（可选，用于拼接 key）
            user_id: 用户 ID（必填）
            session_id: 显式会话 ID（可选，优先级高于 workspace + user）
        """
        if session_id:
            self._key = f"agent:memory:session:{session_id}"
        else:
            ws = workspace_id or 0
            self._key = f"agent:memory:{ws}:{user_id}"

        self._max_rounds = settings.AGENT_MEMORY_MAX_ROUNDS
        self._ttl = settings.AGENT_MEMORY_TTL_SECONDS

    @property
    def key(self) -> str:
        return self._key

    @property
    def _summary_key(self) -> str:
        """摘要持久化 key —— 摘要必须持久化，否则下一轮 load() 拿不到，前文永久丢失"""
        return f"{self._key}:summary"

    def _load_summary(self) -> Optional[str]:
        try:
            return get_redis().get(self._summary_key)
        except Exception as e:
            logger.warning(f"[Memory] 读取摘要失败: {e}")
            return None

    def _save_summary(self, summary: str):
        try:
            get_redis().set(self._summary_key, summary, ex=self._ttl)
        except Exception as e:
            logger.warning(f"[Memory] 保存摘要失败: {e}")

    def load(self) -> list[dict]:
        """
        加载对话历史 —— 先查 Redis，空则 fallback 到 MySQL 持久化表

        这样即使 Redis 过期（24h TTL）或跨设备，Agent 也能恢复之前的对话。
        从 MySQL 拉到后自动回灌 Redis，下次直接命中缓存。

        Returns:
            OpenAI 格式的 messages 列表（不含 system prompt，由上层拼接）
        """
        # --- 1. 先查 Redis ---
        try:
            r = get_redis()
            raw_list = r.lrange(self._key, 0, -1)
            if raw_list:
                messages = []
                for raw in raw_list:
                    try:
                        msg = json.loads(raw)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
                logger.debug(f"[Memory] Redis 命中 {len(messages)} 条, key={self._key}")
                return messages
        except Exception as e:
            logger.warning(f"[Memory] Redis 查询异常，尝试 MySQL: {e}")

        # --- 2. Redis 为空 → fallback 到 MySQL ---
        return self._load_from_mysql()

    def _load_from_mysql(self) -> list[dict]:
        """从 MySQL agent_message 表按 session_key 拉取历史（OpenAI messages 格式）"""
        try:
            from app.db.session import SessionLocal
            from app.models.agent_session import AgentSession, AgentMessage

            # 从 Redis key 中解析 session_key
            # key 格式: agent:memory:session:{session_id} 或 agent:memory:{ws}:{user_id}
            session_key = None
            if self._key.startswith("agent:memory:session:"):
                session_key = self._key[len("agent:memory:session:"):]

            if not session_key:
                logger.debug(f"[Memory] 无法从 key 解析 session_key，跳过 MySQL fallback, key={self._key}")
                return []

            db = SessionLocal()
            try:
                session = db.query(AgentSession).filter(
                    AgentSession.session_key == session_key
                ).first()
                if not session:
                    logger.debug(f"[Memory] MySQL 无对应会话, session_key={session_key}")
                    return []

                db_messages = db.query(AgentMessage).filter(
                    AgentMessage.session_id == session.id
                ).order_by(AgentMessage.seq.asc()).limit(200).all()

                if not db_messages:
                    logger.debug(f"[Memory] MySQL 会话无消息, session_id={session.id}")
                    return []

                # 转为 OpenAI 格式：只保留 user/assistant 的纯 content。
                # 不能回灌带 tool_calls 的 assistant 消息（缺少配对的 tool 消息会被
                # OpenAI 以「tool_calls must be followed by tool messages」拒绝），
                # 也不能塞 image_url 作为顶层 key（非法字段）。
                messages = []
                for m in db_messages:
                    if m.role not in ("user", "assistant"):
                        continue
                    messages.append({"role": m.role, "content": m.content or ""})

                logger.info(f"[Memory] MySQL fallback 拉取 {len(messages)} 条, session_id={session.id}")

                # 回灌 Redis（warm up cache）
                self._seed_redis(messages)
                return messages

            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[Memory] MySQL fallback 失败: {e}")
            return []

    def _seed_redis(self, messages: list[dict]):
        """把 MySQL 拉到的历史回灌 Redis（只回灌 user/assistant 纯文本，跳过 tool/system）"""
        try:
            r = get_redis()
            # 过滤：只存 user 和 assistant 的纯 content（与 save() 格式一致）
            cleaned = []
            for m in messages:
                role = m.get("role", "")
                content = m.get("content", "")
                if role in ("user", "assistant") and content:
                    cleaned.append(json.dumps({"role": role, "content": content}, ensure_ascii=False))

            if cleaned:
                r.delete(self._key)
                r.rpush(self._key, *cleaned)
                r.expire(self._key, self._ttl)
                logger.info(f"[Memory] MySQL 回灌 Redis: {len(cleaned)} 条, key={self._key}")
        except Exception as e:
            logger.warning(f"[Memory] Redis 回灌失败: {e}")

    async def load_with_summary(self) -> list[dict]:
        """
        加载记忆并自动摘要压缩（长对话优化）

        当对话轮次超过 max_rounds（默认 10 轮 = 20 条）时：
        - 把最早的一半对话让 LLM 生成一段摘要
        - 返回 [SystemMessage(摘要)] + [最近 max_rounds 条完整对话]
        - 同时更新 Redis 存储（用摘要替换老对话，保留最新）

        好处：
        - 防止 Redis 存储膨胀
        - 防止 LLM 上下文超限（4k/8k window 爆掉）
        - 保留长期对话的语义连续性

        Returns:
            OpenAI 格式的 messages 列表
        """
        existing_summary = self._load_summary()
        history = self.load()
        total_messages = len(history)

        # 不到两倍 max_rounds，不需要压缩
        if total_messages <= self._max_rounds * 2:
            if existing_summary:
                return [{
                    "role": "system",
                    "content": f"【对话上下文摘要】之前的对话要点：{existing_summary}",
                }] + history
            return history

        split_point = (total_messages // 2)  # 前半 vs 后半
        old_msgs = history[:split_point]
        recent_msgs = history[split_point:]

        logger.info(f"[Memory] 长对话触发压缩: total={total_messages}, 摘要前 {split_point} 条, 保留最近 {len(recent_msgs)} 条")

        # 尝试让 LLM 生成摘要
        summary = None
        try:
            from app.modules.agent.llm_provider import get_llm
            llm = get_llm(has_image=False)

            # 构造纯文本对话用于摘要
            dialog_text = "\n".join(
                f"[{m['role']}]: {m.get('content', '')[:200]}" for m in old_msgs
            )
            summary_resp = await llm.chat(
                messages=[{
                    "role": "user",
                    "content": f"请用 2-3 句话概括以下对话的要点（保留关键信息：做了什么任务、调了哪些工具、结论是什么）：\n{dialog_text}",
                }],
                temperature=0.1,
            )
            summary = summary_resp.choices[0].message.content
        except Exception as e:
            logger.warning(f"[Memory] LLM 摘要失败: {e}，降级为简单截断")

        # 不管摘要是否成功，都用最近 max_rounds*2 条替代
        # 先清空旧的，再推新的
        try:
            r = get_redis()
            r.delete(self._key)
            r.rpush(self._key, *[json.dumps(m, ensure_ascii=False) for m in recent_msgs])
            r.expire(self._key, self._ttl)
        except Exception as e:
            logger.warning(f"[Memory] 摘要后重置 Redis 失败: {e}")

        # 合并旧摘要 + 新摘要并持久化，避免每轮压缩都丢弃前文语义
        merged_summary = existing_summary
        if summary:
            merged_summary = f"{existing_summary} {summary}".strip() if existing_summary else summary
        if merged_summary:
            self._save_summary(merged_summary)
            return [{
                "role": "system",
                "content": f"【对话上下文摘要】之前的对话要点：{merged_summary}",
            }] + recent_msgs
        return recent_msgs

    def save(self, user_message: str, assistant_reply: str, image_url: Optional[str] = None):
        """
        保存一轮对话（user + assistant）

        Args:
            user_message: 用户消息文本
            assistant_reply: Agent 回复文本
            image_url: 用户输入中的图片 URL（可选）
        """
        try:
            r = get_redis()

            # 构造 user message
            user_msg = {"role": "user", "content": user_message}
            if image_url:
                user_msg["image_url"] = image_url

            assistant_msg = {"role": "assistant", "content": assistant_reply}

            # 右推入队
            r.rpush(self._key, json.dumps(user_msg, ensure_ascii=False))
            r.rpush(self._key, json.dumps(assistant_msg, ensure_ascii=False))

            # 超出最大轮次时截断（每轮 = user + assistant = 2 条）
            max_items = self._max_rounds * 2
            current_len = r.llen(self._key)
            if current_len > max_items:
                # 左边弹出多余的
                remove_count = current_len - max_items
                for _ in range(remove_count):
                    r.lpop(self._key)

            # 刷新 TTL
            r.expire(self._key, self._ttl)

            logger.debug(f"[Memory] 已保存, 当前 {min(current_len, max_items)} 条, key={self._key}")
        except Exception as e:
            logger.warning(f"[Memory] 保存失败: {e}")

    def clear(self):
        """清空当前会话记忆"""
        try:
            r = get_redis()
            r.delete(self._key)
            logger.info(f"[Memory] 已清空, key={self._key}")
        except Exception as e:
            logger.warning(f"[Memory] 清空失败: {e}")

    def count(self) -> int:
        """当前会话的消息条数"""
        try:
            r = get_redis()
            return r.llen(self._key)
        except Exception:
            return 0
