from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from sqlalchemy.orm import Session

from app.products.models import (
    CartItem,
    Product,
)


MONEY_PLACES = Decimal("0.01")


def get_cart(
    db: Session,
    user_id: int,
):
    rows = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id
        )
        .all()
    )

    cart = {}

    for row in rows:
        if (
            row.product_id > 0
            and row.quantity > 0
        ):
            cart[row.product_id] = (
                row.quantity
            )

    return cart


def get_cart_count(
    db: Session,
    user_id: int,
):
    cart = get_cart(
        db=db,
        user_id=user_id,
    )

    return sum(
        cart.values()
    )


def add_to_cart(
    db: Session,
    user_id: int,
    product_id: int,
    quantity: int,
):
    if quantity <= 0:
        raise ValueError(
            "Quantity must be greater than 0"
        )

    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        .first()
    )

    if cart_item:
        cart_item.quantity += quantity

    else:
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
        )

        db.add(cart_item)

    db.commit()
    db.refresh(cart_item)

    return cart_item


def set_cart_quantity(
    db: Session,
    user_id: int,
    product_id: int,
    quantity: int,
):
    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        .first()
    )

    if quantity <= 0:
        if cart_item:
            db.delete(cart_item)
            db.commit()

        return None

    if cart_item:
        cart_item.quantity = quantity

    else:
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
        )

        db.add(cart_item)

    db.commit()
    db.refresh(cart_item)

    return cart_item


def remove_from_cart(
    db: Session,
    user_id: int,
    product_id: int,
):
    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        .first()
    )

    if not cart_item:
        return False

    db.delete(cart_item)
    db.commit()

    return True


def clear_cart(
    db: Session,
    user_id: int,
):
    deleted_count = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id
        )
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return deleted_count


def get_cart_details(
    db: Session,
    user_id: int,
):
    cart = get_cart(
        db=db,
        user_id=user_id,
    )

    if not cart:
        return {
            "items": [],
            "total": Decimal("0.00"),
            "item_count": 0,
            "has_stock_errors": False,
        }

    product_ids = list(
        cart.keys()
    )

    products = (
        db.query(Product)
        .filter(
            Product.id.in_(
                product_ids
            )
        )
        .all()
    )

    product_map = {
        product.id: product
        for product in products
    }

    items = []

    total = Decimal("0.00")

    item_count = 0

    has_stock_errors = False

    for product_id, quantity in cart.items():

        product = product_map.get(
            product_id
        )

        if product is None:
            has_stock_errors = True
            continue

        unit_price = Decimal(
            str(product.price)
        ).quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        line_total = (
            unit_price
            *
            quantity
        ).quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        is_available = (
            product.is_active
            and
            product.stock_quantity
            >=
            quantity
        )

        if not is_available:
            has_stock_errors = True

        items.append(
            {
                "product":
                    product,

                "quantity":
                    quantity,

                "unit_price":
                    unit_price,

                "line_total":
                    line_total,

                "is_available":
                    is_available,

                "available_stock":
                    product.stock_quantity,
            }
        )

        total += line_total

        item_count += quantity

    total = total.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )

    items.sort(
        key=lambda item: (
            item["product"].platform.lower(),
            item["product"].product_name.lower(),
        )
    )

    return {
        "items":
            items,

        "total":
            total,

        "item_count":
            item_count,

        "has_stock_errors":
            has_stock_errors,
    }


def group_cart_items_by_platform(
    cart_details: dict,
):
    grouped_items = {
        "swiggy": [],
        "insights": [],
    }

    for item in cart_details["items"]:

        platform = (
            item["product"]
            .platform
            .strip()
            .lower()
        )

        if platform not in grouped_items:
            raise ValueError(
                "Invalid product platform"
            )

        grouped_items[
            platform
        ].append(
            item
        )

    return grouped_items