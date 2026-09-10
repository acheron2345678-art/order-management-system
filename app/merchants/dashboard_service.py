from sqlalchemy import func
from sqlalchemy.orm import Session

from app.products.models import Product


def get_merchant_dashboard_summary(
    db: Session,
    restaurant_id: int,
):

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
    }