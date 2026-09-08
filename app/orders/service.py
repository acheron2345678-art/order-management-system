from datetime import date

from app.core.config import ORDER_STATUSES,ORDER_STATUS_TRANSITIONS
from app.orders import repository

def validate_status_transition(
    current_status: str,
    new_status: str,
):
    validate_status(
        current_status
    )

    validate_status(
        new_status
    )

    if current_status == new_status:
        return new_status

    allowed_statuses = (
        ORDER_STATUS_TRANSITIONS.get(
            current_status,
            set(),
        )
    )

    if new_status not in allowed_statuses:
        raise ValueError(
            f"Cannot change order status "
            f"from '{current_status}' "
            f"to '{new_status}'"
        )

    return new_status

def parse_order_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def validate_status(status: str):
    if status not in ORDER_STATUSES:
        raise ValueError("Invalid order status")
    return status


def get_order(db, model, order_id: int,client_id:int |None=None):
    return repository.get_order_by_id(db, model, order_id,client_id=client_id)


def get_orders(db, model, status=None, order_date=None,client_id:int |None=None):
    parsed_date = parse_order_date(order_date)
    orders = repository.get_orders(db, model, status, parsed_date,client_id=client_id)
    return orders, len(orders)


def get_all_orders(db, model,client_id:int |None=None):
    return repository.get_all_orders(db, model,client_id=client_id)


def create_order(
    db,
    model,
    customer_name,
    order_number,
    amount,
    status,
    order_date,
    client_id:int
):
    order_data = {
        "customer_name": customer_name.strip(),
        "order_number": order_number.strip(),
        "amount": float(amount),
        "status": validate_status(status),
        "order_date": parse_order_date(order_date),
        "client_id":client_id
    }
    return repository.create_order(db, model, order_data)


def update_order(
    db,
    order,
    customer_name,
    order_number,
    amount,
    status,
    order_date,
    client_id: int,
):
    order_data = {
        "customer_name": customer_name.strip(),
        "order_number": order_number.strip(),
        "amount": float(amount),
        "status": validate_status_transition(
            order.status,
            status,
        ),
        "order_date": parse_order_date(
            order_date
        ),
        "client_id": client_id,
    }

    return repository.update_order(
        db,
        order,
        order_data,
    )


def delete_order(db, order):
    repository.delete_order(db, order)
