from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from sqlalchemy.orm import Session

from app.orders.models import (
    OrderItem,
)

from app.orders.validation import (
    clean_required_text,
    validate_platform,
    validate_positive_id,
    validate_positive_money,
    validate_positive_quantity,
)


MONEY_PLACES = Decimal(
    "0.01"
)


def normalize_platform(
    platform: str,
):
    return validate_platform(
        platform
    )


def normalize_price(
    value,
):
    return validate_positive_money(
        value,
        "Unit price",
    )


def create_order_item(
    db: Session,
    platform: str,
    order_id: int,
    product_id: int,
    product_name: str,
    unit_price,
    quantity: int,
):
    platform = normalize_platform(
        platform
    )

    order_id = validate_positive_id(
        order_id,
        "Order ID",
    )

    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    quantity = (
        validate_positive_quantity(
            quantity
        )
    )

    product_name = clean_required_text(
        product_name,
        "Product name",
        max_length=255,
    )

    price = normalize_price(
        unit_price
    )

    line_total = (
        price
        *
        quantity
    ).quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )

    if line_total <= 0:
        raise ValueError(
            "Line total must be greater than zero."
        )

    item = OrderItem(
        platform=platform,
        order_id=order_id,
        product_id=product_id,
        product_name=product_name,
        unit_price=price,
        quantity=quantity,
        line_total=line_total,
    )

    db.add(
        item
    )

    db.flush()

    return item


def get_order_items(
    db: Session,
    platform: str,
    order_id: int,
):
    platform = normalize_platform(
        platform
    )

    order_id = validate_positive_id(
        order_id,
        "Order ID",
    )

    return (
        db.query(
            OrderItem
        )
        .filter(
            OrderItem.platform
            ==
            platform,

            OrderItem.order_id
            ==
            order_id,
        )
        .order_by(
            OrderItem.id.asc()
        )
        .all()
    )


def calculate_order_total(
    db: Session,
    platform: str,
    order_id: int,
):
    items = get_order_items(
        db=db,
        platform=platform,
        order_id=order_id,
    )

    total = Decimal(
        "0.00"
    )

    for item in items:
        total += Decimal(
            str(
                item.line_total
            )
        )

    return total.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def delete_order_items(
    db: Session,
    platform: str,
    order_id: int,
):
    platform = normalize_platform(
        platform
    )

    order_id = validate_positive_id(
        order_id,
        "Order ID",
    )

    deleted_count = (
        db.query(
            OrderItem
        )
        .filter(
            OrderItem.platform
            ==
            platform,

            OrderItem.order_id
            ==
            order_id,
        )
        .delete(
            synchronize_session=False
        )
    )

    db.flush()

    return deleted_count


def replace_order_items(
    db: Session,
    platform: str,
    order_id: int,
    items: list[dict],
):
    if not items:
        raise ValueError(
            "An order must contain "
            "at least one product"
        )

    platform = normalize_platform(
        platform
    )

    order_id = validate_positive_id(
        order_id,
        "Order ID",
    )

    delete_order_items(
        db=db,
        platform=platform,
        order_id=order_id,
    )

    created_items = []

    for item_data in items:
        item = create_order_item(
            db=db,

            platform=platform,

            order_id=order_id,

            product_id=item_data[
                "product_id"
            ],

            product_name=item_data[
                "product_name"
            ],

            unit_price=item_data[
                "unit_price"
            ],

            quantity=item_data[
                "quantity"
            ],
        )

        created_items.append(
            item
        )

    total = Decimal(
        "0.00"
    )

    for item in created_items:
        total += Decimal(
            str(
                item.line_total
            )
        )

    total = total.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )

    if total <= 0:
        raise ValueError(
            "Order total must be greater than zero."
        )

    return (
        created_items,
        total,
    )