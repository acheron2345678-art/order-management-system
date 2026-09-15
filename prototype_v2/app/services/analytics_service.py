from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import Order, OrderItem, OrderStatus
from ..schemas import DashboardAnalytics, RevenuePoint, StatusBreakdownItem, TopItem


ACTIVE = {
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.PREPARING,
    OrderStatus.OUT_FOR_DELIVERY,
}


def get_analytics(db: Session, store_id: int) -> DashboardAnalytics:
    total_revenue = db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.store_id == store_id,
            Order.status == OrderStatus.DELIVERED,
        )
    ) or Decimal("0")

    order_count = db.scalar(select(func.count(Order.id)).where(Order.store_id == store_id)) or 0
    active_orders = db.scalar(
        select(func.count(Order.id)).where(Order.store_id == store_id, Order.status.in_(ACTIVE))
    ) or 0

    completed_count = db.scalar(
        select(func.count(Order.id)).where(Order.store_id == store_id, Order.status == OrderStatus.DELIVERED)
    ) or 0
    average = (Decimal(total_revenue) / completed_count) if completed_count else Decimal("0")

    top_rows = db.execute(
        select(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.line_total).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.store_id == store_id, Order.status != OrderStatus.CANCELLED)
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    ).all()
    top_items = [TopItem(name=row[0], quantity=int(row[1]), revenue=Decimal(row[2])) for row in top_rows]

    status_rows = db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.store_id == store_id)
        .group_by(Order.status)
    ).all()
    status_map = {status.value if hasattr(status, "value") else str(status): int(count) for status, count in status_rows}
    status_breakdown = [
        StatusBreakdownItem(status=status.value, count=status_map.get(status.value, 0))
        for status in OrderStatus
    ]

    start = date.today() - timedelta(days=6)
    trend_rows = db.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.coalesce(
                func.sum(case((Order.status == OrderStatus.DELIVERED, Order.total_amount), else_=0)), 0
            ).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(Order.store_id == store_id, func.date(Order.created_at) >= start.isoformat())
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    ).all()
    trend_map: dict[str, tuple[Decimal, int]] = {
        str(row.day): (Decimal(row.revenue or 0), int(row.orders or 0)) for row in trend_rows
    }
    revenue_trend: list[RevenuePoint] = []
    for offset in range(7):
        current = start + timedelta(days=offset)
        revenue, orders = trend_map.get(current.isoformat(), (Decimal("0"), 0))
        revenue_trend.append(RevenuePoint(date=current, revenue=revenue, orders=orders))

    return DashboardAnalytics(
        store_id=store_id,
        total_revenue=Decimal(total_revenue),
        order_count=int(order_count),
        active_orders=int(active_orders),
        average_order_value=average,
        top_items=top_items,
        status_breakdown=status_breakdown,
        revenue_trend=revenue_trend,
    )
