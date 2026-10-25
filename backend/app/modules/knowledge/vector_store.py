"""知识库 — Chroma 向量库封装（嵌入式 PersistentClient）

关键设计：
1. 距离度量必须显式 cosine（默认 L2 会导致相似度排序错误）
2. 嵌入式 Chroma 底层是 SQLite 单进程写；Gunicorn 多 worker / 并发 BackgroundTasks
   下必须用 Redis 分布式锁把写操作串行化（kb:lock:write）
3. 数据目录 backend/data/chroma（.gitignore 排除；docker-compose 挂载 ./backend/data:/app/data 持久化）
4. chromadb 未安装时本模块可正常导入，实际使用时抛出明确错误（不影响后端其余功能启动）
"""
import logging
import uuid
import time
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("knowledge.vector_store")

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:  # pragma: no cover
    chromadb = None
    ChromaSettings = None

_client = None
_collection = None

# backend/ 目录绝对路径（本文件位于 backend/app/modules/knowledge/）
BACKEND_DIR = Path(__file__).resolve().parents[3]

_WRITE_LOCK_KEY = "kb:lock:write"
_WRITE_LOCK_WAIT_SECONDS = 10  # 拿不到锁时的最长等待


def get_chroma():
    """单例 PersistentClient（chromadb 未安装时抛出明确错误）"""
    global _client
    if chromadb is None:
        raise RuntimeError("chromadb 未安装，知识库功能不可用（pip install chromadb）")
    if _client is None:
        path = BACKEND_DIR / settings.CHROMA_DIR
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"[KB] Chroma PersistentClient 就绪: {path}")
    return _client


def get_collection():
    """获取/创建集合 — 必须显式指定 cosine，否则默认 L2 会让相似度排序出错"""
    global _collection
    if _collection is None:
        from app.modules.knowledge.embedding import DashScopeEmbeddingFunction
        _collection = get_chroma().get_or_create_collection(
            name=settings.KB_COLLECTION,
            embedding_function=DashScopeEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


@contextmanager
def chroma_write_lock(ttl: int = None):
    """Chroma 写操作跨进程互斥锁（Redis SET NX EX）

    - 拿到锁 → 执行写操作 → finally 释放（token 校验防误删他人锁）
    - 未拿到锁 → 轮询等待最多 10s → 仍失败抛 TimeoutError，由调用方标记
      status='pending' 留待 /knowledge/rebuild 补偿
    - Redis 不可用时异常直接向上抛（严格模式：宁可索引挂起也不冒并发写坏库的风险）
    """
    from app.db.redis_client import get_redis

    ttl = ttl or settings.KB_WRITE_LOCK_TTL
    token = uuid.uuid4().hex
    r = get_redis()

    deadline = time.time() + _WRITE_LOCK_WAIT_SECONDS
    acquired = False
    while time.time() < deadline:
        if r.set(_WRITE_LOCK_KEY, token, nx=True, ex=ttl):
            acquired = True
            break
        time.sleep(0.2)
    if not acquired:
        raise TimeoutError("获取知识库写锁超时（其它进程正在写入 Chroma）")
    try:
        yield
    finally:
        try:
            if r.get(_WRITE_LOCK_KEY) == token:
                r.delete(_WRITE_LOCK_KEY)
        except Exception:
            pass
