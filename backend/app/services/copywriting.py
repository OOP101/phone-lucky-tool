"""智能文案生成服务：商品描述 / 广告语 / 活动文案 / SEO 标签，多语言。"""
import asyncio
import logging
import queue as queue_mod
import threading
from typing import Iterator, List, Optional

from sqlalchemy.orm import Session

from app.core.llm.base import extract_usage
from app.core.llm.factory import get_llm
from app.db.models import ApiUsage
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_LANG_NAMES = {
    "en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic",
    "ja": "Japanese", "ko": "Korean", "de": "German", "ru": "Russian",
    "pt": "Portuguese", "it": "Italian", "zh": "Chinese",
}


def _system(style: str, tone: str) -> str:
    return (
        f"你是一名资深的跨境电商营销文案专家。"
        f"请以【{style or '专业'}】风格、【{tone or '亲切'}】语气创作，"
        "文案需突出卖点、符合目标市场文化、可直接投放。"
    )


_SPEC = {
    "title": ("copywriting_title", "请生成商品标题。"),
    "description": ("copywriting_description", "请生成商品详情描述。"),
    "ad": ("copywriting_ad", "请生成一条适用于 Google/Facebook 投放的广告语。"),
    "campaign": ("copywriting_title", "请生成促销活动主题文案。"),
    "keywords": ("copywriting_keywords", "请生成 SEO 关键词标签（逗号分隔）。"),
}

_TYPE_KEYS = {
    "ad": ["ad"],
    "campaign": ["campaign"],
    "keywords": ["keywords"],
    "product": ["title", "description", "keywords"],
    "all": ["title", "description", "ad", "keywords"],
}

SECTION_LABELS = {
    "title": "商品标题",
    "description": "商品描述",
    "ad": "广告语",
    "campaign": "活动文案",
    "keywords": "SEO 关键词",
}


def _build_prompt(
    product_name: str,
    category: str,
    selling_points: str,
    target_market: str,
    target_language: str,
) -> str:
    lang_name = _LANG_NAMES.get(target_language, target_language)
    return (
        f"商品名称：{product_name}\n"
        f"品类：{category}\n"
        f"卖点关键词：{selling_points}\n"
        f"目标市场：{target_market}\n"
        f"目标语言：{target_language}（{lang_name}）\n"
    )


def stream_copywriting(
    copy_type: str,
    product_name: str,
    category: Optional[str] = "",
    selling_points: Optional[str] = "",
    target_market: Optional[str] = "",
    target_language: str = "en",
    style: Optional[str] = "",
    tone: Optional[str] = "",
) -> Iterator[tuple]:
    """SSE 流式生成：多段文案线程级并发，逐段实时产出。

    产出 (event, data) 事件序列：
      section_start {key, label}
      delta         {key, text}
      section_end   {key}
      error         {key, message}   单段失败不影响其他段
      done          {keys, result, errors}
    保留与非流式接口一致的并发延迟（≈最慢一段），同时客户端逐字可见。
    """
    base = _build_prompt(product_name, category, selling_points, target_market, target_language)
    system = _system(style, tone)
    keys = _TYPE_KEYS.get(copy_type, _TYPE_KEYS["all"])
    llm = get_llm()

    q: "queue_mod.Queue[tuple]" = queue_mod.Queue()
    texts: dict = {k: "" for k in keys}
    errors: dict = {}
    finished_lock = threading.Lock()
    finished_count = {"n": 0}
    SENTINEL = ("__worker_done__", None)

    def _worker(key: str) -> None:
        task_name, extra = _SPEC[key]
        prompt = base + extra
        q.put(("section_start", {"key": key, "label": SECTION_LABELS.get(key, key)}))
        try:
            for kind, piece in llm.stream_events(prompt, system=system, task=task_name):
                if kind != "content":
                    # 推理模型的思考过程不转发（多段并发会交错），段落级加载动效已足够反馈
                    continue
                texts[key] += piece
                q.put(("delta", {"key": key, "text": piece}))
            q.put(("section_end", {"key": key}))
        except Exception as e:  # noqa: BLE001
            logger.warning("文案段落 %s 流式生成失败: %s", key, e)
            errors[key] = str(e)
            q.put(("error", {"key": key, "message": str(e)}))
        finally:
            with finished_lock:
                finished_count["n"] += 1
            q.put(SENTINEL)

    threads = [threading.Thread(target=_worker, args=(k,), daemon=True) for k in keys]
    for t in threads:
        t.start()

    done_workers = 0
    while done_workers < len(threads):
        event, data = q.get()
        if event == "__worker_done__":
            done_workers += 1
        else:
            yield event, data

    for t in threads:
        t.join()

    # token 用量独立会话落库（StreamingResponse 迭代时请求级 db 已关闭）
    db = SessionLocal()
    try:
        for key in keys:
            task_name, extra = _SPEC[key]
            prompt_tokens, completion_tokens = extract_usage(None, base + extra, texts[key])
            db.add(ApiUsage(
                endpoint="/copywriting/stream",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ))
        db.commit()
    finally:
        db.close()

    result = {k: texts[k] for k in keys if texts.get(k)}
    yield "done", {"keys": keys, "result": result, "errors": errors}


async def generate_copywriting_async(
    db: Session,
    copy_type: str,
    product_name: str,
    category: Optional[str] = "",
    selling_points: Optional[str] = "",
    target_market: Optional[str] = "",
    target_language: str = "en",
    style: Optional[str] = "",
    tone: Optional[str] = "",
) -> dict:
    """生成营销文案，copy_type: product | ad | campaign | keywords | all。

    多段文案（product/all）通过 asyncio.gather 并发调用 LLM，延迟约为最慢一段。
    """
    base = _build_prompt(product_name, category, selling_points, target_market, target_language)

    llm = get_llm()
    system = _system(style, tone)
    usage_rows: List[ApiUsage] = []

    async def _gen(task: str, extra: str) -> str:
        r = await llm.agenerate(base + extra, system=system, task=task)
        prompt_tokens, completion_tokens = extract_usage(r, base + extra, r.content)
        usage_rows.append(
            ApiUsage(endpoint="/copywriting", prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        )
        return r.content

    keys = _TYPE_KEYS.get(copy_type, _TYPE_KEYS["all"])
    results = await asyncio.gather(*(_gen(*_SPEC[k]) for k in keys))

    for row in usage_rows:
        db.add(row)
    db.commit()
    return dict(zip(keys, results))


def generate_copywriting(db: Session, **kwargs) -> dict:
    """同步入口（批量等场景使用），内部复用并发的异步实现。"""
    return asyncio.run(generate_copywriting_async(db, **kwargs))


def generate_batch(db: Session, products: List[dict], target_language: str = "en") -> List[dict]:
    """批量生成多商品多语言文案。"""
    results = []
    for p in products:
        try:
            r = generate_copywriting(
                db,
                copy_type="product",
                product_name=p.get("name", ""),
                selling_points=p.get("selling_points", ""),
                target_market=p.get("target_market", ""),
                target_language=target_language,
            )
            results.append({"name": p.get("name"), "ok": True, "result": r})
        except Exception as e:  # noqa: BLE001
            results.append({"name": p.get("name"), "ok": False, "error": str(e)})
    db.commit()
    return results
