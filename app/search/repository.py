from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.users.models import User


def get_all(
    db: Session,
    model,
    client_id: int | None = None,
):
    query = (
        db.query(model)
        .outerjoin(
            User,
            model.client_id == User.id
        )
    )

    if client_id is not None:
        query = query.filter(
            model.client_id == client_id
        )

    return (
        query
        .order_by(model.id.asc())
        .all()
    )


def search(
    db: Session,
    model,
    search_query: str,
    client_id: int | None = None,
):
    search_term = f"%{search_query}%"

    filters = [
        model.customer_name.ilike(
            search_term
        ),

        model.order_number.ilike(
            search_term
        ),

        model.status.ilike(
            search_term
        ),

        model.product_name.ilike(
            search_term
        ),

        User.username.ilike(
            search_term
        ),

        User.email.ilike(
            search_term
        ),
    ]


    if search_query.isdigit():

        filters.append(
            model.id == int(
                search_query
            )
        )


    try:

        filters.append(
            model.order_date
            ==
            date.fromisoformat(
                search_query
            )
        )

    except ValueError:
        pass


    try:

        filters.append(
            model.amount
            ==
            float(search_query)
        )

    except ValueError:
        pass


    query = (
        db.query(model)
        .outerjoin(
            User,
            model.client_id == User.id
        )
        .filter(
            or_(*filters)
        )
    )


    if client_id is not None:

        query = query.filter(
            model.client_id == client_id
        )


    return (
        query
        .order_by(model.id.asc())
        .all()
    )