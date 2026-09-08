from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.orders.models import SwiggyOrders
from app.products.models import CartItem, Product


PLATFORM = "swiggy"

MONEY_PLACES = Decimal("0.01")


def get_swiggy_products(
    db: Session,
    limit: int | None = None,
    search_query: str = "",
):
    query = (
        db.query(Product)
        .filter(
            Product.is_active == True,
            Product.platform.ilike(PLATFORM),
        )
    )

    search_query = search_query.strip()

    if search_query:
        pattern = f"%{search_query}%"

        query = query.filter(
            or_(
                Product.product_name.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )

    query = query.order_by(
        Product.id.asc()
    )

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def get_swiggy_product(
    db: Session,
    product_id: int,
):
    return (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active == True,
            Product.platform.ilike(PLATFORM),
        )
        .first()
    )


def get_swiggy_cart(
    db: Session,
    user_id: int,
):
    rows = (
        db.query(CartItem)
        .join(
            Product,
            Product.id == CartItem.product_id,
        )
        .filter(
            CartItem.user_id == user_id,
            Product.platform.ilike(PLATFORM),
        )
        .all()
    )

    cart = {}

    for row in rows:

        if (
            row.product_id > 0
            and
            row.quantity > 0
        ):
            cart[row.product_id] = row.quantity

    return cart


def get_swiggy_cart_count(
    db: Session,
    user_id: int,
):
    cart = get_swiggy_cart(
        db=db,
        user_id=user_id,
    )

    return sum(
        cart.values()
    )


def get_swiggy_cart_details(
    db: Session,
    user_id: int,
):
    cart = get_swiggy_cart(
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
            Product.id.in_(product_ids),
            Product.platform.ilike(PLATFORM),
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
            unit_price * quantity
        ).quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        is_available = (
            product.is_active
            and
            product.stock_quantity >= quantity
        )

        if not is_available:
            has_stock_errors = True

        items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "is_available": is_available,
                "available_stock": product.stock_quantity,
            }
        )

        total += line_total

        item_count += quantity

    total = total.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )

    items.sort(
        key=lambda item:
            item["product"].product_name.lower()
    )

    return {
        "items": items,
        "total": total,
        "item_count": item_count,
        "has_stock_errors": has_stock_errors,
    }


def clear_swiggy_cart(
    db: Session,
    user_id: int,
):
    rows = (
        db.query(CartItem)
        .join(
            Product,
            Product.id == CartItem.product_id,
        )
        .filter(
            CartItem.user_id == user_id,
            Product.platform.ilike(PLATFORM),
        )
        .all()
    )

    for row in rows:
        db.delete(row)

    db.commit()

    return len(rows)


def get_client_swiggy_orders(
    db: Session,
    client_id: int,
):
    return (
        db.query(SwiggyOrders)
        .filter(
            SwiggyOrders.client_id == client_id
        )
        .order_by(
            SwiggyOrders.id.desc()
        )
        .all()
    )


def get_client_swiggy_order(
    db: Session,
    client_id: int,
    order_id: int,
):
    return (
        db.query(SwiggyOrders)
        .filter(
            SwiggyOrders.id == order_id,
            SwiggyOrders.client_id == client_id,
        )
        .first()
    )