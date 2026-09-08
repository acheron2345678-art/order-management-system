from sqlalchemy import (
    case,
    func,
)

from sqlalchemy.orm import Session


def get_summary(
    db: Session,
    model,
    client_id: int | None = None,
):
    query = db.query(
        func.count(
            model.id
        ).label(
            "total"
        ),

        func.sum(
            case(
                (
                    model.status == "pending",
                    1,
                ),
                else_=0,
            )
        ).label(
            "pending"
        ),

        func.sum(
            case(
                (
                    model.status == "processing",
                    1,
                ),
                else_=0,
            )
        ).label(
            "processing"
        ),

        func.sum(
            case(
                (
                    model.status == "completed",
                    1,
                ),
                else_=0,
            )
        ).label(
            "completed"
        ),

        func.sum(
            case(
                (
                    model.status == "cancelled",
                    1,
                ),
                else_=0,
            )
        ).label(
            "cancelled"
        ),

        func.sum(
            case(
                (
                    model.status == "completed",
                    model.amount,
                ),
                else_=0,
            )
        ).label(
            "amount"
        ),
    )


    if client_id is not None:

        query = query.filter(
            model.client_id == client_id
        )


    row = query.one()


    return {
        "total": int(
            row.total or 0
        ),

        "pending": int(
            row.pending or 0
        ),

        "processing": int(
            row.processing or 0
        ),

        "completed": int(
            row.completed or 0
        ),

        "cancelled": int(
            row.cancelled or 0
        ),

        "amount": float(
            row.amount or 0
        ),
    }


def get_daily_metrics(
    db: Session,
    model,
    client_id: int | None = None,
):
    query = db.query(

        model.order_date.label(
            "order_date"
        ),

        func.count(
            model.id
        ).label(
            "total"
        ),

        func.sum(
            case(
                (
                    model.status == "pending",
                    1,
                ),
                else_=0,
            )
        ).label(
            "pending"
        ),

        func.sum(
            case(
                (
                    model.status == "processing",
                    1,
                ),
                else_=0,
            )
        ).label(
            "processing"
        ),

        func.sum(
            case(
                (
                    model.status == "completed",
                    1,
                ),
                else_=0,
            )
        ).label(
            "completed"
        ),

        func.sum(
            case(
                (
                    model.status == "cancelled",
                    1,
                ),
                else_=0,
            )
        ).label(
            "cancelled"
        ),

        func.sum(
            case(
                (
                    model.status == "completed",
                    model.amount,
                ),
                else_=0,
            )
        ).label(
            "amount"
        ),
    )


    if client_id is not None:

        query = query.filter(
            model.client_id == client_id
        )


    rows = (
        query
        .group_by(
            model.order_date
        )
        .order_by(
            model.order_date.asc()
        )
        .all()
    )


    return [
        {
            "date":
                row.order_date.isoformat(),

            "total":
                int(row.total or 0),

            "pending":
                int(row.pending or 0),

            "processing":
                int(row.processing or 0),

            "completed":
                int(row.completed or 0),

            "cancelled":
                int(row.cancelled or 0),

            "amount":
                float(row.amount or 0),
        }

        for row in rows

        if row.order_date is not None
    ]


def get_product_performance(
    db: Session,
    model,
    client_id: int | None = None,
):
    query = (
        db.query(

            model.product_name.label(
                "product_name"
            ),

            func.count(
                model.id
            ).label(
                "orders"
            ),

            func.sum(
                model.amount
            ).label(
                "revenue"
            ),
        )

        .filter(
            model.status == "completed",
            model.product_name.isnot(None),
            model.product_name != "",
        )
    )


    if client_id is not None:

        query = query.filter(
            model.client_id == client_id
        )


    rows = (
        query
        .group_by(
            model.product_name
        )
        .all()
    )


    return [
        {
            "product_name":
                row.product_name,

            "orders":
                int(row.orders or 0),

            "revenue":
                float(row.revenue or 0),
        }

        for row in rows
    ]


def get_drilldown_orders(
    db: Session,
    model,
    order_date,
    metric: str,
    client_id: int | None = None,
):
    query = (
        db.query(model)
        .filter(
            model.order_date == order_date
        )
    )


    if client_id is not None:

        query = query.filter(
            model.client_id == client_id
        )


    if metric in {
        "pending",
        "processing",
        "completed",
        "cancelled",
    }:

        query = query.filter(
            model.status == metric
        )


    elif metric == "amount":

        query = query.filter(
            model.status == "completed"
        )


    return (
        query
        .order_by(
            model.id.asc()
        )
        .all()
    )

def get_product_order_counts(db:Session,model):
    rows=db.query(model.product_id.label("product_id"),model.product_name.label("product_name"),func.count(model.id).label("orders")).filter(model.product_name.isnot(None),model.product_name!="",model.product_id.isnot(None)).group_by(model.product_id,model.product_name).all()

    return [
        {
            "product_id":row.product_id,
            "product_name":row.product_name,
            "orders":int(row.orders or 0)
        }
        for row in rows
    ]