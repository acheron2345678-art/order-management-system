from datetime import date

from sqlalchemy import func

from app.dashboard import repository
from app.orders.models import OrderItem


TREND_POINT_LIMIT = 14


VALID_DRILLDOWN_PLATFORMS = {
    "swiggy",
    "insights",
    "combined",
}


VALID_DRILLDOWN_METRICS = {
    "total",
    "pending",
    "processing",
    "completed",
    "cancelled",
    "amount",
}


METRIC_LABELS = {
    "total": "Orders",
    "pending": "Pending",
    "processing": "Processing",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "amount": "Revenue",
}


def get_dashboard_data(
    db,
    model,
    client_id=None,
):
    summary = repository.get_summary(
        db,
        model,
        client_id=client_id,
    )

    summary["trend"] = (
        repository.get_daily_metrics(
            db,
            model,
            client_id=client_id,
        )
    )

    return summary


def _align_trends(
    swiggy_trend,
    insights_trend,
):
    swiggy_by_date = {
        item["date"]: item
        for item in swiggy_trend
    }

    insights_by_date = {
        item["date"]: item
        for item in insights_trend
    }

    dates = sorted(
        set(swiggy_by_date)
        |
        set(insights_by_date)
    )

    if (
        len(dates)
        >
        TREND_POINT_LIMIT
    ):
        dates = dates[
            -TREND_POINT_LIMIT:
        ]

    empty_values = {
        "total": 0,
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "cancelled": 0,
        "amount": 0.0,
    }

    def build(
        source,
    ):
        aligned = []

        for current_date in dates:

            values = source.get(
                current_date,
                empty_values,
            )

            aligned.append(
                {
                    "date":
                        current_date,

                    "total":
                        int(
                            values.get(
                                "total",
                                0,
                            )
                        ),

                    "pending":
                        int(
                            values.get(
                                "pending",
                                0,
                            )
                        ),

                    "processing":
                        int(
                            values.get(
                                "processing",
                                0,
                            )
                        ),

                    "completed":
                        int(
                            values.get(
                                "completed",
                                0,
                            )
                        ),

                    "cancelled":
                        int(
                            values.get(
                                "cancelled",
                                0,
                            )
                        ),

                    "amount":
                        round(
                            float(
                                values.get(
                                    "amount",
                                    0,
                                )
                            ),
                            2,
                        ),
                }
            )

        return aligned

    return (
        build(
            swiggy_by_date
        ),
        build(
            insights_by_date
        ),
    )


def _get_product_performance_from_items(
    db,
    model,
    platform,
    client_id=None,
):
    query = (
        db.query(
            OrderItem.product_id,
            OrderItem.product_name,

            func.sum(
                OrderItem.quantity
            ).label(
                "quantity"
            ),

            func.sum(
                OrderItem.line_total
            ).label(
                "revenue"
            ),

            func.count(
                func.distinct(
                    OrderItem.order_id
                )
            ).label(
                "orders"
            ),
        )
        .join(
            model,
            model.id
            ==
            OrderItem.order_id,
        )
        .filter(
            OrderItem.platform
            ==
            platform,

            model.status
            ==
            "completed",
        )
    )

    if client_id is not None:

        query = query.filter(
            model.client_id
            ==
            client_id
        )

    rows = (
        query
        .group_by(
            OrderItem.product_id,
            OrderItem.product_name,
        )
        .all()
    )

    return [
        {
            "product_id":
                row.product_id,

            "product_name":
                row.product_name,

            "quantity":
                int(
                    row.quantity
                    or 0
                ),

            "orders":
                int(
                    row.orders
                    or 0
                ),

            "revenue":
                round(
                    float(
                        row.revenue
                        or 0
                    ),
                    2,
                ),
        }

        for row in rows
    ]


def _combine_products(
    swiggy_products,
    insights_products,
):
    combined = {}

    for item in [
        *swiggy_products,
        *insights_products,
    ]:

        product_id = item.get(
            "product_id"
        )

        product_name = (
            item.get(
                "product_name"
            )
            or
            "Unknown Product"
        ).strip()

        if product_id is not None:

            key = (
                "product",
                product_id,
            )

        else:

            key = (
                "name",
                product_name.casefold(),
            )

        if key not in combined:

            combined[key] = {
                "product_id":
                    product_id,

                "product_name":
                    product_name,

                "quantity":
                    0,

                "orders":
                    0,

                "revenue":
                    0.0,
            }

        combined[
            key
        ][
            "quantity"
        ] += int(
            item.get(
                "quantity",
                0,
            )
        )

        combined[
            key
        ][
            "orders"
        ] += int(
            item.get(
                "orders",
                0,
            )
        )

        combined[
            key
        ][
            "revenue"
        ] += float(
            item.get(
                "revenue",
                0,
            )
        )

    products = []

    for values in combined.values():

        values[
            "revenue"
        ] = round(
            values[
                "revenue"
            ],
            2,
        )

        products.append(
            values
        )

    products.sort(
        key=lambda item: (
            item[
                "quantity"
            ],
            item[
                "revenue"
            ],
            item[
                "orders"
            ],
        ),
        reverse=True,
    )

    return products


def _build_top_items(
    swiggy_products,
    insights_products,
    limit=5,
):
    items = []

    for item in swiggy_products:

        items.append(
            {
                **item,
                "platform":
                    "swiggy",
            }
        )

    for item in insights_products:

        items.append(
            {
                **item,
                "platform":
                    "insights",
            }
        )

    items.sort(
        key=lambda item: (
            item.get(
                "orders",
                0,
            ),
            item.get(
                "quantity",
                0,
            ),
            item.get(
                "revenue",
                0,
            ),
        ),
        reverse=True,
    )

    return items[
        :limit
    ]


def build_dashboard_context(
    db,
    swiggy_model,
    insights_model,
    client_id=None,
):
    swiggy = (
        get_dashboard_data(
            db,
            swiggy_model,
            client_id=client_id,
        )
    )

    insights = (
        get_dashboard_data(
            db,
            insights_model,
            client_id=client_id,
        )
    )

    (
        swiggy["trend"],
        insights["trend"],
    ) = _align_trends(
        swiggy["trend"],
        insights["trend"],
    )

    total_orders = (
        swiggy["total"]
        +
        insights["total"]
    )

    total_amount = (
        swiggy["amount"]
        +
        insights["amount"]
    )

    completed_orders = (
        swiggy["completed"]
        +
        insights["completed"]
    )

    completion_rate = (
        round(
            (
                completed_orders
                /
                total_orders
            )
            *
            100,
            1,
        )

        if total_orders

        else 0.0
    )

    average_order_value = (
        round(
            total_amount
            /
            completed_orders,
            2,
        )

        if completed_orders

        else 0.0
    )

    combined = {
        "total":
            total_orders,

        "pending":
            swiggy["pending"]
            +
            insights["pending"],

        "processing":
            swiggy["processing"]
            +
            insights["processing"],

        "completed":
            completed_orders,

        "cancelled":
            swiggy["cancelled"]
            +
            insights["cancelled"],

        "amount":
            round(
                total_amount,
                2,
            ),

        "average_order_value":
            average_order_value,
    }

    summary = {
        "total_orders":
            total_orders,

        "revenue":
            round(
                total_amount,
                2,
            ),

        "completion_rate":
            completion_rate,

        "average_order_value":
            average_order_value,
    }

    swiggy_products = (
        _get_product_performance_from_items(
            db,
            swiggy_model,
            "swiggy",
            client_id=client_id,
        )
    )

    insights_products = (
        _get_product_performance_from_items(
            db,
            insights_model,
            "insights",
            client_id=client_id,
        )
    )

    products = (
        _combine_products(
            swiggy_products,
            insights_products,
        )
    )

    top_selling_products = (
        _build_top_items(
            swiggy_products,
            insights_products,
            limit=5,
        )
    )

    return {
        "swiggy":
            swiggy,

        "insights":
            insights,

        "combined":
            combined,

        "summary":
            summary,

        "products":
            products,

        "top_selling_products":
            top_selling_products,

        "total_orders":
            total_orders,

        "total_amount":
            round(
                total_amount,
                2,
            ),
    }


def _normalize_drilldown_metric(
    metric: str,
):
    normalized = (
        metric
        .strip()
        .lower()
    )

    if normalized == "revenue":

        normalized = "amount"

    if (
        normalized
        not in
        VALID_DRILLDOWN_METRICS
    ):
        raise ValueError(
            "Invalid dashboard metric"
        )

    return normalized


def _normalize_drilldown_platform(
    platform: str,
):
    normalized = (
        platform
        .strip()
        .lower()
    )

    if normalized in {
        "all",
        "all-platforms",
        "all_platforms",
    }:

        normalized = "combined"

    if (
        normalized
        not in
        VALID_DRILLDOWN_PLATFORMS
    ):
        raise ValueError(
            "Invalid dashboard platform"
        )

    return normalized


def _parse_drilldown_date(
    date_value: str,
):
    try:

        return date.fromisoformat(
            date_value
        )

    except ValueError as exc:

        raise ValueError(
            "Invalid dashboard date"
        ) from exc


def _format_drilldown_order(
    order,
    platform_name: str,
):
    return {
        "platform":
            platform_name,

        "id":
            order.id,

        "customer_name":
            order.customer_name,

        "order_number":
            order.order_number,

        "product_name":
            order.product_name,

        "amount":
            round(
                float(
                    order.amount
                    or 0
                ),
                2,
            ),

        "status":
            order.status,

        "order_date":
            order.order_date.isoformat(),
    }


def get_dashboard_drilldown(
    db,
    swiggy_model,
    insights_model,
    platform: str,
    metric: str,
    date_value: str,
    client_id=None,
):
    platform_key = (
        _normalize_drilldown_platform(
            platform
        )
    )

    metric_key = (
        _normalize_drilldown_metric(
            metric
        )
    )

    selected_date = (
        _parse_drilldown_date(
            date_value
        )
    )

    orders = []

    if platform_key in {
        "swiggy",
        "combined",
    }:

        swiggy_orders = (
            repository
            .get_drilldown_orders(
                db,
                swiggy_model,
                selected_date,
                metric_key,
                client_id=client_id,
            )
        )

        orders.extend(
            _format_drilldown_order(
                order,
                "Swiggy",
            )

            for order
            in swiggy_orders
        )

    if platform_key in {
        "insights",
        "combined",
    }:

        insights_orders = (
            repository
            .get_drilldown_orders(
                db,
                insights_model,
                selected_date,
                metric_key,
                client_id=client_id,
            )
        )

        orders.extend(
            _format_drilldown_order(
                order,
                "Insights",
            )

            for order
            in insights_orders
        )

    orders.sort(
        key=lambda item: (
            item[
                "platform"
            ],
            item[
                "id"
            ],
        )
    )

    if platform_key == "swiggy":

        platform_label = (
            "Swiggy"
        )

    elif platform_key == "insights":

        platform_label = (
            "Insights"
        )

    else:

        platform_label = (
            "All Platforms"
        )

    return {
        "platform":
            platform_label,

        "metric":
            metric_key,

        "metric_label":
            METRIC_LABELS[
                metric_key
            ],

        "date":
            selected_date.isoformat(),

        "order_count":
            len(
                orders
            ),

        "total_amount":
            round(
                sum(
                    item[
                        "amount"
                    ]

                    for item
                    in orders
                ),
                2,
            ),

        "orders":
            orders,
    }


def get_global_top_selling_products(
    db,
    swiggy_model,
    insights_model,
    limit=5,
    client_id=None,
):
    swiggy_products = (
        _get_product_performance_from_items(
            db,
            swiggy_model,
            "swiggy",
            client_id=client_id,
        )
    )

    insights_products = (
        _get_product_performance_from_items(
            db,
            insights_model,
            "insights",
            client_id=client_id,
        )
    )

    return _build_top_items(
        swiggy_products,
        insights_products,
        limit=limit,
    )