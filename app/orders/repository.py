from sqlalchemy.orm import Session


def get_order_by_id(
    db: Session,
    model,
    order_id: int,
    client_id: int | None = None,
):
    query = db.query(
        model
    ).filter(
        model.id == order_id
    )

    if client_id is not None:
        query = query.filter(
            model.client_id == client_id
        )

    return query.first()


def get_orders(
    db: Session,
    model,
    status=None,
    order_date=None,
    client_id: int | None = None,
):
    query = db.query(
        model
    )

    if client_id is not None:
        query = query.filter(
            model.client_id == client_id
        )

    if status:
        query = query.filter(
            model.status == status
        )

    if order_date:
        query = query.filter(
            model.order_date == order_date
        )

    return query.order_by(
        model.id.asc()
    ).all()


def get_all_orders(
    db: Session,
    model,
    client_id: int | None = None,
):
    query = db.query(
        model
    )

    if client_id is not None:
        query = query.filter(
            model.client_id == client_id
        )

    return query.order_by(
        model.id.asc()
    ).all()


def order_number_exists(
    db: Session,
    model,
    order_number: str,
    *,
    exclude_order_id: int | None = None,
) -> bool:
    query = db.query(
        model
    ).filter(
        model.order_number == order_number
    )

    if exclude_order_id is not None:
        query = query.filter(
            model.id != exclude_order_id
        )

    return (
        query.first()
        is not None
    )


def create_order(
    db: Session,
    model,
    order_data: dict,
):
    order = model(
        **order_data
    )

    db.add(
        order
    )

    db.commit()

    db.refresh(
        order
    )

    return order


def update_order(
    db: Session,
    order,
    order_data: dict,
):
    for field, value in (
        order_data.items()
    ):
        setattr(
            order,
            field,
            value,
        )

    db.commit()

    db.refresh(
        order
    )

    return order


def delete_order(
    db: Session,
    order,
):
    db.delete(
        order
    )

    db.commit()