"""知识库 — 索引流水线（抽取 → 切片 → 向量化 → 写入 Chroma）

触发点（均为 BackgroundTasks，接口响应后本进程异步执行，不阻塞请求）：
- file/router.py        POST /upload      → index_source("file", f.id)
- file/router.py        DELETE /{id}      → delete_source_index("file", file_id)
- announcement/router   POST ""           → index_source("announcement", a.id)
- announcement/router   DELETE /{id}      → delete_source_index("announcement", ann_id)
- im/router.py          发送文本消息        → index_source("im", msg.id)
- im/router.py          撤回消息           → delete_source_index("im", msg_id)

幂等性：
- 向量 id = f"{source_type}:{source_id}:{chunk_index}"（确定性，重写前先删旧分片）
- content_hash 未变且 status == 'indexed' 时跳过重复 embedding
"""
import hashlib
import logging
import os
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.modules.knowledge.models import KnowledgeDocument, KnowledgeChunk

logger = logging.getLogger("knowledge.indexer")

# 单篇源文本长度上限（防止病态大文件把 embedding 费用撑爆）
_MAX_SOURCE_CHARS = 200_000

# 纯文本类扩展名（utf-8 + errors=ignore 直接读）
_TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".html",
              ".css", ".js", ".ts", ".py", ".java", ".cpp", ".c", ".go", ".rs", ".sql", ".log"}


# ============================================================
# 文本抽取辅助
# ============================================================

class _TagStripper(HTMLParser):
    """公告富文本去标签（标准库实现，不引 bs4）"""

    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def strip_html(html: str) -> str:
    try:
        s = _TagStripper()
        s.feed(html or "")
        return unescape(s.text())
    except Exception:
        return re.sub(r"<[^>]+>", " ", html or "")


def chunk_text(text: str, size: int = None, overlap: int = None) -> list:
    """中文优先切片：段落优先合并，超长段落按句末标点滑窗"""
    size = size or settings.KB_CHUNK_SIZE
    overlap = overlap or settings.KB_CHUNK_OVERLAP
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list = []
    buf = ""

    def _flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for p in paragraphs:
        if len(p) > size:
            _flush()
            start, n = 0, len(p)
            while start < n:
                end = min(start + size, n)
                if end < n:
                    # 尽量落在句末标点处断开
                    window = p[start:end]
                    cut = max(window.rfind(c) for c in "。！？；\n")
                    if cut > size // 2:
                        end = start + cut + 1
                piece = p[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end >= n:
                    break
                start = max(end - overlap, start + 1)
        else:
            if buf and len(buf) + len(p) + 1 > size:
                _flush()
            buf = f"{buf}\n{p}" if buf else p
    _flush()
    return [c for c in chunks if c]


def extract_file_text(f) -> tuple:
    """按扩展名抽取文件文本。返回 (正文, 状态)：indexed / failed / unsupported"""
    from app.modules.file.storage import storage

    ext = os.path.splitext(f.name or "")[1].lower()
    try:
        real_path = storage._get_path(f.workspace_id, f.path)
    except Exception as e:
        logger.warning(f"[KB] 文件路径非法 {f.workspace_id}/{f.path}: {e}")
        return "", "failed"
    if not os.path.exists(real_path):
        return "", "failed"

    if ext in _TEXT_EXTS:
        try:
            with open(real_path, "r", encoding="utf-8", errors="ignore") as fp:
                return fp.read(), "indexed"
        except Exception as e:
            logger.warning(f"[KB] 文本文件读取失败 {f.name}: {e}")
            return "", "failed"

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(real_path)
            pages = []
            for pg in reader.pages:
                try:
                    pages.append(pg.extract_text() or "")
                except Exception:
                    continue  # 个别页解析失败不中断
            return "\n".join(pages), "indexed"
        except Exception as e:
            logger.warning(f"[KB] PDF 解析失败 {f.name}: {e}")
            return "", "failed"

    if ext == ".docx":
        try:
            import docx
            d = docx.Document(real_path)
            parts = [p.text for p in d.paragraphs]
            for table in d.tables:
                for row in table.rows:
                    parts.append("\t".join(c.text for c in row.cells))
            return "\n".join(parts), "indexed"
        except Exception as e:
            logger.warning(f"[KB] DOCX 解析失败 {f.name}: {e}")
            return "", "failed"

    if ext == ".xlsx":
        try:
            from openpyxl import load_workbook
            wb = load_workbook(real_path, read_only=True, data_only=True)
            lines = []
            for ws_ in wb.worksheets:
                for row in ws_.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None and str(c).strip()]
                    if cells:
                        lines.append(" | ".join(cells))
            return "\n".join(lines), "indexed"
        except Exception as e:
            logger.warning(f"[KB] XLSX 解析失败 {f.name}: {e}")
            return "", "failed"

    return "", "unsupported"  # .doc/.xls/图片/音视频/压缩包等


# ============================================================
# 来源加载
# ============================================================

def _load_source(db, source_type: str, source_id: int):
    """读取来源并抽取文本。

    Returns:
        payload dict：{text, title, workspace_id, created_by, status[, conversation_id]}
        None：来源不存在 / 已停用 / 不值得索引（如过短聊天）
    """
    if source_type == "file":
        from app.modules.file.models import File
        f = db.query(File).filter(File.id == source_id, File.is_active == True).first()
        if f is None:
            return None
        text, status = extract_file_text(f)
        text = (text or "")[:_MAX_SOURCE_CHARS]
        return {"text": text, "title": f.name, "workspace_id": f.workspace_id,
                "created_by": f.uploader_id, "status": status}

    if source_type == "announcement":
        from app.modules.announcement.models import Announcement
        a = db.query(Announcement).filter(
            Announcement.id == source_id, Announcement.is_active == True).first()
        if a is None:
            return None
        text = f"{a.title}\n{strip_html(a.content)}".strip()[:_MAX_SOURCE_CHARS]
        return {"text": text, "title": a.title, "workspace_id": a.workspace_id,
                "created_by": a.created_by, "status": "ok" if text else "unsupported"}

    if source_type == "im":
        from app.modules.im.models import Message, Conversation, MessageType
        m = db.query(Message).filter(
            Message.id == source_id, Message.is_recalled == False).first()
        if m is None or m.msg_type != MessageType.TEXT:
            return None
        content = (m.content or "").strip()
        if len(content) < 10:
            return None  # 过短的闲聊不值得索引
        conv = db.query(Conversation).filter(Conversation.id == m.conversation_id).first()
        if conv is None:
            return None
        sender = db.query(User).filter(User.id == m.sender_id).first()
        sender_name = (sender.nickname if sender and sender.nickname
                       else sender.real_name if sender and sender.real_name
                       else f"用户{m.sender_id}")
        ts = m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
        text = f"[{ts}] {sender_name}: {content}"[:_MAX_SOURCE_CHARS]
        title = conv.name if conv.name else f"会话#{conv.id}"
        return {"text": text, "title": title, "workspace_id": conv.workspace_id,
                "created_by": m.sender_id, "status": "ok",
                "conversation_id": m.conversation_id}

    return None


# ============================================================
# 索引 / 删除
# ============================================================

def index_source(source_type: str, source_id: int) -> None:
    """幂等索引入口（后台线程运行，自建 DB 会话；任何失败都不向上抛）"""
    db = SessionLocal()
    try:
        payload = _load_source(db, source_type, source_id)
        if payload is None:
            logger.info(f"[KB] 跳过索引（来源不存在/已停用/不值得索引）: {source_type}/{source_id}")
            return

        ws_id = payload["workspace_id"]
        title = payload.get("title") or ""

        # ---- 文档行（幂等 upsert）----
        doc = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_type == source_type,
            KnowledgeDocument.source_id == source_id,
        ).first()
        if doc is None:
            doc = KnowledgeDocument(
                workspace_id=ws_id, source_type=source_type, source_id=source_id,
                title=title[:255], created_by=payload.get("created_by"), status="pending",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
        else:
            doc.title = title[:255]
            doc.workspace_id = ws_id
            doc.created_by = payload.get("created_by")
            doc.is_active = True

        # ---- 不可索引 / 抽取失败 → 记状态后返回 ----
        if payload["status"] != "ok":
            doc.status = payload["status"]
            doc.error_msg = "未抽取到文本" if payload["status"] == "failed" else "不支持的文件类型"
            db.commit()
            logger.info(f"[KB] 索引终止 {source_type}/{source_id}: {doc.status}")
            return

        text = payload["text"]
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        # ---- 内容未变且已索引 → 跳过重复 embedding ----
        if doc.status == "indexed" and doc.content_hash == content_hash:
            logger.info(f"[KB] 内容未变，跳过 {source_type}/{source_id}")
            return

        chunks = chunk_text(text)
        if not chunks:
            doc.status = "failed"
            doc.error_msg = "切片结果为空"
            db.commit()
            return

        # ---- 写 Chroma（写锁内：先删旧分片再写入；embedding 由 collection.add 自动触发）----
        ids = [f"{source_type}:{source_id}:{i}" for i in range(len(chunks))]
        metadatas = []
        for i, c in enumerate(chunks):
            meta = {
                "workspace_id": int(ws_id),
                "source_type": source_type,
                "source_id": int(source_id),
                "chunk_index": i,
                "title": title[:255],
                "created_by": int(payload.get("created_by") or 0),
                "created_at": (doc.created_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                "is_active": True,
            }
            if source_type == "im":
                meta["conversation_id"] = int(payload["conversation_id"])
            metadatas.append(meta)

        try:
            from app.modules.knowledge.vector_store import chroma_write_lock, get_collection
            with chroma_write_lock():
                col = get_collection()
                col.delete(where={"$and": [
                    {"source_type": {"$eq": source_type}},
                    {"source_id": {"$eq": int(source_id)}},
                ]})
                col.add(ids=ids, documents=chunks, metadatas=metadatas)
        except Exception as e:
            # 拿锁超时 → pending（留待 /knowledge/rebuild 补偿）；其它异常 → failed
            doc.status = "pending" if isinstance(e, TimeoutError) else "failed"
            doc.error_msg = f"{type(e).__name__}: {e}"[:500]
            db.commit()
            logger.error(f"[KB] 写入向量失败 {source_type}/{source_id}: {e}")
            return

        # ---- 回填 DB 元数据 ----
        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == doc.id).delete(synchronize_session=False)
        for i, c in enumerate(chunks):
            db.add(KnowledgeChunk(document_id=doc.id, chunk_index=i,
                                  point_id=ids[i], content=c, char_count=len(c)))
        doc.status = "indexed"
        doc.chunk_count = len(chunks)
        doc.content_hash = content_hash
        doc.error_msg = None
        db.commit()
        logger.info(f"[KB] 索引完成 {source_type}/{source_id}「{title}」→ {len(chunks)} 片")

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception(f"[KB] 索引异常 {source_type}/{source_id}: {e}")
    finally:
        db.close()


def delete_source_index(source_type: str, source_id: int, db=None) -> None:
    """删除来源的向量与分片元数据（文件/公告删除、IM 撤回时调用）

    Chroma 清理失败只告警不阻塞（向量残留可由 /knowledge/rebuild 全量重建消除）。
    """
    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        try:
            from app.modules.knowledge.vector_store import chroma_write_lock, get_collection
            with chroma_write_lock():
                get_collection().delete(where={"$and": [
                    {"source_type": {"$eq": source_type}},
                    {"source_id": {"$eq": int(source_id)}},
                ]})
        except Exception as e:
            logger.warning(f"[KB] 清理向量失败（留待重建）: {source_type}/{source_id}: {e}")

        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id.in_(
                db.query(KnowledgeDocument.id).filter(
                    KnowledgeDocument.source_type == source_type,
                    KnowledgeDocument.source_id == source_id,
                )
            )
        ).delete(synchronize_session=False)
        db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_type == source_type,
            KnowledgeDocument.source_id == source_id,
        ).update({"is_active": False, "chunk_count": 0}, synchronize_session=False)
        db.commit()
        logger.info(f"[KB] 已删除索引 {source_type}/{source_id}")
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception(f"[KB] 删除索引异常 {source_type}/{source_id}: {e}")
    finally:
        if own_db:
            db.close()
