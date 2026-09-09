from datetime import datetime

from decimal import Decimal

from uuid import uuid4

from sqlalchemy.orm import Session

from app.orders.models import (
    InsightsOrders,
    SwiggyOrders,
)

from app.orders.validation import (
    clean_optional_text,
    clean_required_text,
    validate_non_negative_integer,
    validate_platform,
    validate_positive_id,
    validate_positive_money,
)

from app.products.models import (
    Product,
)


ORDER_NUMBER_ATTEMPTS = 20


def get_products(
    db: Session,
    active_only: bool = True,
):
    query = db.query(
        Product
    )

    if active_only:
        query = query.filter(
            Product.is_active.is_(
                True
            )
        )

    return query.order_by(
        Product.id.asc()
    ).all()


def get_product(
    db: Session,
    product_id: int,
):
    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    return (
        db.query(
            Product
        )
        .filter(
            Product.id
            ==
            product_id
        )
        .first()
    )


def create_product(
    db: Session,
    product_name: str,
    description: str | None,
    price,
    platform: str,
    image_url: str | None = None,
):
    product_name = (
        clean_required_text(
            product_name,
            "Product name",
            max_length=100,
        )
    )

    description = (
        clean_optional_text(
            description,
            "Description",
            max_length=255,
        )
    )

    price = normalize_product_price(
        price
    )

    platform = normalize_platform(
        platform
    )

    image_url = clean_optional_text(
        image_url,
        "Image URL",
        max_length=500,
    )

    product = Product(
        product_name=product_name,
        description=description,
        price=price,
        platform=platform,
        image_url=image_url,
        is_active=True,
    )

    db.add(
        product
    )

    db.commit()

    db.refresh(
        product
    )

    return product


def update_product(
    db: Session,
    product_id: int,
    product_name: str | None = None,
    description: str | None = None,
    price=None,
    platform: str | None = None,
    image_url: str | None = None,
    is_active: bool | None = None,
):
    product = get_product(
        db,
        product_id,
    )

    if not product:
        return None

    if product_name is not None:
        product.product_name = (
            clean_required_text(
                product_name,
                "Product name",
                max_length=100,
            )
        )

    if description is not None:
        product.description = (
            clean_optional_text(
                description,
                "Description",
                max_length=255,
            )
        )

    if price is not None:
        product.price = (
            normalize_product_price(
                price
            )
        )

    if platform is not None:
        product.platform = (
            normalize_platform(
                platform
            )
        )

    if image_url is not None:
        product.image_url = (
            clean_optional_text(
                image_url,
                "Image URL",
                max_length=500,
            )
        )

    if is_active is not None:
        product.is_active = bool(
            is_active
        )

    db.commit()

    db.refresh(
        product
    )

    return product


def generate_order_number(
    db: Session,
    platform: str,
):
    platform = normalize_platform(
        platform
    )

    if platform == "swiggy":
        prefix = "SW"
        model = SwiggyOrders

    else:
        prefix = "IN"
        model = InsightsOrders

    for _ in range(
        ORDER_NUMBER_ATTEMPTS
    ):
        order_number = (
            f"{prefix}"
            f"{uuid4().hex[:8].upper()}"
        )

        existing_order = (
            db.query(
                model
            )
            .filter(
                model.order_number
                ==
                order_number
            )
            .first()
        )

        if existing_order is None:
            return order_number

    raise RuntimeError(
        "Unable to generate "
        "a unique order number."
    )


def create_checkout_order(
    db: Session,
    product: Product,
    customer_name: str,
    order_date,
    client_id: int,
):
    client_id = validate_positive_id(
        client_id,
        "Client ID",
    )

    customer_name = (
        clean_required_text(
            customer_name,
            "Customer name",
            max_length=100,
        )
    )

    try:
        locked_product = (
            db.query(
                Product
            )
            .filter(
                Product.id
                ==
                validate_positive_id(
                    product.id,
                    "Product ID",
                )
            )
            .with_for_update()
            .first()
        )

        if not locked_product:
            raise ValueError(
                "Product not found"
            )

        if not locked_product.is_active:
            raise ValueError(
                "Product is currently unavailable"
            )

        if (
            locked_product.stock_quantity
            <= 0
        ):
            raise ValueError(
                "Product is out of stock"
            )

        platform = normalize_platform(
            locked_product.platform
        )

        if platform == "swiggy":
            model = SwiggyOrders

        else:
            model = InsightsOrders

        amount = normalize_product_price(
            locked_product.price
        )

        order_number = (
            generate_order_number(
                db,
                platform,
            )
        )

        new_order = model(
            customer_name=customer_name,

            order_number=order_number,

            product_id=(
                locked_product.id
            ),

            product_name=(
                locked_product.product_name
            ),

            amount=float(
                amount
            ),

            status="pending",

            order_date=(
                order_date
            ),

            client_id=(
                client_id
            ),
        )

        locked_product.stock_quantity -= (
            1
        )

        db.add(
            new_order
        )

        db.commit()

        db.refresh(
            new_order
        )

        db.refresh(
            locked_product
        )

        return new_order

    except Exception:
        db.rollback()
        raise


def get_products_from_platform(
    db: Session,
    platform: str,
):
    platform = normalize_platform(
        platform
    )

    return (
        db.query(
            Product
        )
        .filter(
            Product.is_active.is_(
                True
            ),

            Product.platform.ilike(
                platform
            ),
        )
        .order_by(
            Product.product_name.asc()
        )
        .all()
    )


def get_product_for_platform(
    db: Session,
    product_id: int,
    platform: str,
):
    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    platform = normalize_platform(
        platform
    )

    return (
        db.query(
            Product
        )
        .filter(
            Product.id
            ==
            product_id,

            Product.is_active.is_(
                True
            ),

            Product.platform.ilike(
                platform
            ),
        )
        .first()
    )


def restock_product(
    db: Session,
    product_id: int,
    quantity: int,
):
    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    quantity = validate_positive_id(
        quantity,
        "Restock quantity",
    )

    try:
        product = (
            db.query(
                Product
            )
            .filter(
                Product.id
                ==
                product_id
            )
            .with_for_update()
            .first()
        )

        if not product:
            raise ValueError(
                "Product not found"
            )

        product.stock_quantity += (
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


def bulk_restock_products(
    db: Session,
    product_ids: list[int],
    quantities: list[int],
):
    if (
        len(product_ids)
        !=
        len(quantities)
    ):
        raise ValueError(
            "Invalid inventory data"
        )

    restock_data = {}

    for (
        product_id,
        quantity,
    ) in zip(
        product_ids,
        quantities,
    ):
        product_id = (
            validate_positive_id(
                product_id,
                "Product ID",
            )
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
            "Enter a quantity for "
            "at least one product"
        )

    try:
        product_ids_to_update = (
            sorted(
                restock_data.keys()
            )
        )

        products = (
            db.query(
                Product
            )
            .filter(
                Product.id.in_(
                    product_ids_to_update
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
            !=
            len(
                product_ids_to_update
            )
        ):
            raise ValueError(
                "One or more products "
                "were not found"
            )

        restock_time = (
            datetime.now()
        )

        for product in products:
            quantity = restock_data[
                product.id
            ]

            product.stock_quantity += (
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


def normalize_platform(
    platform: str,
):
    return validate_platform(
        platform
    )


def normalize_product_price(
    price,
):
    return validate_positive_money(
        price,
        "Price",
    )


def get_admin_catalog_products(
    db: Session,
    platform: str | None = None,
    include_inactive: bool = True,
):
    query = db.query(
        Product
    )

    if platform:
        platform = normalize_platform(
            platform
        )

        query = query.filter(
            Product.platform.ilike(
                platform
            )
        )

    if not include_inactive:
        query = query.filter(
            Product.is_active.is_(
                True
            )
        )

    return (
        query
        .order_by(
            Product.platform.asc(),
            Product.product_name.asc(),
        )
        .all()
    )


def get_admin_product(
    db: Session,
    product_id: int,
):
    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    return (
        db.query(
            Product
        )
        .filter(
            Product.id
            ==
            product_id
        )
        .first()
    )


def create_catalog_item(
    db: Session,

    product_name: str,

    description: str,

    price,

    platform: str,

    stock_quantity: int = 0,

    reorder_level: int = 5,
):
    product_name = (
        clean_required_text(
            product_name,
            "Name",
            max_length=100,
        )
    )

    description = (
        clean_optional_text(
            description,
            "Description",
            max_length=255,
        )
    )

    platform = normalize_platform(
        platform
    )

    price = normalize_product_price(
        price
    )

    existing = (
        db.query(
            Product
        )
        .filter(
            Product.product_name.ilike(
                product_name
            ),

            Product.platform.ilike(
                platform
            ),
        )
        .first()
    )

    if existing:
        raise ValueError(
            "A catalog item with this "
            "name already exists on "
            "this platform."
        )

    if platform == "swiggy":
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

    else:
        stock_quantity = 0
        reorder_level = 0

    product = Product(
        product_name=product_name,

        description=description,

        price=price,

        platform=platform,

        is_active=True,

        stock_quantity=(
            stock_quantity
        ),

        reorder_level=(
            reorder_level
        ),
    )

    db.add(
        product
    )

    db.commit()

    db.refresh(
        product
    )

    return product


def update_catalog_item(
    db: Session,

    product: Product,

    product_name: str,

    description: str,

    price,

    stock_quantity: (
        int | None
    ) = None,

    reorder_level: (
        int | None
    ) = None,
):
    product_name = (
        clean_required_text(
            product_name,
            "Name",
            max_length=100,
        )
    )

    description = (
        clean_optional_text(
            description,
            "Description",
            max_length=255,
        )
    )

    price = normalize_product_price(
        price
    )

    duplicate = (
        db.query(
            Product
        )
        .filter(
            Product.id
            !=
            product.id,

            Product.product_name.ilike(
                product_name
            ),

            Product.platform.ilike(
                product.platform
            ),
        )
        .first()
    )

    if duplicate:
        raise ValueError(
            "Another catalog item with "
            "this name already exists "
            "on this platform."
        )

    product.product_name = (
        product_name
    )

    product.description = (
        description
    )

    product.price = (
        price
    )

    platform = normalize_platform(
        product.platform
    )

    if platform == "swiggy":
        if stock_quantity is None:
            stock_quantity = (
                product.stock_quantity
            )

        if reorder_level is None:
            reorder_level = (
                product.reorder_level
            )

        product.stock_quantity = (
            validate_non_negative_integer(
                stock_quantity,
                "Stock quantity",
            )
        )

        product.reorder_level = (
            validate_non_negative_integer(
                reorder_level,
                "Reorder level",
            )
        )

    else:
        product.stock_quantity = 0
        product.reorder_level = 0

    db.commit()

    db.refresh(
        product
    )

    return product


def set_catalog_item_active_state(
    db: Session,
    product: Product,
    is_active: bool,
):
    product.is_active = bool(
        is_active
    )

    db.commit()

    db.refresh(
        product
    )

    return product