from sqlalchemy.orm import Session

from app.orders.models import (
    SwiggyOrders,
    InsightsOrders,
    OrderItem,
)


def _get_platform_purchases(
    db: Session,
    order_model,
    platform: str,
    client_id: int,
):
    rows = (
        db.query(
            OrderItem,
            order_model,
        )
        .join(
            order_model,
            order_model.id
            ==
            OrderItem.order_id,
        )
        .filter(
            OrderItem.platform
            ==
            platform,

            order_model.client_id
            ==
            client_id,
        )
        .order_by(
            OrderItem.created_at.desc(),
            order_model.id.desc(),
            OrderItem.id.desc(),
        )
        .all()
    )

    purchases = []

    for item, order in rows:

        purchases.append(
            {
                "platform":
                    platform,

                "order_id":
                    order.id,

                "order_number":
                    order.order_number,

                "product_id":
                    item.product_id,

                "product_name":
                    item.product_name,

                "quantity":
                    item.quantity,

                "unit_price":
                    float(
                        item.unit_price
                        or 0
                    ),

                "line_total":
                    float(
                        item.line_total
                        or 0
                    ),

                "status":
                    order.status,

                "order_date":
                    order.order_date,

                "purchase_time":
                    item.created_at,

                "customer_name":
                    order.customer_name,
            }
        )

    return purchases


def get_client_purchases(
    db: Session,
    client_id: int,
):
    swiggy_purchases = (
        _get_platform_purchases(
            db=db,
            order_model=SwiggyOrders,
            platform="swiggy",
            client_id=client_id,
        )
    )

    insights_purchases = (
        _get_platform_purchases(
            db=db,
            order_model=InsightsOrders,
            platform="insights",
            client_id=client_id,
        )
    )

    purchases = (
        swiggy_purchases
        +
        insights_purchases
    )

    purchases.sort(
        key=lambda item: (
            item["purchase_time"],
            item["order_id"],
            item["product_id"],
        ),
        reverse=True,
    )

    return purchases