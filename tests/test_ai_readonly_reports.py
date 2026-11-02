"""Phase 12B read-only data/role tests (uses SQLite, never production MySQL)."""

import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai.data_service import answer_data_question  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Product, Restaurant  # noqa: E402
from app.users.models import User  # noqa: E402
from app.users.profile_models import ClientProfile  # noqa: E402, F401


@pytest.fixture
def example():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__, Restaurant.__table__, Product.__table__,
            MerchantRestaurant.__table__, SwiggyOrders.__table__,
        ],
    )
    session = Session(engine)
    admin = User(username="admin", email="admin@example.test", password_hash="x", role="admin")
    merchant = User(username="merchant", email="merchant@example.test", password_hash="x", role="merchant")
    client = User(username="client", email="client@example.test", password_hash="x", role="client")
    kfc = Restaurant(name="KFC")
    rival = Restaurant(name="Burger King")
    session.add_all([admin, merchant, client, kfc, rival])
    session.flush()
    session.add(MerchantRestaurant(user_id=merchant.id, restaurant_id=kfc.id))
    for name, restaurant, status, amount, order_date in [
        ("k1", kfc, "completed", 100.25, date(2026, 11, 1)),
        ("k2", kfc, "completed", 200.00, date(2026, 11, 2)),
        ("k3", kfc, "pending", 80.00, date(2026, 11, 2)),
        ("k4", kfc, "cancelled", 90.00, date(2026, 10, 20)),
        ("b1", rival, "completed", 9000.00, date(2026, 11, 2)),
    ]:
        session.add(SwiggyOrders(
            customer_name="test", order_number=name, amount=amount,
            order_date=order_date, status=status, restaurant_id=restaurant.id,
        ))
    session.commit()
    yield session, admin, merchant, client
    session.close()
    engine.dispose()


def report(db, user, text):
    return answer_data_question(db=db, user=user, question=text, as_of=date(2026, 11, 2))


def test_admin_restaurant_monthly_summary(example):
    db, admin, _, _ = example
    result = report(db, admin, "What is KFC revenue this month?")
    assert "KFC" in result
    assert "₹300.25" in result
    assert "Total recorded orders: 3" in result
    assert "Pending: 1" in result
    assert "9000" not in result


def test_month_boundary_and_merchant_scope(example):
    db, _, merchant, _ = example
    result = report(db, merchant, "What is my restaurant revenue last month?")
    assert "KFC" in result
    assert "₹0.00" in result
    assert "Cancelled: 1" in result
    assert "Total recorded orders: 1" in result


def test_merchant_cannot_query_another_restaurant(example):
    db, _, merchant, _ = example
    with pytest.raises(HTTPException) as error:
        report(db, merchant, "What is Burger King's revenue?")
    assert error.value.status_code == 403


def test_clients_cannot_get_restaurant_revenue(example):
    db, _, _, client = example
    with pytest.raises(HTTPException) as error:
        report(db, client, "What is KFC revenue this month?")
    assert error.value.status_code == 403


def test_admin_must_specify_one_restaurant(example):
    db, admin, _, _ = example
    assert "name one restaurant" in report(db, admin, "Show total revenue")
    assert "name one restaurant" in report(db, admin, "Compare KFC and Burger King revenue")


def test_general_guidance_not_intercepted(example):
    db, admin, _, _ = example
    assert report(db, admin, "How can I improve restaurant revenue?") is None
    assert report(db, admin, "How do I create a merchant account?") is None
    assert report(db, admin, "What are the four order statuses?") is None


def test_report_uses_select_only(example):
    db, admin, _, _ = example
    statements = []
    def capture(conn, cursor, statement, params, context, executemany):
        statements.append(statement.strip().upper())
    event.listen(db.bind, "before_cursor_execute", capture)
    report(db, admin, "KFC revenue this month")
    event.remove(db.bind, "before_cursor_execute", capture)
    assert statements and all(s.startswith("SELECT") for s in statements)
