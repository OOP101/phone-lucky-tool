"""智能文案生成 API。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import BatchCopywritingRequest, CopywritingRequest
from app.services import copywriting as copy_service

router = APIRouter()


@router.post("/generate")
async def generate_copy(req: CopywritingRequest, db: Session = Depends(get_db)):
    """生成营销文案（多段文案并发调用 LLM）。"""
    return await copy_service.generate_copywriting_async(
        db,
        copy_type=req.copy_type,
        product_name=req.product_name,
        category=req.category,
        selling_points=req.selling_points,
        target_market=req.target_market,
        target_language=req.target_language,
        style=req.style,
        tone=req.tone,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
def stream_copy(req: CopywritingRequest):
    """生成营销文案（SSE 流式）。

    事件序列：
      section_start {"key", "label"} —— 某一段开始（key: title/description/ad/campaign/keywords）
      delta         {"key", "text"}  —— 该段正文增量，可多条；多段并发、按 key 分别累积
      section_end   {"key"}          —— 该段完成
      error         {"key", "message"} —— 单段失败（不影响其他段）
      done          {"keys", "result", "errors"} —— 全部结束，result 为完整文案
    """
    def event_gen():
        yield _sse("begin", {"copy_type": req.copy_type})
        for event, data in copy_service.stream_copywriting(
            copy_type=req.copy_type,
            product_name=req.product_name,
            category=req.category,
            selling_points=req.selling_points,
            target_market=req.target_market,
            target_language=req.target_language,
            style=req.style,
            tone=req.tone,
        ):
            yield _sse(event, data)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/batch")
def generate_batch(req: BatchCopywritingRequest, db: Session = Depends(get_db)):
    """批量生成多商品文案。"""
    return {"results": copy_service.generate_batch(db, req.products, req.target_language)}
