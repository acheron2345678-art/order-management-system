"""Read-only AI inventory reporting tests. SQLite only; no production DB."""

import os

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai.inventory_service import answer_inventory_question  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.products.models import Product, Restaurant  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture
def seeded():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__, Restaurant.__table__, Product.__table__,
            MerchantRestaurant.__table__,
        ],
    )
    db = Session(engine)
    admin = User(username="a", email="a@example.test", password_hash="x", role="admin")
    merchant = User(username="m", email="m@example.test", password_hash="x", role="merchant")
    client = User(username="c", email="c@example.test", password_hash="x", role="client")
    kfc, rival = Restaurant(name="KFC"), Restaurant(name="Burger King")
    db.add_all([admin, merchant, client, kfc, rival]); db.flush()
    db.add(MerchantRestaurant(user_id=merchant.id, restaurant_id=kfc.id))

    def item(name, stock, reorder, restaurant=kfc, active=True, platform="swiggy"):
        db.add(Product(
            product_name=name, price=100, platform=platform,
            restaurant_id=restaurant.id, stock_quantity=stock,
            reorder_level=reorder, is_active=active,
        ))

    item("Zinger", 0, 4)
    item("Burger", 3, 5)
    item("Fries", 20, 5)
    item("Inactive Dish", 0, 5, active=False)
    item("Insights product", 0, 5, platform="insights")
    item("Rival product", 0, 5, restaurant=rival)
    db.commit()
    yield db, admin, merchant, client
    db.close()
    engine.dispose()


def ask(db, user, prompt):
    return answer_inventory_question(db=db, user=user, question=prompt)


def test_merchant_gets_own_low_stock(seeded):
    db, _, merchant, _ = seeded
    output = ask(db, merchant, "Which items should I restock?")
    assert "Verified inventory for KFC" in output
    assert "Out of stock: 1; Low stock: 1; Above reorder level: 1" in output
    assert "Zinger" in output and "Burger" in output
    assert output.index("Zinger") < output.index("Burger")
    assert "5 unit(s)" in output  # zero stock, reorder 4, reach 5
    assert "3 unit(s)" in output  # 3 stock, reorder 5, reach 6
    assert "Rival product" not in output
    assert "Inactive Dish" not in output
    assert "Insights product" not in output


def test_admin_can_query_named_restaurant(seeded):
    db, admin, _, _ = seeded
    output = ask(db, admin, "Give me KFC inventory summary")
    assert "KFC" in output and "Products: 3" in output
    output = ask(db, admin, "Show Burger King out of stock products")
    assert "Rival product" in output and "Zinger" not in output


def test_admin_needs_unambiguous_restaurant(seeded):
    db, admin, _, _ = seeded
    assert "name one restaurant" in ask(db, admin, "Show inventory summary")
    assert "name one restaurant" in ask(db, admin, "Compare KFC and Burger King stock levels")


def test_merchant_cannot_view_other_restaurant(seeded):
    db, _, merchant, _ = seeded
    with pytest.raises(HTTPException) as exc:
        ask(db, merchant, "Show Burger King low stock items")
    assert exc.value.status_code == 403


def test_clients_cannot_read_inventory(seeded):
    db, _, _, client = seeded
    with pytest.raises(HTTPException) as exc:
        ask(db, client, "Show KFC inventory summary")
    assert exc.value.status_code == 403


def test_general_guidance_not_intercepted(seeded):
    db, admin, _, _ = seeded
    assert ask(db, admin, "How do I restock an item?") is None
    assert ask(db, admin, "Give me five inventory management tips") is None
    assert ask(db, admin, "How can I improve inventory?") is None
    assert ask(db, admin, "What is KFC revenue?") is None


def test_select_only(seeded):
    db, admin, _, _ = seeded
    commands = []
    def capture(conn, cursor, statement, params, context, executemany):
        commands.append(statement.strip().upper())
    event.listen(db.bind, "before_cursor_execute", capture)
    ask(db, admin, "KFC low stock items")
    event.remove(db.bind, "before_cursor_execute", capture)
    assert commands and all(c.startswith("SELECT") for c in commands)


def test_merchant_can_view_individual_stock_quantities(seeded):
    db, _, merchant, _ = seeded
    result = ask(db, merchant, "no. of quantity in each product?")
    assert "Current stock quantity by product" in result
    assert "Zinger" in result and "0 unit(s) available" in result
    assert "Burger" in result and "3 unit(s) available" in result
    assert "Fries" in result and "20 unit(s) available" in result
    assert "Total units: 23" in result
    assert "Inactive Dish" not in result
    assert "Rival product" not in result


def test_merchant_can_request_itemized_stock_in_other_phrasings(seeded):
    db, _, merchant, _ = seeded
    for question in (
        "What is the quantity for each product?",
        "Show stock quantity of every product",
        "Show my stock of each product",
    ):
        result = ask(db, merchant, question)
        assert "Fries" in result and "20 unit(s) available" in result


def test_unknown_named_restaurant_is_denied_instead_of_silent_fallback(seeded):
    db, _, merchant, _ = seeded
    # The seeded DB has no City Kitchen. A named foreign target must still be denied.
    for question in (
        "Show City Kitchen low stock items",
        "Show City Kitchen inventory summary",
        "Show stock of City Kitchen",
        "Show low stock items of City Kitchen",
        "How many products are in City Kitchen inventory?",
    ):
        with pytest.raises(HTTPException) as exc:
            ask(db, merchant, question)
        assert exc.value.status_code == 403, question


def test_unqualified_inventory_requests_still_use_owned_restaurant(seeded):
    db, _, merchant, _ = seeded
    for question in (
        "Show low stock items",
        "Show my inventory summary",
        "Show stock of all products",
        "Show KFC inventory summary",
        "What is KFC inventory level?",
    ):
        result = ask(db, merchant, question)
        assert "Verified inventory for KFC" in result, question


def test_admin_itemized_quantities_need_restaurant_name(seeded):
    db, admin, _, _ = seeded
    unnamed = ask(db, admin, "no. of quantity in each product?")
    assert "name one restaurant" in unnamed
    itemized = ask(db, admin, "Show KFC stock quantity of each product")
    assert "Fries" in itemized and "20 unit(s) available" in itemized
    assert "Rival product" not in itemized


def test_itemized_inventory_uses_only_select_queries(seeded):
    db, _, merchant, _ = seeded
    statements = []

    def capture(conn, cursor, statement, params, context, executemany):
        statements.append(statement.strip().upper())

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        answer = ask(db, merchant, "no. of quantity in each product?")
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert "Zinger" in answer
    assert statements and all(sql.startswith("SELECT") for sql in statements)
