from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core.config import settings
from ..models import MenuItem, Order, OrderItem, OrderStatus, Store
from ..schemas import OrderCreate


TWOPLACES = Decimal("0.01")

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def create_order(db: Session, payload: OrderCreate) -> Order:
    store = db.get(Store, payload.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    if not store.is_open:
        raise HTTPException(status_code=409, detail="Store is currently closed")

    requested_ids = {item.menu_item_id for item in payload.items}
    menu_items = db.scalars(select(MenuItem).where(MenuItem.id.in_(requested_ids))).all()
    by_id = {item.id: item for item in menu_items}

    if len(by_id) != len(requested_ids):
        raise HTTPException(status_code=400, detail="One or more menu items do not exist")

    subtotal = Decimal("0.00")
    staged: list[tuple[MenuItem, int, Decimal]] = []
    for requested in payload.items:
        menu_item = by_id[requested.menu_item_id]
        if menu_item.store_id != store.id:
            raise HTTPException(status_code=400, detail=f"{menu_item.name} belongs to another store")
        if not menu_item.is_available:
            raise HTTPException(status_code=409, detail=f"{menu_item.name} is unavailable")
        line_total = money(menu_item.price * requested.quantity)
        subtotal += line_total
        staged.append((menu_item, requested.quantity, line_total))

    subtotal = money(subtotal)
    tax_amount = money(subtotal * Decimal(str(settings.tax_rate)))
    total_amount = money(subtotal + tax_amount)

    order = Order(
        store_id=store.id,
        customer_id=payload.customer_id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        notes=payload.notes,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
    )
    db.add(order)
    db.flush()

    for menu_item, quantity, line_total in staged:
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                quantity=quantity,
                unit_price=money(menu_item.price),
                line_total=line_total,
            )
        )

    db.commit()
    return get_order_or_404(db, order.id)


def transition_order(db: Session, order: Order, requested_status: OrderStatus) -> Order:
    if requested_status == order.status:
        return order
    allowed = ALLOWED_TRANSITIONS[order.status]
    if requested_status not in allowed:
        allowed_names = ", ".join(sorted(item.value for item in allowed)) or "none"
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition {order.status.value} -> {requested_status.value}. Allowed: {allowed_names}",
        )
    order.status = requested_status
    db.add(order)
    db.commit()
    return get_order_or_404(db, order.id)
