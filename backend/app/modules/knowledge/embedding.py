"""知识库 — 千问 DashScope Embedding 封装

自定义 Chroma EmbeddingFunction：避免 Chroma 默认使用 ONNX MiniLM（首次调用会偷跑下载模型）。
全程走 compatible-mode /embeddings，与 Agent 对话共用 QWEN_API_KEY。
"""
import logging
import time

from app.core.config import settings

logger = logging.getLogger("knowledge.embedding")

# chromadb 可选：未安装时不影响其余模块导入（vector_store 使用时会给出明确错误）
try:
    from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
except ImportError:  # pragma: no cover
    EmbeddingFunction = object
    Documents = list
    Embeddings = list


def embed_texts(texts: list) -> list:
    """批量向量化：DashScope compatible-mode /embeddings，429/5xx 指数退避重试 3 次

    Returns:
        与输入等长的向量列表（list[list[float]]）
    """
    if not texts:
        return []

    from openai import OpenAI
    cli = OpenAI(api_key=settings.QWEN_API_KEY, base_url=settings.QWEN_BASE_URL)

    out: list = []
    batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)
    for i in range(0, len(texts), batch_size):
        batch = [str(t) for t in texts[i:i + batch_size]]
        for attempt in range(3):
            try:
                resp = cli.embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
                # 按 index 还原顺序（服务端可能乱序返回）
                batch_out = sorted(resp.data, key=lambda d: d.index)
                out.extend([d.embedding for d in batch_out])
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"[KB] embedding 失败（batch {i}，{len(batch)} 条）: {e}")
                    raise
                time.sleep(2 ** attempt)
    return out


class DashScopeEmbeddingFunction(EmbeddingFunction):
    """Chroma 自定义 embedding function — 全程使用千问云端向量"""

    def __init__(self):
        super().__init__()

    def __call__(self, input: Documents) -> Embeddings:
        return embed_texts(list(input))

    def name(self) -> str:
        return "dashscope"
