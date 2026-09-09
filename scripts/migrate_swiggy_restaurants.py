from pathlib import Path
import sys


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine
from app.products.models import (
    Product,
    Restaurant,
)


STARTER_RESTAURANTS = [
    {
        "name": "Burger Junction",
        "description": (
            "Loaded burgers, crispy sides "
            "and quick comfort food."
        ),
        "cuisines": (
            "Burgers, American, Fast Food"
        ),
        "rating": 4.4,
        "delivery_min_minutes": 20,
        "delivery_max_minutes": 30,
        "location": "T. Nagar, Chennai",
        "offer_text": (
            "20% OFF up to ₹100"
        ),
    },
    {
        "name": "Pizza House",
        "description": (
            "Fresh pizzas, cheesy favourites "
            "and classic Italian-style bites."
        ),
        "cuisines": (
            "Pizzas, Italian, Fast Food"
        ),
        "rating": 4.3,
        "delivery_min_minutes": 25,
        "delivery_max_minutes": 35,
        "location": (
            "Velachery, Chennai"
        ),
        "offer_text": (
            "Free delivery on selected orders"
        ),
    },
    {
        "name": "Biryani House",
        "description": (
            "Aromatic biryanis, kebabs "
            "and hearty Indian meals."
        ),
        "cuisines": (
            "Biryani, North Indian, Kebabs"
        ),
        "rating": 4.5,
        "delivery_min_minutes": 25,
        "delivery_max_minutes": 35,
        "location": (
            "Anna Nagar, Chennai"
        ),
        "offer_text": (
            "₹125 OFF above ₹499"
        ),
    },
    {
        "name": "Southern Kitchen",
        "description": (
            "South Indian breakfast favourites, "
            "meals and regional comfort food."
        ),
        "cuisines": (
            "South Indian, Indian, Beverages"
        ),
        "rating": 4.6,
        "delivery_min_minutes": 20,
        "delivery_max_minutes": 30,
        "location": (
            "Adyar, Chennai"
        ),
        "offer_text": (
            "10% OFF on selected dishes"
        ),
    },
    {
        "name": "Wrap & Roll",
        "description": (
            "Fresh wraps, rolls, snacks and "
            "filling grab-and-go meals."
        ),
        "cuisines": (
            "Wraps, Rolls, North Indian, Snacks"
        ),
        "rating": 4.2,
        "delivery_min_minutes": 20,
        "delivery_max_minutes": 30,
        "location": (
            "Guindy, Chennai"
        ),
        "offer_text": (
            "15% OFF above ₹299"
        ),
    },
    {
        "name": "Pasta Street",
        "description": (
            "Creamy pastas, Italian-inspired mains "
            "and casual cafe favourites."
        ),
        "cuisines": (
            "Pasta, Italian, Continental"
        ),
        "rating": 4.3,
        "delivery_min_minutes": 25,
        "delivery_max_minutes": 35,
        "location": (
            "Nungambakkam, Chennai"
        ),
        "offer_text": (
            "20% OFF on selected dishes"
        ),
    },
    {
        "name": "City Kitchen",
        "description": (
            "A flexible multi-cuisine kitchen for "
            "dishes that do not yet belong to a "
            "specialist restaurant."
        ),
        "cuisines": "Multi-cuisine",
        "rating": 4.1,
        "delivery_min_minutes": 25,
        "delivery_max_minutes": 35,
        "location": "Chennai",
        "offer_text": None,
    },
]


PRODUCT_ASSIGNMENT_RULES = [
    (
        (
            "burger",
        ),
        "Burger Junction",
        "Burgers",
    ),

    (
        (
            "pizza",
        ),
        "Pizza House",
        "Pizzas",
    ),

    (
        (
            "biryani",
            "kebab",
        ),
        "Biryani House",
        "Biryani",
    ),

    (
        (
            "dosa",
            "idli",
            "vada",
            "sambar",
            "uttapam",
        ),
        "Southern Kitchen",
        "South Indian",
    ),

    (
        (
            "wrap",
            "roll",
        ),
        "Wrap & Roll",
        "Wraps & Rolls",
    ),

    (
        (
            "pasta",
        ),
        "Pasta Street",
        "Pasta",
    ),
]


def add_product_columns():
    inspector = inspect(
        engine
    )

    existing_columns = {
        column["name"]
        for column
        in inspector.get_columns(
            "products"
        )
    }

    with engine.begin() as connection:

        if (
            "restaurant_id"
            not in existing_columns
        ):
            connection.execute(
                text(
                    "ALTER TABLE products "
                    "ADD COLUMN restaurant_id "
                    "INT NULL"
                )
            )

        if (
            "menu_category"
            not in existing_columns
        ):
            connection.execute(
                text(
                    "ALTER TABLE products "
                    "ADD COLUMN menu_category "
                    "VARCHAR(100) NULL"
                )
            )

        if (
            "is_bestseller"
            not in existing_columns
        ):
            connection.execute(
                text(
                    "ALTER TABLE products "
                    "ADD COLUMN is_bestseller "
                    "BOOLEAN NOT NULL "
                    "DEFAULT FALSE"
                )
            )

    inspector = inspect(
        engine
    )

    existing_indexes = {
        index["name"]
        for index
        in inspector.get_indexes(
            "products"
        )
        if index.get(
            "name"
        )
    }

    if (
        "ix_products_restaurant_id"
        not in existing_indexes
    ):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE INDEX "
                    "ix_products_restaurant_id "
                    "ON products "
                    "(restaurant_id)"
                )
            )

    inspector = inspect(
        engine
    )

    has_restaurant_foreign_key = any(
        "restaurant_id"
        in foreign_key.get(
            "constrained_columns",
            [],
        )
        for foreign_key
        in inspector.get_foreign_keys(
            "products"
        )
    )

    if not has_restaurant_foreign_key:

        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE products "
                    "ADD CONSTRAINT "
                    "fk_products_restaurant_id "
                    "FOREIGN KEY "
                    "(restaurant_id) "
                    "REFERENCES restaurants(id) "
                    "ON DELETE SET NULL"
                )
            )


def seed_restaurants(
    db: Session,
):
    restaurants_by_name = {
        restaurant.name:
            restaurant

        for restaurant
        in db.query(
            Restaurant
        ).all()
    }

    for restaurant_data in (
        STARTER_RESTAURANTS
    ):
        name = restaurant_data[
            "name"
        ]

        restaurant = (
            restaurants_by_name.get(
                name
            )
        )

        if restaurant is None:

            restaurant = Restaurant(
                **restaurant_data
            )

            db.add(
                restaurant
            )

            db.flush()

            restaurants_by_name[
                name
            ] = restaurant

    return restaurants_by_name


def get_restaurant_assignment(
    product_name: str,
):
    normalized_name = (
        product_name or ""
    ).strip().lower()

    for (
        keywords,
        restaurant_name,
        category,
    ) in PRODUCT_ASSIGNMENT_RULES:

        if any(
            keyword in normalized_name
            for keyword in keywords
        ):
            return (
                restaurant_name,
                category,
            )

    return (
        "City Kitchen",
        "Recommended",
    )


def assign_existing_swiggy_products(
    db: Session,
    restaurants_by_name: dict,
):
    products = (
        db.query(
            Product
        )
        .filter(
            Product.platform.ilike(
                "swiggy"
            )
        )
        .order_by(
            Product.id.asc()
        )
        .all()
    )

    updated_count = 0

    for product in products:

        if (
            product.restaurant_id
            is not None
        ):
            continue

        (
            restaurant_name,
            category,
        ) = get_restaurant_assignment(
            product.product_name
        )

        restaurant = (
            restaurants_by_name[
                restaurant_name
            ]
        )

        product.restaurant_id = (
            restaurant.id
        )

        if not (
            product.menu_category
            or ""
        ).strip():

            product.menu_category = (
                category
            )

        updated_count += 1

    return updated_count


def run_migration():
    if (
        engine.dialect.name
        !=
        "mysql"
    ):
        raise RuntimeError(
            "This migration is written "
            "for the project's MySQL database."
        )

    print(
        "Creating the restaurants table "
        "if needed..."
    )

    Restaurant.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    print(
        "Adding restaurant fields "
        "to products if needed..."
    )

    add_product_columns()

    with Session(
        bind=engine
    ) as db:

        try:
            restaurants_by_name = (
                seed_restaurants(
                    db
                )
            )

            updated_count = (
                assign_existing_swiggy_products(
                    db,
                    restaurants_by_name,
                )
            )

            db.commit()

        except Exception:
            db.rollback()
            raise

    print(
        "Restaurant migration "
        "completed successfully."
    )

    print(
        "Existing Swiggy products "
        f"assigned: {updated_count}"
    )

    print(
        "No cuisine restrictions were added; "
        "restaurant/category values remain "
        "flexible metadata."
    )


if __name__ == "__main__":
    run_migration()