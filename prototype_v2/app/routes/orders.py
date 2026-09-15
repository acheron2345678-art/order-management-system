from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Order
from ..realtime.manager import manager
from ..schemas import OrderCreate, OrderOut, OrderStatusUpdate
from ..services.order_service import create_order, get_order_or_404, transition_order

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderOut, status_code=201)
async def create(payload: OrderCreate, db: Session = Depends(get_db)):
    order = create_order(db, payload)
    event = {
        "type": "ORDER_CREATED",
        "order_id": order.id,
        "store_id": order.store_id,
        "status": order.status.value,
        "total_amount": float(order.total_amount),
    }
    await manager.broadcast_order(order.id, event)
    await manager.broadcast_merchant(order.store_id, event)
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return get_order_or_404(db, order_id)


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_id)
    order = transition_order(db, order, payload.status)
    event = {
        "type": "ORDER_STATUS_UPDATED",
        "order_id": order.id,
        "store_id": order.store_id,
        "status": order.status.value,
        "updated_at": order.updated_at.isoformat(),
    }
    await manager.broadcast_order(order.id, event)
    await manager.broadcast_merchant(order.store_id, event)
    return order
