from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.orders.models import SwiggyOrders
from app.products.models import Product


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
            "swiggy",

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
            "swiggy",

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
    # RESTAURANT ORDER SUMMARY
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
    }