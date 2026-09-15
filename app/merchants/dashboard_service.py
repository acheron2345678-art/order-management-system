from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.orders.models import (
    OrderItem,
    SwiggyOrders,
)

from app.products.models import Product


PLATFORM = "swiggy"


def get_merchant_dashboard_summary(
    db: Session,
    restaurant_id: int,
):

    # =====================================================
    # MENU / INVENTORY SUMMARY
    # =====================================================

    base_query = (
        db.query(
            Product
        )
        .filter(
            Product.platform
            ==
            PLATFORM,

            Product.restaurant_id
            ==
            restaurant_id,
        )
    )

    total_items = (
        base_query.count()
    )

    active_items = (
        base_query
        .filter(
            Product.is_active.is_(
                True
            )
        )
        .count()
    )

    out_of_stock_items = (
        base_query
        .filter(
            Product.stock_quantity
            <=
            0
        )
        .count()
    )

    low_stock_items = (
        base_query
        .filter(
            Product.stock_quantity
            >
            0,

            Product.stock_quantity
            <=
            Product.reorder_level,
        )
        .count()
    )

    bestseller_items = (
        base_query
        .filter(
            Product.is_bestseller.is_(
                True
            )
        )
        .count()
    )

    category_count = (
        db.query(
            func.count(
                func.distinct(
                    Product.menu_category
                )
            )
        )
        .filter(
            Product.platform
            ==
            PLATFORM,

            Product.restaurant_id
            ==
            restaurant_id,

            Product.menu_category.isnot(
                None
            ),

            Product.menu_category
            !=
            "",
        )
        .scalar()
        or
        0
    )

    # =====================================================
    # ORDER SUMMARY
    # =====================================================

    order_rows = (
        db.query(
            SwiggyOrders.status,

            func.count(
                SwiggyOrders.id
            ).label(
                "order_count"
            ),

            func.coalesce(
                func.sum(
                    SwiggyOrders.amount
                ),
                0,
            ).label(
                "order_amount"
            ),
        )
        .filter(
            SwiggyOrders.restaurant_id
            ==
            restaurant_id
        )
        .group_by(
            SwiggyOrders.status
        )
        .all()
    )

    order_counts = {
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "cancelled": 0,
    }

    total_orders = 0

    completed_revenue = Decimal(
        "0.00"
    )

    for (
        status,
        order_count,
        order_amount,
    ) in order_rows:

        normalized_status = (
            status
            or
            ""
        ).strip().lower()

        order_count = int(
            order_count
            or
            0
        )

        total_orders += (
            order_count
        )

        if normalized_status in order_counts:

            order_counts[
                normalized_status
            ] = order_count

        if normalized_status == "completed":

            completed_revenue = Decimal(
                str(
                    order_amount
                    or
                    0
                )
            ).quantize(
                Decimal(
                    "0.01"
                )
            )

    # =====================================================
    # RECENT ORDERS
    # =====================================================

    item_stats = (
        db.query(
            OrderItem.order_id.label(
                "order_id"
            ),

            func.min(
                OrderItem.created_at
            ).label(
                "created_at"
            ),

            func.sum(
                OrderItem.quantity
            ).label(
                "item_count"
            ),
        )
        .filter(
            OrderItem.platform
            ==
            PLATFORM
        )
        .group_by(
            OrderItem.order_id
        )
        .subquery()
    )

    recent_order_rows = (
        db.query(
            SwiggyOrders,

            item_stats.c.created_at,

            item_stats.c.item_count,
        )
        .outerjoin(
            item_stats,

            item_stats.c.order_id
            ==
            SwiggyOrders.id,
        )
        .filter(
            SwiggyOrders.restaurant_id
            ==
            restaurant_id
        )
        .order_by(
            item_stats.c.created_at.desc(),

            SwiggyOrders.order_date.desc(),

            SwiggyOrders.id.desc(),
        )
        .limit(
            5
        )
        .all()
    )

    recent_orders = []

    for (
        order,
        created_at,
        item_count,
    ) in recent_order_rows:

        order.sort_created_at = (
            created_at
        )

        order.item_count = int(
            item_count
            or
            0
        )

        recent_orders.append(
            order
        )

    # =====================================================
    # STOCK ATTENTION
    # =====================================================

    stock_alert_items = (
        db.query(
            Product
        )
        .filter(
            Product.platform
            ==
            PLATFORM,

            Product.restaurant_id
            ==
            restaurant_id,

            Product.is_active.is_(
                True
            ),

            Product.stock_quantity
            <=
            Product.reorder_level,
        )
        .order_by(
            Product.stock_quantity.asc(),

            Product.product_name.asc(),
        )
        .limit(
            5
        )
        .all()
    )

    # =====================================================
    # RESULT
    # =====================================================

    return {
        "total_items":
            total_items,

        "active_items":
            active_items,

        "category_count":
            category_count,

        "bestseller_items":
            bestseller_items,

        "low_stock_items":
            low_stock_items,

        "out_of_stock_items":
            out_of_stock_items,

        "total_orders":
            total_orders,

        "pending_orders":
            order_counts[
                "pending"
            ],

        "processing_orders":
            order_counts[
                "processing"
            ],

        "completed_orders":
            order_counts[
                "completed"
            ],

        "cancelled_orders":
            order_counts[
                "cancelled"
            ],

        "completed_revenue":
            completed_revenue,

        "recent_orders":
            recent_orders,

        "stock_alert_items":
            stock_alert_items,
    }