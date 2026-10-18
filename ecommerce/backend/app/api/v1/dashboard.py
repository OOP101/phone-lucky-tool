"""工作台聚合接口：首屏关键指标一次拉齐。"""
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.models import (
    ApiUsage,
    Conversation,
    Customer,
    FollowUp,
    KnowledgeDoc,
    Product,
)
from app.db.session import get_db

router = APIRouter()

_LOW_STOCK_THRESHOLD = 10


@router.get("/overview", summary="工作台聚合指标")
def overview(
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_user),
):
    """工作台首屏：客服 / 客户 / 商品 / 知识 / AI 用量 等关键计数。"""
    tenant = current.get("tenant_id", "default")
    today_start = datetime.combine(datetime.now().date(), time.min)
    week_start = datetime.combine((datetime.now() - timedelta(days=7)).date(), time.min)
    month_start = datetime.combine(
        (datetime.now() - timedelta(days=30)).date(), time.min
    )

    # 客服会话
    conv_q = db.query(Conversation).filter(Conversation.tenant_id == tenant)
    conversations_today = conv_q.filter(Conversation.created_at >= today_start).count()
    conversations_week = conv_q.filter(Conversation.created_at >= week_start).count()
    conversations_total = conv_q.count()

    # 客户
    cust_q = db.query(Customer).filter(Customer.tenant_id == tenant)
    customers_total = cust_q.count()
    customers_month = cust_q.filter(Customer.created_at >= month_start).count()
    grade_a = cust_q.filter(Customer.grade == "A").count()
    pending_followups = (
        db.query(FollowUp)
        .filter(
            FollowUp.tenant_id == tenant,
            FollowUp.next_follow_date.isnot(None),
            FollowUp.next_follow_date >= today_start,
        )
        .count()
    )

    # 商品
    prod_q = db.query(Product).filter(Product.tenant_id == tenant)
    products_total = prod_q.count()
    products_active = prod_q.filter(Product.status == "active").count()
    low_stock = prod_q.filter(Product.stock_quantity < _LOW_STOCK_THRESHOLD).count()
    stock_value = (
        db.query(func.coalesce(func.sum(Product.stock_quantity * Product.cost_price), 0.0))
        .filter(Product.tenant_id == tenant)
        .scalar()
    )

    # 知识库
    docs_total = (
        db.query(KnowledgeDoc).filter(KnowledgeDoc.tenant_id == tenant).count()
    )
    docs_indexed = (
        db.query(KnowledgeDoc)
        .filter(KnowledgeDoc.tenant_id == tenant, KnowledgeDoc.status == "indexed")
        .count()
    )

    # AI 用量（必须按租户过滤，否则泄露其他租户用量）
    usage_today = (
        db.query(
            func.coalesce(func.sum(ApiUsage.prompt_tokens + ApiUsage.completion_tokens), 0)
        )
        .filter(ApiUsage.tenant_id == tenant, ApiUsage.created_at >= today_start)
        .scalar()
    )
    ai_calls_today = (
        db.query(ApiUsage)
        .filter(ApiUsage.tenant_id == tenant, ApiUsage.created_at >= today_start)
        .count()
    )

    return {
        "chat": {
            "today": conversations_today,
            "week": conversations_week,
            "total": conversations_total,
        },
        "customer": {
            "total": customers_total,
            "month_new": customers_month,
            "grade_a": grade_a,
            "pending_followups": pending_followups,
        },
        "product": {
            "total": products_total,
            "active": products_active,
            "low_stock": low_stock,
            "stock_value": round(float(stock_value), 2),
        },
        "knowledge": {
            "total": docs_total,
            "indexed": docs_indexed,
        },
        "ai": {
            "calls_today": ai_calls_today,
            "tokens_today": int(usage_today),
        },
    }
