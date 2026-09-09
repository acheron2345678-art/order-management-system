from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.orders.models import SwiggyOrders
from app.orders.validation import validate_positive_id
from app.products.models import CartItem, Product, Restaurant


PLATFORM = "swiggy"
MONEY_PLACES = Decimal("0.01")


CATEGORY_ICONS = {
    "burger": "🍔",
    "burgers": "🍔",
    "pizza": "🍕",
    "pizzas": "🍕",
    "biryani": "🍛",
    "south indian": "🥞",
    "wraps & rolls": "🌯",
    "wraps": "🌯",
    "rolls": "🌯",
    "pasta": "🍝",
    "desserts": "🍰",
    "beverages": "🥤",
    "drinks": "🥤",
    "starters": "🍗",
    "main course": "🍲",
    "recommended": "⭐",
    "bestsellers": "🔥",
}


def get_category_icon(category_name: str) -> str:
    normalized = (category_name or "").strip().lower()
    return CATEGORY_ICONS.get(normalized, "🍽️")


def get_swiggy_menu_categories(
    db: Session,
    limit: int = 8,
):
    rows = (
        db.query(
            Product.menu_category,
            func.count(Product.id).label("dish_count"),
        )
        .join(
            Restaurant,
            Restaurant.id == Product.restaurant_id,
        )
        .filter(
            Product.is_active.is_(True),
            Product.platform.ilike(PLATFORM),
            Product.menu_category.is_not(None),
            Restaurant.is_active.is_(True),
        )
        .group_by(Product.menu_category)
        .order_by(
            func.count(Product.id).desc(),
            Product.menu_category.asc(),
        )
        .limit(limit)
        .all()
    )

    categories = []

    for category_name, dish_count in rows:
        category_name = (category_name or "").strip()

        if not category_name:
            continue

        categories.append(
            {
                "name": category_name,
                "dish_count": int(dish_count or 0),
                "icon": get_category_icon(category_name),
            }
        )

    return categories


def get_swiggy_restaurants(
    db: Session,
    limit: int | None = None,
):
    restaurants = (
        db.query(Restaurant)
        .options(
            selectinload(Restaurant.products)
        )
        .filter(
            Restaurant.is_active.is_(True)
        )
        .order_by(
            Restaurant.rating.desc(),
            Restaurant.name.asc(),
        )
        .all()
    )

    cards = []

    for restaurant in restaurants:
        active_products = [
            product
            for product in restaurant.products
            if product.is_active
            and (product.platform or "").strip().lower() == PLATFORM
        ]

        if not active_products:
            continue

        prices = [
            Decimal(str(product.price)).quantize(
                MONEY_PLACES,
                rounding=ROUND_HALF_UP,
            )
            for product in active_products
        ]

        cards.append(
            {
                "restaurant": restaurant,
                "dish_count": len(active_products),
                "bestseller_count": sum(
                    1
                    for product in active_products
                    if bool(product.is_bestseller)
                ),
                "starting_price": min(prices),
            }
        )

    if limit is not None:
        cards = cards[:limit]

    return cards


def get_swiggy_restaurant(
    db: Session,
    restaurant_id: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    return (
        db.query(Restaurant)
        .filter(
            Restaurant.id == restaurant_id,
            Restaurant.is_active.is_(True),
        )
        .first()
    )


def get_swiggy_products(
    db: Session,
    limit: int | None = None,
    search_query: str = "",
    restaurant_id: int | None = None,
):
    query = (
        db.query(Product)
        .join(
            Restaurant,
            Restaurant.id == Product.restaurant_id,
        )
        .filter(
            Product.is_active.is_(True),
            Product.platform.ilike(PLATFORM),
            Restaurant.is_active.is_(True),
        )
    )

    if restaurant_id is not None:
        restaurant_id = validate_positive_id(
            restaurant_id,
            "Restaurant ID",
        )

        query = query.filter(
            Product.restaurant_id == restaurant_id
        )

    search_query = (search_query or "").strip()

    if search_query:
        pattern = f"%{search_query}%"

        query = query.filter(
            or_(
                Product.product_name.ilike(pattern),
                Product.description.ilike(pattern),
                Product.menu_category.ilike(pattern),
            )
        )

    query = query.order_by(
        Product.is_bestseller.desc(),
        Product.menu_category.asc(),
        Product.product_name.asc(),
    )

    if limit is not None:
        query = query.limit(limit)

    return query.all()



def _menu_anchor(value: str) -> str:
    cleaned = []
    previous_dash = False

    for character in (value or "").strip().lower():
        if character.isalnum():
            cleaned.append(character)
            previous_dash = False
        elif not previous_dash:
            cleaned.append("-")
            previous_dash = True

    anchor = "".join(cleaned).strip("-")
    return anchor or "menu"


def get_swiggy_restaurant_menu(
    db: Session,
    restaurant_id: int,
    search_query: str = "",
):
    restaurant = get_swiggy_restaurant(
        db=db,
        restaurant_id=restaurant_id,
    )

    if restaurant is None:
        return None

    products = get_swiggy_products(
        db=db,
        search_query=search_query,
        restaurant_id=restaurant.id,
    )

    recommended_products = [
        product
        for product in products
        if bool(product.is_bestseller)
    ]

    if not recommended_products and not search_query and products:
        recommended_products = products[: min(4, len(products))]

    category_map = {}

    for product in products:
        category_name = (product.menu_category or "Other").strip() or "Other"

        if category_name not in category_map:
            category_map[category_name] = []

        category_map[category_name].append(product)

    category_groups = [
        {
            "name": category_name,
            "anchor": _menu_anchor(category_name),
            "products": category_products,
        }
        for category_name, category_products in category_map.items()
    ]

    return {
        "restaurant": restaurant,
        "products": products,
        "recommended_products": recommended_products,
        "category_groups": category_groups,
        "dish_count": len(products),
        "search_query": (search_query or "").strip(),
    }

def get_swiggy_product(
    db: Session,
    product_id: int,
):
    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    return (
        db.query(Product)
        .join(
            Restaurant,
            Restaurant.id == Product.restaurant_id,
        )
        .filter(
            Product.id == product_id,
            Product.is_active.is_(True),
            Product.platform.ilike(PLATFORM),
            Restaurant.is_active.is_(True),
        )
        .first()
    )


def get_swiggy_cart(
    db: Session,
    user_id: int,
):
    rows = (
        db.query(CartItem)
        .join(Product, Product.id == CartItem.product_id)
        .filter(
            CartItem.user_id == user_id,
            Product.platform.ilike(PLATFORM),
        )
        .all()
    )

    cart = {}

    for row in rows:
        if row.product_id > 0 and row.quantity > 0:
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

    return sum(cart.values())


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

    product_ids = list(cart.keys())

    products = (
        db.query(Product)
        .options(selectinload(Product.restaurant))
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
        product = product_map.get(product_id)

        if product is None:
            has_stock_errors = True
            continue

        unit_price = Decimal(str(product.price)).quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        line_total = (unit_price * quantity).quantize(
            MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

        restaurant_available = (
            product.restaurant is not None
            and product.restaurant.is_active
        )

        is_available = (
            product.is_active
            and restaurant_available
            and product.stock_quantity >= quantity
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
        key=lambda item: (
            (
                item["product"].restaurant.name.lower()
                if item["product"].restaurant
                else ""
            ),
            item["product"].product_name.lower(),
        )
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
        .join(Product, Product.id == CartItem.product_id)
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