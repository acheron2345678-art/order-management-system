from sqlalchemy.orm import Session

from app.orders.validation import (
    validate_positive_id,
)

from app.products.models import (
    Product,
)

from app.products.service import (
    create_catalog_item,
    set_catalog_item_active_state,
    update_catalog_item,
)


SWIGGY_PLATFORM = "swiggy"


def get_merchant_menu_items(
    db: Session,
    restaurant_id: int,
    include_inactive: bool = True,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    query = (
        db.query(Product)
        .filter(
            Product.platform.ilike(
                SWIGGY_PLATFORM
            ),
            Product.restaurant_id
            ==
            restaurant_id,
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
            Product.menu_category.asc(),
            Product.product_name.asc(),
            Product.id.asc(),
        )
        .all()
    )


def get_merchant_menu_item(
    db: Session,
    restaurant_id: int,
    product_id: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    product_id = validate_positive_id(
        product_id,
        "Product ID",
    )

    return (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.platform.ilike(
                SWIGGY_PLATFORM
            ),
            Product.restaurant_id
            ==
            restaurant_id,
        )
        .first()
    )


def build_merchant_menu_summary(
    products,
):
    return {
        "total_items":
            len(products),

        "active_items":
            sum(
                1
                for product in products
                if product.is_active
            ),

        "inactive_items":
            sum(
                1
                for product in products
                if not product.is_active
            ),

        "bestseller_items":
            sum(
                1
                for product in products
                if product.is_bestseller
            ),

        "low_stock_items":
            sum(
                1
                for product in products
                if (
                    product.stock_quantity > 0
                    and
                    product.stock_quantity
                    <=
                    product.reorder_level
                )
            ),

        "out_of_stock_items":
            sum(
                1
                for product in products
                if product.stock_quantity <= 0
            ),
    }


def create_merchant_menu_item(
    db: Session,
    restaurant_id: int,
    *,
    product_name: str,
    description: str,
    price,
    stock_quantity: int,
    reorder_level: int,
    menu_category: str,
    is_bestseller: bool,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    return create_catalog_item(
        db=db,

        product_name=product_name,

        description=description,

        price=price,

        platform="swiggy",

        stock_quantity=stock_quantity,

        reorder_level=reorder_level,

        restaurant_id=restaurant_id,

        menu_category=menu_category,

        is_bestseller=is_bestseller,
    )


def update_merchant_menu_item(
    db: Session,
    restaurant_id: int,
    product_id: int,
    *,
    product_name: str,
    description: str,
    price,
    stock_quantity: int,
    reorder_level: int,
    menu_category: str,
    is_bestseller: bool,
):
    product = get_merchant_menu_item(
        db=db,

        restaurant_id=restaurant_id,

        product_id=product_id,
    )

    if product is None:
        return None

    return update_catalog_item(
        db=db,

        product=product,

        product_name=product_name,

        description=description,

        price=price,

        stock_quantity=stock_quantity,

        reorder_level=reorder_level,

        # IMPORTANT:
        # Restaurant comes from the
        # authenticated Merchant assignment.
        restaurant_id=restaurant_id,

        menu_category=menu_category,

        is_bestseller=is_bestseller,
    )


def set_merchant_menu_item_active_state(
    db: Session,
    restaurant_id: int,
    product_id: int,
    is_active: bool,
):
    product = get_merchant_menu_item(
        db=db,

        restaurant_id=restaurant_id,

        product_id=product_id,
    )

    if product is None:
        return None

    return set_catalog_item_active_state(
        db=db,

        product=product,

        is_active=is_active,
    )