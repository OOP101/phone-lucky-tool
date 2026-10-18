"""知识库管理服务：文档解析、清洗、分块、向量化、入库。"""
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.embeddings.factory import get_embedding
from app.core.vector_store.factory import get_vector_store
from app.db.models import KnowledgeDoc
from app.utils.chunking import chunk_text
from app.utils.text_clean import sanitize

logger = logging.getLogger(__name__)

SUPPORTED_EXT = {".txt", ".md", ".csv", ".pdf", ".docx"}


def parse_file(filename: str, content: bytes) -> str:
    """按扩展名解析文档内容为纯文本。"""
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md", ".csv"):
        return content.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"解析 PDF 失败（需安装 pypdf）：{e}")
    if ext == ".docx":
        try:
            from docx import Document
            import io

            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"解析 Word 失败（需安装 python-docx）：{e}")
    raise ValueError(f"不支持的文件类型：{ext}")


def add_document(db: Session, filename: str, content: bytes, tenant_id: str = "default") -> dict:
    """解析并入库一篇文档，返回摘要。同名文档按替换语义处理：先删旧向量与旧记录。"""
    text = parse_file(filename, content)
    text = sanitize(text)
    if not text:
        raise ValueError("文档内容为空")

    chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks:
        raise ValueError("文档切分后无有效内容")

    # 同名替换（限同一租户内）语义保持；但调整时序：先写新、后删旧。
    # 旧实现先删旧向量+commit 再 embedding/写向量，中途任何失败都会永久丢失已有知识。
    existing = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.filename == filename, KnowledgeDoc.tenant_id == tenant_id)
        .first()
    )

    # 新 doc_id 与旧向量互不干扰，先完成 embedding 与向量写入
    embedding = get_embedding()
    vectors = embedding.embed(chunks)
    doc_id = uuid.uuid4().hex[:16]
    ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": filename, "doc_id": doc_id, "tenant_id": tenant_id, "chunk_index": i}
        for i in range(len(chunks))
    ]

    get_vector_store().add(ids, chunks, vectors, metadatas)

    # 新向量已就位，此时才删除旧数据：任何失败点旧知识均完好
    if existing:
        _delete_vectors_for(existing)
        db.delete(existing)

    record = KnowledgeDoc(
        doc_id=doc_id,
        tenant_id=tenant_id,
        filename=filename,
        content_type=Path(filename).suffix.lower(),
        status="indexed",
        chunk_count=len(chunks),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # 文档增删后使 BM25 索引缓存失效（见 rag/retriever.py）
    from app.services.rag.retriever import invalidate_bm25_cache

    invalidate_bm25_cache()

    return {
        "id": record.id,
        "doc_id": doc_id,
        "filename": filename,
        "chunk_count": len(chunks),
        "status": "indexed",
    }


def add_documents_bulk(
    db: Session,
    files: List[tuple],
    tenant_id: str = "default",
    embed_batch_size: int = 32,
    progress=None,
) -> dict:
    """批量入库多篇文档（千级语料导入专用）。

    - 全部文档解析/分块后统一向量化（按 embed_batch_size 分批调用 Embedding）；
    - 向量库一次性写入，规避 memory 实现逐文档全量 JSON 落盘的 O(n²) 开销；
    - SQLite 元数据单次提交；同名替换语义与 add_document 一致。

    files: [(filename, content_bytes), ...]；progress: 可选回调 (done, total, filename)。
    返回 {"indexed", "total_chunks", "skipped": [(filename, reason), ...]}。
    """
    prepared: List[tuple] = []  # (filename, chunks)
    skipped: List[tuple] = []

    for i, (filename, content) in enumerate(files):
        try:
            text = parse_file(filename, content)
            text = sanitize(text)
            chunks = (
                chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
                if text else []
            )
            if not chunks:
                skipped.append((filename, "文档为空或切分后无有效内容"))
            else:
                prepared.append((filename, chunks))
        except Exception as e:  # noqa: BLE001
            skipped.append((filename, str(e)[:150]))
        if progress:
            progress(i + 1, len(files), filename)

    if not prepared:
        return {"indexed": 0, "total_chunks": 0, "skipped": skipped}

    # 同名替换的旧记录查询后置到向量写入成功之后（与 add_document 相同的时序修正）：
    # 旧实现先删旧数据+commit，后续 embedding/向量写入任一失败都会永久丢失全部被替换文档。
    embedding = get_embedding()
    all_ids: List[str] = []
    all_texts: List[str] = []
    all_vectors: List[List[float]] = []
    all_metas: List[dict] = []
    pending_texts: List[str] = []
    pending_refs: List[tuple] = []  # (id, text, metadata)
    records: List[KnowledgeDoc] = []

    def _flush_embeddings():
        if not pending_texts:
            return
        vectors = embedding.embed(pending_texts)
        for (chunk_id, text, meta), vector in zip(pending_refs, vectors):
            all_ids.append(chunk_id)
            all_texts.append(text)
            all_metas.append(meta)
            all_vectors.append(vector)
        pending_texts.clear()
        pending_refs.clear()

    for filename, chunks in prepared:
        doc_id = uuid.uuid4().hex[:16]
        for i, chunk in enumerate(chunks):
            pending_texts.append(chunk)
            pending_refs.append((
                f"{doc_id}:{i}",
                chunk,
                {"source": filename, "doc_id": doc_id,
                 "tenant_id": tenant_id, "chunk_index": i},
            ))
        if len(pending_texts) >= embed_batch_size:
            _flush_embeddings()
        records.append(KnowledgeDoc(
            doc_id=doc_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=Path(filename).suffix.lower(),
            status="indexed",
            chunk_count=len(chunks),
        ))
    _flush_embeddings()

    # 向量库分批写入（Chroma 单批有上限；memory 实现也只需一次落盘/批）
    store = get_vector_store()
    write_batch = 500
    for start in range(0, len(all_ids), write_batch):
        end = start + write_batch
        store.add(
            all_ids[start:end],
            all_texts[start:end],
            all_vectors[start:end],
            all_metas[start:end],
        )

    # 新向量全部写入成功后，才删除同名旧数据并落库新记录（原子性更好）
    existing = (
        db.query(KnowledgeDoc)
        .filter(
            KnowledgeDoc.tenant_id == tenant_id,
            KnowledgeDoc.filename.in_([name for name, _ in prepared]),
        )
        .all()
    )
    for record in existing:
        _delete_vectors_for(record)
        db.delete(record)

    db.add_all(records)
    db.commit()

    from app.services.rag.retriever import invalidate_bm25_cache

    invalidate_bm25_cache()

    return {
        "indexed": len(prepared),
        "total_chunks": len(all_ids),
        "skipped": skipped,
    }


def list_documents(db: Session, tenant_id: str = "default") -> List[dict]:
    docs = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.tenant_id == tenant_id)
        .order_by(KnowledgeDoc.created_at.desc())
        .all()
    )
    return [
        {"id": d.id, "filename": d.filename, "status": d.status,
         "chunk_count": d.chunk_count, "created_at": d.created_at.isoformat()}
        for d in docs
    ]


def _delete_vectors_for(record: KnowledgeDoc) -> None:
    """删除一篇文档对应的全部向量。优先按 doc_id 精确匹配；
    历史记录无 doc_id 时回退按 filename 匹配（仅在替换同名文档的上下文中安全）。"""
    store = get_vector_store()
    all_items = store.list_all()
    if record.doc_id:
        ids_to_delete = [item["id"] for item in all_items if item["metadata"].get("doc_id") == record.doc_id]
    else:
        ids_to_delete = [item["id"] for item in all_items if item["metadata"].get("source") == record.filename]
    if ids_to_delete:
        store.delete(ids_to_delete)


def delete_document(db: Session, doc_id: int, tenant_id: str = "default") -> None:
    record = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.id == doc_id, KnowledgeDoc.tenant_id == tenant_id)
        .first()
    )
    if not record:
        return
    _delete_vectors_for(record)
    db.delete(record)
    db.commit()

    from app.services.rag.retriever import invalidate_bm25_cache

    invalidate_bm25_cache()


def search_knowledge(query: str, top_k: int = 5) -> List[dict]:
    """知识库检索（供调试/管理后台使用）。"""
    from app.services.rag.retriever import get_retriever

    return get_retriever().retrieve(query, top_k=top_k)
