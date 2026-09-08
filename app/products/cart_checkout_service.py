from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from sqlalchemy.orm import Session

from app.orders.models import (
    SwiggyOrders,
)

from app.orders.order_item_service import (
    create_order_item,
)

from app.products.models import (
    Product,
)

from app.products.service import (
    generate_order_number,
)


PLATFORM = "swiggy"

MONEY_PLACES = Decimal(
    "0.01"
)


def normalize_money(
    value,
):
    return Decimal(
        str(value)
    ).quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def normalize_cart(
    cart,
):
    normalized = {}


    if not cart:
        return normalized


    if isinstance(
        cart,
        dict,
    ):

        for product_id, quantity in (
            cart.items()
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
                continue


            if quantity <= 0:
                continue


            normalized[
                product_id
            ] = quantity


    return normalized


def create_cart_orders(
    db: Session,
    cart,
    customer_name: str,
    order_date,
    client_id: int,

    delivery_name: str | None = None,
    delivery_phone: str | None = None,

    delivery_address_line1: str | None = None,
    delivery_address_line2: str | None = None,

    delivery_city: str | None = None,
    delivery_state: str | None = None,

    delivery_postal_code: str | None = None,
    delivery_country: str | None = None,
):
    customer_name = (
        customer_name.strip()
    )


    if not customer_name:

        raise ValueError(
            "Customer name is required."
        )


    normalized_cart = (
        normalize_cart(
            cart
        )
    )


    if not normalized_cart:

        raise ValueError(
            "Your cart is empty."
        )


    try:

        prepared_items = []


        # =====================================
        # LOCK AND VALIDATE PRODUCTS
        # =====================================

        for (
            product_id,
            quantity,
        ) in normalized_cart.items():

            product = (
                db.query(Product)
                .filter(
                    Product.id
                    ==
                    product_id
                )
                .with_for_update()
                .first()
            )


            if product is None:

                raise ValueError(
                    "One or more products "
                    "could not be found."
                )


            if (
                not product.platform
                or
                product.platform.lower()
                !=
                PLATFORM
            ):

                raise ValueError(
                    "Only Swiggy products "
                    "can be purchased from "
                    "the Swiggy cart."
                )


            if not product.is_active:

                raise ValueError(
                    f"{product.product_name} "
                    "is currently unavailable."
                )


            if quantity <= 0:

                raise ValueError(
                    "Product quantity must "
                    "be greater than zero."
                )


            if (
                quantity
                >
                product.stock_quantity
            ):

                raise ValueError(
                    f"Only "
                    f"{product.stock_quantity} "
                    f"units of "
                    f"{product.product_name} "
                    "are currently available."
                )


            unit_price = (
                normalize_money(
                    product.price
                )
            )


            line_total = (
                normalize_money(
                    unit_price
                    *
                    quantity
                )
            )


            prepared_items.append(
                {
                    "product":
                        product,

                    "product_id":
                        product.id,

                    "product_name":
                        product.product_name,

                    "unit_price":
                        unit_price,

                    "quantity":
                        quantity,

                    "line_total":
                        line_total,
                }
            )


        if not prepared_items:

            raise ValueError(
                "Your cart is empty."
            )


        # =====================================
        # ORDER TOTAL
        # =====================================

        order_total = sum(
            (
                item[
                    "line_total"
                ]
                for item
                in prepared_items
            ),
            Decimal("0.00"),
        )


        order_total = (
            normalize_money(
                order_total
            )
        )


        # =====================================
        # ORDER HEADER DESCRIPTION
        # =====================================

        first_item = (
            prepared_items[0]
        )


        if len(
            prepared_items
        ) == 1:

            order_product_name = (
                first_item[
                    "product_name"
                ]
            )


        else:

            remaining_count = (
                len(
                    prepared_items
                )
                -
                1
            )

            order_product_name = (
                f"{first_item['product_name']} "
                f"+ {remaining_count} more"
            )


        # =====================================
        # ORDER NUMBER
        # =====================================

        order_number = (
            generate_order_number(
                db=db,
                platform=PLATFORM,
            )
        )


        # =====================================
        # CREATE SWIGGY ORDER
        # =====================================

        order = SwiggyOrders(
            customer_name=(
                customer_name
            ),

            order_number=(
                order_number
            ),

            product_id=(
                first_item[
                    "product_id"
                ]
            ),

            product_name=(
                order_product_name
            ),

            amount=(
                float(
                    order_total
                )
            ),

            status="pending",

            order_date=(
                order_date
            ),

            client_id=(
                client_id
            ),

            delivery_name=(
                delivery_name
            ),

            delivery_phone=(
                delivery_phone
            ),

            delivery_address_line1=(
                delivery_address_line1
            ),

            delivery_address_line2=(
                delivery_address_line2
            ),

            delivery_city=(
                delivery_city
            ),

            delivery_state=(
                delivery_state
            ),

            delivery_postal_code=(
                delivery_postal_code
            ),

            delivery_country=(
                delivery_country
            ),
        )


        db.add(
            order
        )

        db.flush()


        # =====================================
        # CREATE ORDER ITEMS
        # =====================================

        email_items = []


        for item in prepared_items:

            create_order_item(
                db=db,

                platform=PLATFORM,

                order_id=(
                    order.id
                ),

                product_id=(
                    item[
                        "product_id"
                    ]
                ),

                product_name=(
                    item[
                        "product_name"
                    ]
                ),

                unit_price=(
                    item[
                        "unit_price"
                    ]
                ),

                quantity=(
                    item[
                        "quantity"
                    ]
                ),
            )


            # =================================
            # REDUCE STOCK
            # =================================

            product = ( 
                item["product"]
            )


            product.stock_quantity = (
                product.stock_quantity
                -
                item["quantity"]
            )


            # =================================
            # SAFE RESULT DATA
            # =================================

            email_items.append(
                {
                    "product_id":
                        item[
                            "product_id"
                        ],

                    "product_name":
                        item[
                            "product_name"
                        ],

                    "unit_price":
                        float(
                            item[
                                "unit_price"
                            ]
                        ),

                    "quantity":
                        int(
                            item[
                                "quantity"
                            ]
                        ),

                    "line_total":
                        float(
                            item[
                                "line_total"
                            ]
                        ),
                }
            )


        # =====================================
        # COMMIT
        # =====================================

        db.commit()

        db.refresh(
            order
        )


        # =====================================
        # KEEP EXISTING RETURN SHAPE
        # =====================================

        return [
            {
                "platform":
                    PLATFORM,

                "order":
                    order,

                "items":
                    email_items,
            }
        ]


    except ValueError:

        db.rollback()

        raise


    except Exception:

        db.rollback()

        raise