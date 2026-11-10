"""LangGraph Store 的 MySQL 持久化实现

为什么不用 InMemoryStore：它只活在进程内，重启即丢，达不到「跨会话长期记忆」。
本实现继承 langgraph.store.base.BaseStore，落到 MySQL agent_memory_item 表，
并提供带向量的语义检索（向量复用知识库的 DashScope embedding；失败时降级为关键词匹配）。
"""
import json
import logging
import math
from datetime import datetime
from typing import Any, Iterable, Optional

import anyio
from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    PutOp,
    SearchItem,
    SearchOp,
)

from app.db.session import SessionLocal
from app.models.agent_memory import AgentMemoryItem

logger = logging.getLogger("agent.store.mysql")

_MAX_CANDIDATES = 500  # 单次语义检索参与打分的最大候选条数


def _ns_to_str(namespace: tuple) -> str:
    return "/".join(str(p) for p in namespace)


def _str_to_ns(ns: str) -> tuple:
    return tuple(ns.split("/")) if ns else ()


def _value_text(value: dict) -> str:
    """用于向量化 / 关键词匹配的扁平文本"""
    text = value.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _embed(text: str) -> Optional[list]:
    """向量化；不可用时返回 None（检索自动降级为关键词）"""
    try:
        from app.modules.knowledge.embedding import embed_texts
        vecs = embed_texts([text])
        return vecs[0] if vecs else None
    except Exception as e:
        logger.warning(f"[Store] embedding 失败，降级关键词检索: {e}")
        return None


def _cosine(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _match_filter(value: dict, flt: Optional[dict]) -> bool:
    if not flt:
        return True
    for k, expected in flt.items():
        actual = value.get(k)
        if isinstance(expected, dict):
            # 支持 $eq / $in 这类简单算子
            for op, v in expected.items():
                if op == "$eq" and actual != v:
                    return False
                if op == "$in" and actual not in v:
                    return False
        elif actual != expected:
            return False
    return True


class MySQLStore(BaseStore):
    """LangGraph Store 的 MySQL 实现（namespace + key → JSON value）"""

    # ---------- BaseStore 抽象接口 ----------

    def batch(self, ops: Iterable[Any]) -> list:
        results = []
        db = SessionLocal()
        try:
            for op in ops:
                if isinstance(op, GetOp):
                    results.append(self._get(db, op))
                elif isinstance(op, PutOp):
                    results.append(self._put(db, op))
                elif isinstance(op, SearchOp):
                    results.append(self._search(db, op))
                elif isinstance(op, ListNamespacesOp):
                    results.append(self._list_namespaces(db, op))
                else:
                    results.append(None)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return results

    async def abatch(self, ops: Iterable[Any]) -> list:
        return await anyio.to_thread.run_sync(lambda: self.batch(ops))

    # ---------- 具体操作 ----------

    def _get(self, db, op: GetOp) -> Optional[Item]:
        ns = _ns_to_str(op.namespace)
        row = db.query(AgentMemoryItem).filter(
            AgentMemoryItem.namespace == ns,
            AgentMemoryItem.key == op.key,
        ).first()
        return self._to_item(row) if row else None

    def _put(self, db, op: PutOp) -> None:
        ns = _ns_to_str(op.namespace)
        row = db.query(AgentMemoryItem).filter(
            AgentMemoryItem.namespace == ns,
            AgentMemoryItem.key == op.key,
        ).first()

        # value=None 表示删除
        if op.value is None:
            if row:
                db.delete(row)
            return

        text = _value_text(op.value)
        # index=False 表示不建向量；否则尝试向量化（失败不影响写入，检索会降级）
        embedding = None
        if op.index is not False:
            embedding = _embed(text)
        embedding_json = json.dumps(embedding) if embedding else None

        payload = json.dumps(op.value, ensure_ascii=False)
        if row:
            row.value = payload
            row.text = text
            row.embedding = embedding_json or row.embedding
            row.workspace_id = op.value.get("workspace_id")
            row.is_active = True
        else:
            db.add(AgentMemoryItem(
                namespace=ns,
                key=op.key,
                value=payload,
                text=text,
                embedding=embedding_json,
                workspace_id=op.value.get("workspace_id"),
            ))
        db.flush()

    def _search(self, db, op: SearchOp) -> list:
        prefix = _ns_to_str(op.namespace_prefix)
        rows = db.query(AgentMemoryItem).filter(
            AgentMemoryItem.is_active == True,  # noqa: E712
            (AgentMemoryItem.namespace == prefix)
            | (AgentMemoryItem.namespace.like(f"{prefix}/%")),
        ).order_by(AgentMemoryItem.updated_at.desc()).limit(_MAX_CANDIDATES).all()

        candidates = []
        for row in rows:
            try:
                value = json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                continue
            if _match_filter(value, op.filter):
                candidates.append((row, value))

        if op.query:
            scored = self._semantic_scores(op.query, candidates)
            scored.sort(key=lambda x: x[0], reverse=True)
            items = [
                self._to_search_item(row, value, score)
                for score, row, value in scored
                if score > 0
            ]
        else:
            items = [self._to_search_item(row, value, None) for row, value in candidates]

        return items[op.offset: op.offset + op.limit]

    def _semantic_scores(self, query: str, candidates: list) -> list:
        """返回 [(score, row, value)]；无向量时降级为关键词重合度"""
        qvec = _embed(query)
        if qvec:
            out = []
            for row, value in candidates:
                if not row.embedding:
                    continue
                try:
                    vec = json.loads(row.embedding)
                except (json.JSONDecodeError, TypeError):
                    continue
                out.append((_cosine(qvec, vec), row, value))
            if out:
                return out
            # 有向量但候选全为空 → 继续走关键词兜底

        q_tokens = {t for t in query.lower().replace("，", " ").replace("。", " ").split() if t}
        out = []
        for row, value in candidates:
            text = (row.text or "").lower()
            if not q_tokens:
                out.append((0.0, row, value))
                continue
            hit = sum(1 for t in q_tokens if t in text)
            if hit:
                out.append((hit / len(q_tokens), row, value))
        return out

    def _list_namespaces(self, db, op: ListNamespacesOp) -> list:
        rows = db.query(AgentMemoryItem.namespace).distinct().all()
        namespaces = [_str_to_ns(r[0]) for r in rows]

        if op.match_conditions:
            filtered = []
            for ns in namespaces:
                ok = True
                for cond in op.match_conditions:
                    path = tuple(cond.path)
                    if getattr(cond, "match_type", "prefix") == "prefix":
                        ok = ok and ns[:len(path)] == path
                    else:  # suffix
                        ok = ok and ns[-len(path):] == path
                if ok:
                    filtered.append(ns)
            namespaces = filtered

        if op.max_depth:
            namespaces = [ns[:op.max_depth] for ns in namespaces]
        namespaces = sorted(set(namespaces))
        return namespaces[op.offset: op.offset + op.limit]

    # ---------- 行 → LangGraph 对象 ----------

    @staticmethod
    def _to_item(row: AgentMemoryItem) -> Optional[Item]:
        try:
            value = json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            return None
        return Item(
            namespace=_str_to_ns(row.namespace),
            key=row.key,
            value=value,
            created_at=row.created_at or datetime.now(),
            updated_at=row.updated_at or datetime.now(),
        )

    @staticmethod
    def _to_search_item(row: AgentMemoryItem, value: dict, score: Optional[float]) -> SearchItem:
        return SearchItem(
            _str_to_ns(row.namespace),
            row.key,
            value,
            row.created_at or datetime.now(),
            row.updated_at or datetime.now(),
            score,
        )
