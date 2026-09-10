from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import (
    ORDER_STATUSES,
    ORDER_STATUS_TRANSITIONS,
)

from app.orders.models import (
    OrderHistory,
    OrderItem,
    SwiggyOrders,
)

from app.orders.order_item_service import (
    get_order_items,
)

from app.orders.service import (
    validate_status_transition,
)

from app.orders.validation import (
    validate_positive_id,
)


PLATFORM = "swiggy"


def _order_item_stats_subquery(
    db: Session,
):

    return (
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


def get_merchant_orders(
    db: Session,
    restaurant_id: int,
    *,
    status: str | None = None,
):

    restaurant_id = (
        validate_positive_id(
            restaurant_id,
            "Restaurant ID",
        )
    )


    item_stats = (
        _order_item_stats_subquery(
            db
        )
    )


    query = (

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
    )


    if status:

        status = (
            status
            .strip()
            .lower()
        )

        if status not in ORDER_STATUSES:

            raise ValueError(
                "Invalid order status."
            )

        query = query.filter(
            SwiggyOrders.status
            ==
            status
        )


    rows = (

        query

        .order_by(
            item_stats.c.created_at.desc(),

            SwiggyOrders.order_date.desc(),

            SwiggyOrders.id.desc(),
        )

        .all()
    )


    orders = []


    for (
        order,
        created_at,
        item_count,
    ) in rows:

        order.sort_created_at = (
            created_at
        )

        order.item_count = int(
            item_count
            or
            0
        )

        orders.append(
            order
        )


    return orders


def get_merchant_order(
    db: Session,
    restaurant_id: int,
    order_id: int,
):

    restaurant_id = (
        validate_positive_id(
            restaurant_id,
            "Restaurant ID",
        )
    )

    order_id = (
        validate_positive_id(
            order_id,
            "Order ID",
        )
    )


    order = (

        db.query(
            SwiggyOrders
        )

        .filter(

            SwiggyOrders.id
            ==
            order_id,

            SwiggyOrders.restaurant_id
            ==
            restaurant_id,
        )

        .first()
    )


    if order is None:

        return None


    items = get_order_items(

        db=db,

        platform=PLATFORM,

        order_id=order.id,
    )


    created_times = [

        item.created_at

        for item in items

        if item.created_at
    ]


    order.sort_created_at = (

        min(
            created_times
        )

        if created_times

        else None
    )


    order.item_count = sum(

        int(
            item.quantity
        )

        for item in items
    )


    return (
        order,
        items,
    )


def get_merchant_order_summary(
    db: Session,
    restaurant_id: int,
):

    restaurant_id = (
        validate_positive_id(
            restaurant_id,
            "Restaurant ID",
        )
    )


    orders = (

        db.query(
            SwiggyOrders
        )

        .filter(
            SwiggyOrders.restaurant_id
            ==
            restaurant_id
        )

        .all()
    )


    completed_revenue = Decimal(
        "0.00"
    )


    summary = {

        "total":
            len(
                orders
            ),

        "pending":
            0,

        "processing":
            0,

        "completed":
            0,

        "cancelled":
            0,

        "completed_revenue":
            Decimal(
                "0.00"
            ),
    }


    for order in orders:

        status = (
            order.status
            or
            ""
        ).strip().lower()


        if status in {
            "pending",
            "processing",
            "completed",
            "cancelled",
        }:

            summary[
                status
            ] += 1


        if status == "completed":

            completed_revenue += Decimal(
                str(
                    order.amount
                )
            )


    summary[
        "completed_revenue"
    ] = completed_revenue.quantize(
        Decimal(
            "0.01"
        )
    )


    return summary


def get_allowed_merchant_statuses(
    current_status: str,
):

    current_status = (
        current_status
        or
        ""
    ).strip().lower()


    allowed = (

        ORDER_STATUS_TRANSITIONS.get(
            current_status,
            set(),
        )
    )


    status_order = [
        "pending",
        "processing",
        "completed",
        "cancelled",
    ]


    return [

        status

        for status
        in status_order

        if status
        in allowed
    ]


def update_merchant_order_status(
    db: Session,
    restaurant_id: int,
    order_id: int,
    *,
    new_status: str,
    changed_by: int,
):

    restaurant_id = (
        validate_positive_id(
            restaurant_id,
            "Restaurant ID",
        )
    )


    order_id = (
        validate_positive_id(
            order_id,
            "Order ID",
        )
    )


    changed_by = (
        validate_positive_id(
            changed_by,
            "Merchant User ID",
        )
    )


    new_status = (
        new_status
        or
        ""
    ).strip().lower()


    if new_status not in ORDER_STATUSES:

        raise ValueError(
            "Invalid order status."
        )


    try:

        order = (

            db.query(
                SwiggyOrders
            )

            .filter(

                SwiggyOrders.id
                ==
                order_id,

                SwiggyOrders.restaurant_id
                ==
                restaurant_id,
            )

            .with_for_update()

            .first()
        )


        if order is None:

            return None


        old_status = (
            order.status
        )


        validated_status = (
            validate_status_transition(
                old_status,
                new_status,
            )
        )


        if (
            validated_status
            ==
            old_status
        ):

            return order


        order.status = (
            validated_status
        )


        history = OrderHistory(

            platform=PLATFORM,

            order_id=order.id,

            action="update",

            field_name="status",

            old_value=str(
                old_status
            ),

            new_value=str(
                validated_status
            ),

            changed_by=changed_by,
        )


        db.add(
            history
        )


        db.commit()


        db.refresh(
            order
        )


        return order


    except ValueError:

        db.rollback()

        raise


    except Exception:

        db.rollback()

        raise