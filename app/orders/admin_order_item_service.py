from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session
from app.orders.models import SwiggyOrders,InsightsOrders
from app.products.models import Product
from app.orders.order_item_service import (
    get_order_items,create_order_item
)


MONEY_PLACES = Decimal("0.01")


def normalize_money(
    value,
):
    return (
        Decimal(str(value))
        .quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )
    )


def prepare_admin_order_items(
    db: Session,
    platform: str,
    product_ids: list[int],
    quantities: list[int],
):
    platform = (
        platform
        .strip()
        .lower()
    )

    if platform not in {
        "swiggy",
        "insights",
    }:
        raise ValueError(
            "Invalid platform"
        )

    if (
        len(product_ids)
        != len(quantities)
    ):
        raise ValueError(
            "Invalid product data"
        )

    if not product_ids:
        raise ValueError(
            "Select at least one product"
        )

    requested = {}

    for product_id, quantity in zip(
        product_ids,
        quantities,
    ):
        try:

            product_id = int(
                product_id
            )

            quantity = int(
                quantity
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Invalid product or quantity"
            )

        if product_id <= 0:
            raise ValueError(
                "Invalid product"
            )

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than 0"
            )

        requested[
            product_id
        ] = (
            requested.get(
                product_id,
                0,
            )
            + quantity
        )

    product_ids_to_load = sorted(
        requested.keys()
    )

    products = (
        db.query(Product)
        .filter(
            Product.id.in_(
                product_ids_to_load
            )
        )
        .order_by(
            Product.id.asc()
        )
        .all()
    )

    if (
        len(products)
        != len(product_ids_to_load)
    ):
        raise ValueError(
            "One or more products were not found"
        )

    items = []

    total = Decimal(
        "0.00"
    )

    for product in products:

        product_platform = (
            product.platform
            .strip()
            .lower()
        )

        if (
            product_platform
            != platform
        ):
            raise ValueError(
                f"{product.product_name} "
                "does not belong to this platform"
            )

        if not product.is_active:
            raise ValueError(
                f"{product.product_name} "
                "is currently unavailable"
            )

        quantity = requested[
            product.id
        ]

        if (
            quantity
            > product.stock_quantity
        ):
            raise ValueError(
                f"Only "
                f"{product.stock_quantity} "
                f"units of "
                f"{product.product_name} "
                "are available"
            )

        unit_price = normalize_money(
            product.price
        )

        line_total = (
            unit_price
            * quantity
        ).quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        items.append(
            {
                "product": product,
                "product_id": product.id,
                "product_name": (
                    product.product_name
                ),
                "unit_price": unit_price,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

        total += line_total

    total = total.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )

    return items, total


def get_admin_order_items(
    db: Session,
    platform: str,
    order_id: int,
):
    items = get_order_items(
        db=db,
        platform=platform,
        order_id=order_id,
    )

    result = []

    total = Decimal(
        "0.00"
    )

    for item in items:

        line_total = normalize_money(
            item.line_total
        )

        result.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "unit_price": normalize_money(
                    item.unit_price
                ),
                "quantity": item.quantity,
                "line_total": line_total,
            }
        )

        total += line_total

    return (
        result,
        total.quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        ),
    )

def create_admin_multi_product_order(
    db: Session,
    platform: str,
    customer_name: str,
    order_number: str,
    client_id: int,
    order_date,
    product_ids: list[int],
    quantities: list[int],
):
    platform = (
        platform
        .strip()
        .lower()
    )

    customer_name = (
        customer_name.strip()
    )

    order_number = (
        order_number.strip()
    )

    if not customer_name:
        raise ValueError(
            "Customer name is required"
        )

    if not order_number:
        raise ValueError(
            "Order number is required"
        )

    if platform == "swiggy":
        model = SwiggyOrders

    elif platform == "insights":
        model = InsightsOrders

    else:
        raise ValueError(
            "Invalid platform"
        )

    if (
        len(product_ids)
        != len(quantities)
    ):
        raise ValueError(
            "Invalid product data"
        )

    if not product_ids:
        raise ValueError(
            "Select at least one product"
        )

    requested = {}

    for product_id, quantity in zip(
        product_ids,
        quantities,
    ):
        product_id = int(
            product_id
        )

        quantity = int(
            quantity
        )

        if product_id <= 0:
            raise ValueError(
                "Invalid product"
            )

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than 0"
            )

        requested[
            product_id
        ] = (
            requested.get(
                product_id,
                0,
            )
            + quantity
        )

    try:

        existing_order = (
            db.query(model)
            .filter(
                model.order_number
                == order_number
            )
            .first()
        )

        if existing_order:
            raise ValueError(
                "Order number already exists"
            )

        product_ids_to_load = sorted(
            requested.keys()
        )

        products = (
            db.query(Product)
            .filter(
                Product.id.in_(
                    product_ids_to_load
                )
            )
            .order_by(
                Product.id.asc()
            )
            .with_for_update()
            .all()
        )

        if (
            len(products)
            != len(product_ids_to_load)
        ):
            raise ValueError(
                "One or more products were not found"
            )

        prepared_items = []

        total = Decimal(
            "0.00"
        )

        for product in products:

            product_platform = (
                product.platform
                .strip()
                .lower()
            )

            if product_platform != platform:
                raise ValueError(
                    f"{product.product_name} "
                    "does not belong to this platform"
                )

            if not product.is_active:
                raise ValueError(
                    f"{product.product_name} "
                    "is unavailable"
                )

            quantity = requested[
                product.id
            ]

            if (
                quantity
                > product.stock_quantity
            ):
                raise ValueError(
                    f"Only "
                    f"{product.stock_quantity} "
                    f"units of "
                    f"{product.product_name} "
                    "are available"
                )

            unit_price = normalize_money(
                product.price
            )

            line_total = (
                unit_price
                * quantity
            ).quantize(
                MONEY_PLACES,
                rounding=ROUND_HALF_UP,
            )

            prepared_items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )

            total += line_total

        total = total.quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        if len(prepared_items) == 1:

            compatibility_product_id = (
                prepared_items[0][
                    "product"
                ].id
            )

            compatibility_product_name = (
                prepared_items[0][
                    "product"
                ].product_name
            )

        else:

            compatibility_product_id = None

            compatibility_product_name = (
                "Multiple Products"
            )

        order = model(
            customer_name=customer_name,
            order_number=order_number,
            product_id=(
                compatibility_product_id
            ),
            product_name=(
                compatibility_product_name
            ),
            amount=float(total),
            status="pending",
            order_date=order_date,
            client_id=client_id,
        )

        db.add(
            order
        )

        db.flush()

        for item in prepared_items:

            product = item[
                "product"
            ]

            create_order_item(
                db=db,
                platform=platform,
                order_id=order.id,
                product_id=product.id,
                product_name=(
                    product.product_name
                ),
                unit_price=item[
                    "unit_price"
                ],
                quantity=item[
                    "quantity"
                ],
            )

            product.stock_quantity -= (
                item[
                    "quantity"
                ]
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