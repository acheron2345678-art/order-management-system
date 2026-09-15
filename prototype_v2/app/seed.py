from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import MenuItem, Merchant, Store, User, UserRole


DEMO_ITEMS = [
    ("Margherita Pizza", "Stone-baked tomato, basil and mozzarella", "Pizza", "329.00", "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=700&q=80"),
    ("Truffle Mushroom Pizza", "Mushroom, truffle cream and parmesan", "Pizza", "449.00", "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=700&q=80"),
    ("Crispy Chicken Burger", "Crispy chicken, lettuce and house sauce", "Burgers", "289.00", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=700&q=80"),
    ("Grilled Veggie Burger", "Grilled vegetables, cheese and relish", "Burgers", "249.00", "https://images.unsplash.com/photo-1520072959219-c595dc870360?auto=format&fit=crop&w=700&q=80"),
    ("Creamy Mushroom Pasta", "Penne with mushroom cream sauce", "Mains", "359.00", "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=700&q=80"),
    ("Herb Grilled Chicken", "Grilled chicken, greens and herb butter", "Mains", "429.00", "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=700&q=80"),
    ("Avocado Toast", "Sourdough, avocado, chilli and lemon", "Breakfast", "275.00", "https://images.unsplash.com/photo-1541519227354-08fa5d50c44d?auto=format&fit=crop&w=700&q=80"),
    ("Eggs Benedict", "Poached eggs, hollandaise and toasted muffin", "Breakfast", "315.00", "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&w=700&q=80"),
    ("Garden Salad", "Leafy greens, cucumber, tomato and vinaigrette", "Salads", "229.00", "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=700&q=80"),
    ("Tiramisu", "Coffee-soaked sponge and mascarpone", "Desserts", "245.00", "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=700&q=80"),
    ("Berry Cheesecake", "Baked cheesecake with mixed berries", "Desserts", "265.00", "https://images.unsplash.com/photo-1565958011703-44f9829ba187?auto=format&fit=crop&w=700&q=80"),
    ("Cold Brew", "Slow-steeped coffee over ice", "Drinks", "165.00", "https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=700&q=80"),
]


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(Store.id).limit(1)):
        return

    merchant_user = User(
        email="merchant@example.com",
        full_name="Demo Merchant",
        password_hash="prototype-only",
        role=UserRole.MERCHANT,
    )
    customer = User(
        email="customer@example.com",
        full_name="Demo Customer",
        password_hash="prototype-only",
        role=UserRole.CUSTOMER,
    )
    db.add_all([merchant_user, customer])
    db.flush()

    merchant = Merchant(
        user_id=merchant_user.id,
        business_name="Nova Kitchen Group",
        support_email="hello@novakitchen.test",
    )
    db.add(merchant)
    db.flush()

    store = Store(
        merchant_id=merchant.id,
        name="Nova Kitchen",
        slug="nova-kitchen",
        description="Modern comfort food, bowls, pizzas and cafe favourites.",
        currency="INR",
        is_open=True,
    )
    db.add(store)
    db.flush()

    for name, description, category, price, image_url in DEMO_ITEMS:
        db.add(
            MenuItem(
                store_id=store.id,
                name=name,
                description=description,
                category=category,
                price=Decimal(price),
                image_url=image_url,
                is_available=True,
            )
        )
    db.commit()


def seed_if_empty() -> None:
    with SessionLocal() as db:
        seed_demo_data(db)
