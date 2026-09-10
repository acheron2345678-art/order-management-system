from datetime import datetime

from sqlalchemy.orm import Session

from app.orders.validation import (
    validate_non_negative_integer,
    validate_positive_id,
    validate_positive_quantity,
)

from app.products.models import Product


SWIGGY_PLATFORM = "swiggy"


def get_merchant_inventory_items(
    db: Session,
    restaurant_id: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    return (
        db.query(Product)
        .filter(
            Product.platform.ilike(
                SWIGGY_PLATFORM
            ),
            Product.restaurant_id
            ==
            restaurant_id,
        )
        .order_by(
            Product.stock_quantity.asc(),
            Product.product_name.asc(),
            Product.id.asc(),
        )
        .all()
    )


def get_merchant_inventory_item(
    db: Session,
    restaurant_id: int,
    product_id: int,
    *,
    lock: bool = False,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    query = (
        db.query(Product)
        .filter(
            Product.id
            ==
            product_id,

            Product.platform.ilike(
                SWIGGY_PLATFORM
            ),

            Product.restaurant_id
            ==
            restaurant_id,
        )
    )

    if lock:
        query = query.with_for_update()

    return query.first()


def build_merchant_inventory_summary(
    products,
):
    total_units = sum(
        max(
            product.stock_quantity,
            0,
        )
        for product in products
    )

    out_of_stock = sum(
        1
        for product in products
        if product.stock_quantity <= 0
    )

    low_stock = sum(
        1
        for product in products
        if (
            product.stock_quantity > 0
            and
            product.stock_quantity
            <=
            product.reorder_level
        )
    )

    healthy_stock = sum(
        1
        for product in products
        if (
            product.stock_quantity
            >
            product.reorder_level
        )
    )

    never_restocked = sum(
        1
        for product in products
        if product.last_restocked is None
    )

    return {
        "total_products":
            len(products),

        "total_units":
            total_units,

        "healthy_stock":
            healthy_stock,

        "low_stock":
            low_stock,

        "out_of_stock":
            out_of_stock,

        "never_restocked":
            never_restocked,
    }


def restock_merchant_inventory_item(
    db: Session,
    restaurant_id: int,
    product_id: int,
    quantity: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    quantity = validate_positive_quantity(
        quantity,
        "Restock quantity",
    )

    try:

        product = (
            get_merchant_inventory_item(
                db=db,
                restaurant_id=restaurant_id,
                product_id=product_id,
                lock=True,
            )
        )

        if product is None:
            raise ValueError(
                "Inventory item not found."
            )

        product.stock_quantity = (
            product.stock_quantity
            +
            quantity
        )

        product.last_restocked = (
            datetime.now()
        )

        db.commit()

        db.refresh(
            product
        )

        return product

    except Exception:

        db.rollback()
        raise


def adjust_merchant_inventory_item(
    db: Session,
    restaurant_id: int,
    product_id: int,
    *,
    stock_quantity: int,
    reorder_level: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    stock_quantity = (
        validate_non_negative_integer(
            stock_quantity,
            "Stock quantity",
        )
    )

    reorder_level = (
        validate_non_negative_integer(
            reorder_level,
            "Reorder level",
        )
    )

    try:

        product = (
            get_merchant_inventory_item(
                db=db,
                restaurant_id=restaurant_id,
                product_id=product_id,
                lock=True,
            )
        )

        if product is None:
            raise ValueError(
                "Inventory item not found."
            )

        previous_stock = (
            product.stock_quantity
        )

        product.stock_quantity = (
            stock_quantity
        )

        product.reorder_level = (
            reorder_level
        )

        # Only count this as a restock when
        # the corrected quantity increased.
        if (
            stock_quantity
            >
            previous_stock
        ):
            product.last_restocked = (
                datetime.now()
            )

        db.commit()

        db.refresh(
            product
        )

        return product

    except Exception:

        db.rollback()
        raise


def bulk_restock_merchant_inventory(
    db: Session,
    restaurant_id: int,
    product_ids: list[int],
    quantities: list[int],
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    if (
        len(product_ids)
        !=
        len(quantities)
    ):
        raise ValueError(
            "Invalid bulk restock data."
        )

    restock_data = {}

    for (
        product_id,
        quantity,
    ) in zip(
        product_ids,
        quantities,
    ):
        product_id = validate_positive_id(
            product_id,
            "Product ID",
        )

        quantity = (
            validate_non_negative_integer(
                quantity,
                "Restock quantity",
            )
        )

        if quantity > 0:
            restock_data[
                product_id
            ] = quantity

    if not restock_data:
        raise ValueError(
            "Enter a restock quantity "
            "for at least one dish."
        )

    try:

        product_ids_to_update = sorted(
            restock_data.keys()
        )

        products = (
            db.query(Product)
            .filter(
                Product.id.in_(
                    product_ids_to_update
                ),

                Product.platform.ilike(
                    SWIGGY_PLATFORM
                ),

                Product.restaurant_id
                ==
                restaurant_id,
            )
            .order_by(
                Product.id.asc()
            )
            .with_for_update()
            .all()
        )

        # Important security check.
        #
        # If a Merchant tampers with the
        # submitted IDs and includes a product
        # belonging to another restaurant,
        # that product will not be returned.
        if (
            len(products)
            !=
            len(product_ids_to_update)
        ):
            raise ValueError(
                "One or more inventory items "
                "do not belong to your restaurant."
            )

        restock_time = (
            datetime.now()
        )

        for product in products:

            quantity = restock_data[
                product.id
            ]

            product.stock_quantity = (
                product.stock_quantity
                +
                quantity
            )

            product.last_restocked = (
                restock_time
            )

        db.commit()

        for product in products:
            db.refresh(
                product
            )

        return products

    except Exception:

        db.rollback()
        raise