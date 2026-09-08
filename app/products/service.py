from uuid import uuid4

from sqlalchemy.orm import Session

from datetime import datetime

from app.products.models import Product
from app.orders.models import (
    SwiggyOrders,
    InsightsOrders,
)

from decimal import Decimal,InvalidOperation

def get_products(
    db: Session,
    active_only: bool = True,
):
    query = db.query(Product)

    if active_only:
        query = query.filter(
            Product.is_active == True
        )

    return (
        query
        .order_by(Product.id.asc())
        .all()
    )


def get_product(
    db: Session,
    product_id: int,
):
    return (
        db.query(Product)
        .filter(
            Product.id == product_id
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
    product = Product(
        product_name=product_name,
        description=description,
        price=price,
        platform=platform,
        image_url=image_url,
        is_active=True,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

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
            product_name
        )

    if description is not None:
        product.description = (
            description
        )

    if price is not None:
        product.price = price

    if platform is not None:
        product.platform = platform

    if image_url is not None:
        product.image_url = image_url

    if is_active is not None:
        product.is_active = (
            is_active
        )

    db.commit()
    db.refresh(product)

    return product


def generate_order_number(
    db: Session,
    platform: str,
):
    platform = (
        platform
        .strip()
        .lower()
    )

    if platform == "swiggy":

        prefix = "SW"
        model = SwiggyOrders

    elif platform == "insights":

        prefix = "IN"
        model = InsightsOrders

    else:

        raise ValueError(
            "Invalid product platform"
        )

    while True:

        order_number = (
            f"{prefix}"
            f"{uuid4().hex[:8].upper()}"
        )

        existing_order = (
            db.query(model)
            .filter(
                model.order_number
                == order_number
            )
            .first()
        )

        if existing_order is None:
            return order_number


def create_checkout_order(
    db: Session,
    product: Product,
    customer_name: str,
    order_date,
    client_id: int,
):
    try:

        locked_product = (
            db.query(Product)
            .filter(
                Product.id == product.id
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

        platform = (
            locked_product.platform
            .strip()
            .lower()
        )

        if platform == "swiggy":

            model = SwiggyOrders

        elif platform == "insights":

            model = InsightsOrders

        else:

            raise ValueError(
                "Product has an invalid platform"
            )

        customer_name = (
            customer_name.strip()
        )

        if not customer_name:
            raise ValueError(
                "Customer name is required"
            )

        order_number = (
            generate_order_number(
                db,
                locked_product.platform,
            )
        )

        new_order = model(
            customer_name=customer_name,
            order_number=order_number,
            product_id=locked_product.id,
            product_name=(
                locked_product.product_name
            ),
            amount=float(
                locked_product.price
            ),
            status="pending",
            order_date=order_date,
            client_id=client_id,
        )

        locked_product.stock_quantity -= 1

        db.add(new_order)

        db.commit()

        db.refresh(new_order)
        db.refresh(locked_product)

        return new_order

    except ValueError:

        db.rollback()
        raise

    except Exception:

        db.rollback()
        raise


def get_products_from_platform(
    db: Session,
    platform: str,
):
    return (
        db.query(Product)
        .filter(
            Product.is_active == True,
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
    return (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active == True,
            Product.platform.ilike(
                platform
            ),
        )
        .first()
    )


def restock_product(
        db:Session,
        product_id:int,
        quantity:int
):
    if quantity<=0:
        raise ValueError("Restock quantity must be greater than zero")

    try:
        product=(db.query(Product).filter(Product.id==product_id).with_for_update().first())

        if not product:
            raise ValueError("Product not Found")

        product.stock_quantity+=quantity

        product.last_restocked=(datetime.now())

        db.commit()
        db.refresh(product)
        return product

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

def bulk_restock_products(
    db: Session,
    product_ids: list[int],
    quantities: list[int],
):
    if len(product_ids) != len(quantities):
        raise ValueError(
            "Invalid inventory data"
        )

    restock_data = {}

    for product_id, quantity in zip(
        product_ids,
        quantities,
    ):
        if quantity < 0:
            raise ValueError(
                "Restock quantity cannot be negative"
            )

        if quantity > 0:
            restock_data[product_id] = quantity

    if not restock_data:
        raise ValueError(
            "Enter a quantity for at least one product"
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
            != len(product_ids_to_update)
        ):
            raise ValueError(
                "One or more products were not found"
            )

        restock_time = datetime.now()

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
            db.refresh(product)

        return products

    except ValueError:

        db.rollback()
        raise

    except Exception:

        db.rollback()
        raise

def normalize_platform(
    platform: str,
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
            "Invalid platform."
        )

    return platform


def normalize_product_price(
    price,
):
    try:
        price = Decimal(
            str(price)
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            "Invalid price."
        ) from exc


    if price < 0:
        raise ValueError(
            "Price cannot be negative."
        )


    return price.quantize(
        Decimal("0.01")
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
            Product.is_active == True
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
        product_name.strip()
    )

    description = (
        description.strip()
        if description
        else None
    )

    platform = normalize_platform(
        platform
    )

    price = normalize_product_price(
        price
    )


    if not product_name:

        raise ValueError(
            "Name is required."
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


    # =========================================
    # SWIGGY INVENTORY
    # =========================================

    if platform == "swiggy":

        if stock_quantity < 0:
            raise ValueError(
                "Stock quantity cannot "
                "be negative."
            )

        if reorder_level < 0:
            raise ValueError(
                "Reorder level cannot "
                "be negative."
            )


    # =========================================
    # INSIGHTS HAS NO INVENTORY
    # =========================================

    else:

        stock_quantity = 0
        reorder_level = 0


    product = Product(
        product_name=product_name,
        description=description,
        price=price,
        platform=platform,
        is_active=True,
        stock_quantity=stock_quantity,
        reorder_level=reorder_level,
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
    stock_quantity: int | None = None,
    reorder_level: int | None = None,
):
    product_name = (
        product_name.strip()
    )

    description = (
        description.strip()
        if description
        else None
    )


    if not product_name:

        raise ValueError(
            "Name is required."
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


    # =========================================
    # SWIGGY INVENTORY SETTINGS
    # =========================================

    if (
        product.platform.lower()
        ==
        "swiggy"
    ):

        if stock_quantity is None:
            stock_quantity = (
                product.stock_quantity
            )

        if reorder_level is None:
            reorder_level = (
                product.reorder_level
            )


        if stock_quantity < 0:
            raise ValueError(
                "Stock quantity cannot "
                "be negative."
            )


        if reorder_level < 0:
            raise ValueError(
                "Reorder level cannot "
                "be negative."
            )


        product.stock_quantity = (
            stock_quantity
        )

        product.reorder_level = (
            reorder_level
        )


    # =========================================
    # INSIGHTS
    # =========================================

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
    product.is_active = (
        is_active
    )

    db.commit()

    db.refresh(
        product
    )

    return product