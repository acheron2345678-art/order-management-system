from datetime import date

from app.core.config import (
    ORDER_STATUS_TRANSITIONS,
)

from app.orders import repository

from app.orders.validation import (
    clean_required_text,
    parse_required_date,
    validate_order_number,
    validate_positive_id,
    validate_positive_money,
    validate_status,
)


def validate_status_transition(
    current_status: str,
    new_status: str,
):
    current_status = validate_status(
        current_status
    )

    new_status = validate_status(
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


def parse_order_date(
    value,
):
    if value in (
        None,
        "",
    ):
        return None

    return parse_required_date(
        value,
        "Order date",
    )


def validate_order_form_fields(
    customer_name,
    order_number,
    order_date,
):
    cleaned_customer_name = (
        clean_required_text(
            customer_name,
            "Customer name",
            max_length=100,
        )
    )

    cleaned_order_number = (
        validate_order_number(
            order_number
        )
    )

    parsed_order_date = (
        parse_required_date(
            order_date,
            "Order date",
        )
    )

    return (
        cleaned_customer_name,
        cleaned_order_number,
        parsed_order_date,
    )


def get_order(
    db,
    model,
    order_id: int,
    client_id: int | None = None,
):
    order_id = validate_positive_id(
        order_id,
        "Order ID",
    )

    if client_id is not None:
        client_id = (
            validate_positive_id(
                client_id,
                "Client ID",
            )
        )

    return repository.get_order_by_id(
        db,
        model,
        order_id,
        client_id=client_id,
    )


def get_orders(
    db,
    model,
    status=None,
    order_date=None,
    client_id: int | None = None,
):
    parsed_date = parse_order_date(
        order_date
    )

    normalized_status = None

    if status:
        normalized_status = (
            validate_status(
                status
            )
        )

    if client_id is not None:
        client_id = (
            validate_positive_id(
                client_id,
                "Client ID",
            )
        )

    orders = repository.get_orders(
        db,
        model,
        normalized_status,
        parsed_date,
        client_id=client_id,
    )

    return (
        orders,
        len(orders),
    )


def get_all_orders(
    db,
    model,
    client_id: int | None = None,
):
    if client_id is not None:
        client_id = (
            validate_positive_id(
                client_id,
                "Client ID",
            )
        )

    return repository.get_all_orders(
        db,
        model,
        client_id=client_id,
    )


def create_order(
    db,
    model,
    customer_name,
    order_number,
    amount,
    status,
    order_date,
    client_id: int,
):
    (
        cleaned_customer_name,
        cleaned_order_number,
        parsed_order_date,
    ) = validate_order_form_fields(
        customer_name,
        order_number,
        order_date,
    )

    if repository.order_number_exists(
        db,
        model,
        cleaned_order_number,
    ):
        raise ValueError(
            "Order number already exists."
        )

    amount = validate_positive_money(
        amount,
        "Amount",
    )

    client_id = validate_positive_id(
        client_id,
        "Client ID",
    )

    order_data = {
        "customer_name":
            cleaned_customer_name,

        "order_number":
            cleaned_order_number,

        "amount":
            float(amount),

        "status":
            validate_status(
                status
            ),

        "order_date":
            parsed_order_date,

        "client_id":
            client_id,
    }

    return repository.create_order(
        db,
        model,
        order_data,
    )


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
    (
        cleaned_customer_name,
        cleaned_order_number,
        parsed_order_date,
    ) = validate_order_form_fields(
        customer_name,
        order_number,
        order_date,
    )

    if repository.order_number_exists(
        db,
        type(order),
        cleaned_order_number,
        exclude_order_id=order.id,
    ):
        raise ValueError(
            "Order number already exists."
        )

    amount = validate_positive_money(
        amount,
        "Amount",
    )

    client_id = validate_positive_id(
        client_id,
        "Client ID",
    )

    order_data = {
        "customer_name":
            cleaned_customer_name,

        "order_number":
            cleaned_order_number,

        "amount":
            float(amount),

        "status":
            validate_status_transition(
                order.status,
                status,
            ),

        "order_date":
            parsed_order_date,

        "client_id":
            client_id,
    }

    return repository.update_order(
        db,
        order,
        order_data,
    )


def delete_order(
    db,
    order,
):
    repository.delete_order(
        db,
        order,
    )