"""多语言翻译引擎：持久化术语库 + 翻译记忆 + LLM 翻译。

术语库落地为数据库表（见 app.db.models.Term）；翻译记忆为
「进程内 LRU + SQLite 持久化」两级缓存，跨重启生效，且有容量上限。
"""
import hashlib
import json
import logging
import threading
from collections import OrderedDict
from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.llm.base import extract_usage
from app.core.llm.factory import get_llm
from app.db.models import ApiUsage, Term, TranslationMemory

logger = logging.getLogger(__name__)

# 翻译记忆 LRU 容量：超出后淘汰最久未命中的条目（持久化仍在库中）
_MEMORY_LRU_SIZE = 10_000
_translation_memory_lru: "OrderedDict[str, str]" = OrderedDict()
# FastAPI 同步路由在线程池中执行（copywriting 流式也用了线程），LRU 是
# 复合操作（赋值 + move_to_end + 淘汰），需互斥保护，避免并发下 RuntimeError/KeyError
_lru_lock = threading.Lock()


def _memory_key(text: str, src: str, tgt: str) -> str:
    return hashlib.md5(f"{src}:{tgt}:{text}".encode("utf-8")).hexdigest()


def _lru_get(key: str) -> Optional[str]:
    with _lru_lock:
        hit = _translation_memory_lru.get(key)
        if hit is not None:
            _translation_memory_lru.move_to_end(key)
    return hit


def _lru_put(key: str, value: str) -> None:
    with _lru_lock:
        _translation_memory_lru[key] = value
        _translation_memory_lru.move_to_end(key)
        while len(_translation_memory_lru) > _MEMORY_LRU_SIZE:
            _translation_memory_lru.popitem(last=False)


def _memory_lookup(db: Session, key: str) -> Optional[str]:
    """两级查找：进程内 LRU -> 数据库。"""
    hit = _lru_get(key)
    if hit is not None:
        return hit
    row = db.query(TranslationMemory).filter(TranslationMemory.hash == key).first()
    if row:
        _lru_put(key, row.translated)
        return row.translated
    return None


def _memory_store(db: Session, key: str, translated: str) -> None:
    _lru_put(key, translated)
    if db.query(TranslationMemory).filter(TranslationMemory.hash == key).first():
        return
    # hash 有唯一约束：并发翻译同一新句时「检查-然后-插入」存在竞态，
    # 用 SAVEPOINT 让重复插入在并发冲突时静默降级，且不污染外层事务（ApiUsage 仍正常落库）
    try:
        with db.begin_nested():  # SAVEPOINT
            db.add(TranslationMemory(hash=key, translated=translated))
            db.flush()
    except IntegrityError:
        logger.debug("翻译记忆并发写入冲突，已忽略重复行：%s", key)


def _load_terms(db: Session) -> Dict[str, Dict[str, str]]:
    """从数据库加载术语库。"""
    return {t.term: json.loads(t.translations) for t in db.query(Term).all()}


def _term_glossary(terms: Dict[str, Dict[str, str]], target_language: str) -> str:
    if not terms:
        return ""
    lines = [
        f"{k} = {v.get(target_language, v.get('en', ''))}"
        for k, v in terms.items()
    ]
    return "术语表（请严格使用下列标准译法，不要意译）：\n" + "\n".join(lines) + "\n\n"


def translate(
    db: Session,
    text: str,
    source_language: str = "zh",
    target_language: str = "en",
    use_terminology: bool = True,
    use_memory: bool = True,
) -> dict:
    """实时翻译，优先命中翻译记忆（LRU + 库），启用术语库保证专业一致性。"""
    key = _memory_key(text, source_language, target_language)

    if use_memory:
        hit = _memory_lookup(db, key)
        if hit is not None:
            return {"translation": hit, "source": "memory"}

    term_block = ""
    if use_terminology:
        term_block = _term_glossary(_load_terms(db), target_language)

    prompt = (
        f"{term_block}"
        f"源语言：{source_language}\n"
        f"目标语言：{target_language}\n"
        f"待翻译内容：{text}\n"
        "请输出精准、本地化的翻译结果，仅输出译文。"
    )

    result = get_llm().generate(prompt, task="translation")
    translation = result.content.strip()

    if use_memory:
        _memory_store(db, key, translation)

    prompt_tokens, completion_tokens = extract_usage(result, prompt, translation)
    db.add(ApiUsage(endpoint="/translation", prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens))
    db.commit()

    return {"translation": translation, "source": "llm"}


def add_terminology(term: str, translations: Dict[str, str], category: str = "trade", db: Session = None) -> None:
    """新增或更新术语（upsert）。"""
    if db is None:
        from app.db.session import SessionLocal

        db = SessionLocal()
        own = True
    else:
        own = False
    try:
        existing = db.query(Term).filter(Term.term == term).first()
        payload = json.dumps(translations, ensure_ascii=False)
        if existing:
            existing.translations = payload
            existing.category = category
        else:
            db.add(Term(term=term, translations=payload, category=category))
        db.commit()
    finally:
        if own:
            db.close()


def list_terminology(db: Session = None) -> Dict[str, Dict[str, str]]:
    """列出全部术语。"""
    if db is None:
        from app.db.session import SessionLocal

        db = SessionLocal()
        own = True
    else:
        own = False
    try:
        return _load_terms(db)
    finally:
        if own:
            db.close()
