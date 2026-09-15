from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Order, OrderStatus
from ..schemas import DashboardAnalytics, OrderOut
from ..services.analytics_service import get_analytics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/analytics", response_model=DashboardAnalytics)
def analytics(store_id: int = Query(gt=0), db: Session = Depends(get_db)):
    return get_analytics(db, store_id)


@router.get("/orders", response_model=list[OrderOut])
def dashboard_orders(
    store_id: int = Query(gt=0),
    active_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.store_id == store_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    if active_only:
        stmt = stmt.where(Order.status.notin_([OrderStatus.DELIVERED, OrderStatus.CANCELLED]))
    return db.scalars(stmt).all()
