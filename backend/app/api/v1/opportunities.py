"""商机管理 API：商机 CRUD、阶段流转、销售看板与管道统计。"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.models import Customer, Opportunity
from app.db.session import get_db

router = APIRouter()

# 销售阶段定义（顺序即看板列顺序；won/lost 为终态）
STAGES = [
    {"key": "lead", "label": "初步接触", "probability": 20},
    {"key": "need", "label": "需求确认", "probability": 40},
    {"key": "quote", "label": "报价", "probability": 60},
    {"key": "negotiation", "label": "谈判", "probability": 80},
    {"key": "won", "label": "成交", "probability": 100},
    {"key": "lost", "label": "流失", "probability": 0},
]
STAGE_KEYS = {s["key"] for s in STAGES}
# 活跃阶段（看板展示，不含终态）
ACTIVE_STAGE_KEYS = ["lead", "need", "quote", "negotiation"]


# ============ Pydantic Schemas ============

class OpportunityCreate(BaseModel):
    title: str
    customer_id: int
    product_id: Optional[int] = None
    stage: str = "lead"
    expected_amount: float = 0.0
    currency: str = "USD"
    expected_close_date: Optional[datetime] = None
    probability: Optional[int] = None
    notes: Optional[str] = None


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    product_id: Optional[int] = None
    expected_amount: Optional[float] = None
    currency: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    probability: Optional[int] = None
    notes: Optional[str] = None


class StageMove(BaseModel):
    stage: str
    close_reason: Optional[str] = None  # 转入 won/lost 时填写原因


def _serialize(o: Opportunity, customer_name: Optional[str] = None) -> dict:
    return {
        "id": o.id,
        "title": o.title,
        "customer_id": o.customer_id,
        "customer_name": customer_name,
        "product_id": o.product_id,
        "stage": o.stage,
        "expected_amount": o.expected_amount,
        "currency": o.currency,
        "expected_close_date": o.expected_close_date.isoformat() if o.expected_close_date else None,
        "probability": o.probability,
        "close_reason": o.close_reason,
        "notes": o.notes,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


# ============ 阶段元数据 / 看板 / 统计（须在 {id} 路由之前注册）============

@router.get("/stages", summary="销售阶段定义")
def list_stages(user: dict = Depends(get_current_user)):
    """返回销售阶段及对应默认赢单概率。"""
    return {"stages": STAGES}


@router.get("/board/data", summary="销售看板数据")
def board_data(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """按阶段分组返回商机（看板视图），仅含活跃阶段。"""
    opps = (
        db.query(Opportunity)
        .filter(
            Opportunity.tenant_id == user["tenant_id"],
            Opportunity.stage.in_(ACTIVE_STAGE_KEYS),
        )
        .order_by(Opportunity.expected_amount.desc())
        .all()
    )

    # 批量取客户名
    customer_ids = {o.customer_id for o in opps}
    customers = {
        c.id: c.company_name
        for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
    }

    columns = {key: [] for key in ACTIVE_STAGE_KEYS}
    for o in opps:
        columns[o.stage].append(_serialize(o, customers.get(o.customer_id)))

    return {
        "columns": [
            {"key": s["key"], "label": s["label"], "items": columns[s["key"]]}
            for s in STAGES
            if s["key"] in ACTIVE_STAGE_KEYS
        ]
    }


@router.get("/stats/pipeline", summary="销售管道统计")
def pipeline_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """各阶段商机数量/金额，及加权管道金额、赢单率。"""
    opps = (
        db.query(Opportunity)
        .filter(Opportunity.tenant_id == user["tenant_id"])
        .all()
    )

    by_stage = {s["key"]: {"count": 0, "amount": 0.0} for s in STAGES}
    weighted_pipeline = 0.0

    for o in opps:
        if o.stage in by_stage:
            by_stage[o.stage]["count"] += 1
            by_stage[o.stage]["amount"] += o.expected_amount
        if o.stage in ACTIVE_STAGE_KEYS:
            weighted_pipeline += o.expected_amount * o.probability / 100

    won = by_stage["won"]["count"]
    closed = won + by_stage["lost"]["count"]
    win_rate = round(won / closed * 100, 1) if closed else 0.0

    return {
        "by_stage": [
            {
                "key": s["key"],
                "label": s["label"],
                "count": by_stage[s["key"]]["count"],
                "amount": round(by_stage[s["key"]]["amount"], 2),
            }
            for s in STAGES
        ],
        "weighted_pipeline": round(weighted_pipeline, 2),
        "total_open": sum(by_stage[k]["count"] for k in ACTIVE_STAGE_KEYS),
        "win_rate": win_rate,
    }


# ============ 商机 CRUD ============

@router.get("", summary="商机列表")
def list_opportunities(
    stage: Optional[str] = None,
    customer_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取商机列表，支持按阶段/客户/关键词筛选。"""
    query = db.query(Opportunity).filter(Opportunity.tenant_id == user["tenant_id"])

    if stage:
        query = query.filter(Opportunity.stage == stage)
    if customer_id:
        query = query.filter(Opportunity.customer_id == customer_id)
    if keyword:
        query = query.filter(Opportunity.title.contains(keyword))

    opps = query.order_by(Opportunity.updated_at.desc()).all()

    customer_ids = {o.customer_id for o in opps}
    customers = {
        c.id: c.company_name
        for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
    }

    return {
        "total": len(opps),
        "items": [_serialize(o, customers.get(o.customer_id)) for o in opps],
    }


@router.post("", summary="创建商机")
def create_opportunity(
    req: OpportunityCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建新商机。"""
    # 校验客户存在
    customer = db.query(Customer).filter(
        Customer.id == req.customer_id,
        Customer.tenant_id == user["tenant_id"],
    ).first()
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    if req.stage not in STAGE_KEYS:
        raise HTTPException(status_code=400, detail="无效的销售阶段")

    # 未显式给概率时，按阶段默认概率
    default_prob = next(s["probability"] for s in STAGES if s["key"] == req.stage)
    probability = req.probability if req.probability is not None else default_prob

    opp = Opportunity(
        tenant_id=user["tenant_id"],
        title=req.title,
        customer_id=req.customer_id,
        product_id=req.product_id,
        stage=req.stage,
        expected_amount=req.expected_amount,
        currency=req.currency,
        expected_close_date=req.expected_close_date,
        probability=probability,
        notes=req.notes,
        created_by=user["sub"],
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return {"id": opp.id, "title": opp.title}


@router.get("/{opportunity_id}", summary="商机详情")
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取商机详情。"""
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.tenant_id == user["tenant_id"],
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    customer = db.query(Customer).filter(Customer.id == opp.customer_id).first()
    return _serialize(opp, customer.company_name if customer else None)


@router.put("/{opportunity_id}", summary="更新商机")
def update_opportunity(
    opportunity_id: int,
    req: OpportunityUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新商机信息。"""
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.tenant_id == user["tenant_id"],
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(opp, key, value)

    db.commit()
    return {"ok": True, "id": opp.id}


@router.patch("/{opportunity_id}/stage", summary="推进商机阶段")
def move_stage(
    opportunity_id: int,
    req: StageMove,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """推进/回退商机阶段；转入成交或流失时记录原因，并同步概率。"""
    if req.stage not in STAGE_KEYS:
        raise HTTPException(status_code=400, detail="无效的销售阶段")

    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.tenant_id == user["tenant_id"],
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    opp.stage = req.stage
    new_prob = next(s["probability"] for s in STAGES if s["key"] == req.stage)
    opp.probability = new_prob

    if req.stage in ("won", "lost"):
        opp.close_reason = req.close_reason

    db.commit()
    return {"ok": True, "id": opp.id, "stage": opp.stage, "probability": opp.probability}


@router.delete("/{opportunity_id}", summary="删除商机")
def delete_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除商机。"""
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.tenant_id == user["tenant_id"],
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    db.delete(opp)
    db.commit()
    return {"ok": True}
