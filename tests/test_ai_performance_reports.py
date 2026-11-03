"""Phase 12B.3: isolated read-only performance, roles and trend tests."""

import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai.performance_service import answer_performance_question  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture
def example():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Restaurant.__table__,
                MerchantRestaurant.__table__, SwiggyOrders.__table__],
    )
    db = Session(engine)
    admin = User(username="admin_perf", email="admin_perf@example.test", password_hash="x", role="admin")
    merchant = User(username="merchant_perf", email="merchant_perf@example.test", password_hash="x", role="merchant")
    client = User(username="client_perf", email="client_perf@example.test", password_hash="x", role="client")
    kfc = Restaurant(name="KFC")
    rival = Restaurant(name="Burger King")
    db.add_all([admin, merchant, client, kfc, rival])
    db.flush()
    db.add(MerchantRestaurant(user_id=merchant.id, restaurant_id=kfc.id))
    for order_num, place, status, amount, when in [
        ("m1", kfc, "completed", 100.25, date(2026, 11, 1)),
        ("m2", kfc, "COMPLETED", 200.00, date(2026, 11, 2)),
        ("m3", kfc, " pending ", 30.00, date(2026, 11, 2)),
        ("m4", kfc, "processing", 40.00, date(2026, 11, 3)),
        ("m5", kfc, "cancelled", 95.00, date(2026, 11, 3)),
        ("p1", kfc, "completed", 80.00, date(2026, 10, 1)),
        ("p2", kfc, "cancelled", 70.00, date(2026, 10, 2)),
        ("p3", kfc, "pending", 60.00, date(2026, 10, 3)),
        ("p4", kfc, "completed", 800.00, date(2026, 10, 31)),
        ("bad", rival, "completed", 9000.00, date(2026, 11, 2)),
        ("s1", kfc, "completed", 150.00, date(2026, 9, 1)),
        ("s2", kfc, "completed", 250.00, date(2026, 9, 15)),
        ("s3", kfc, "cancelled", 90.00, date(2026, 9, 30)),
        ("s4", kfc, "pending", 40.00, date(2026, 9, 18)),
        ("a1", kfc, "completed", 50.00, date(2026, 8, 20)),
        ("a2", kfc, "cancelled", 25.00, date(2026, 8, 21)),
    ]:
        db.add(SwiggyOrders(
            customer_name="sample", order_number=order_num, restaurant_id=place.id,
            status=status, amount=amount, order_date=when,
        ))
    db.commit()
    yield db, admin, merchant, client
    db.close()
    engine.dispose()


def report(db, user, question, today=date(2026, 11, 3)):
    return answer_performance_question(db=db, user=user, question=question, as_of=today)


def test_merchant_this_month_exact_metrics(example):
    db, _, merchant, _ = example
    result = report(db, merchant, "Show my restaurant performance this month")
    assert "KFC" in result
    assert "Total orders: 5" in result
    assert "Pending: 1; Processing: 1; Completed: 2; Cancelled: 1" in result
    assert "Completion rate: 40.0%" in result
    assert "Cancellation rate: 20.0%" in result
    assert "₹300.25" in result
    assert "9000" not in result


def test_mtd_comparison_matches_elapsed_days(example):
    db, admin, _, _ = example
    result = report(db, admin, "Compare KFC order performance this month vs last month")
    assert "Total orders: 5" in result
    assert "previous month's first 3 day(s)" in result
    assert "Total orders: 3" in result
    assert "₹80.00" in result
    assert "₹880.00" not in result  # Oct 31 must be excluded from aligned comparison
    assert "Completed-order revenue: +220.25 INR" in result
    assert "Cancellation-rate change: -13.3 percentage points" in result


def test_last_month_full_month_includes_oct_31(example):
    db, admin, _, _ = example
    result = report(db, admin, "Show KFC order performance last month")
    assert "last month (October 2026)" in result
    assert "Total orders: 4" in result
    assert "₹880.00" in result


def test_zero_orders_has_unavailable_rates(example):
    db, admin, _, _ = example
    result = report(db, admin, "Show KFC order performance today", today=date(2026, 12, 20))
    assert "Total orders: 0" in result
    assert "N/A (no orders)" in result
    assert "No orders in this period" in result


def test_merchant_cannot_read_rival(example):
    db, _, merchant, _ = example
    with pytest.raises(HTTPException) as error:
        report(db, merchant, "Compare Burger King order performance this month")
    assert error.value.status_code == 403


def test_merchant_cannot_read_unknown_named_target(example):
    db, _, merchant, _ = example
    with pytest.raises(HTTPException) as error:
        report(db, merchant, "Show Example Cafe performance this month")
    assert error.value.status_code == 403


def test_merchant_cannot_read_unknown_revenue_trend_target(example):
    db, _, merchant, _ = example
    with pytest.raises(HTTPException) as error:
        report(db, merchant, "Show Fictional Cafe revenue trends this month")
    assert error.value.status_code == 403


def test_admin_must_name_one_restaurant(example):
    db, admin, _, _ = example
    assert "name one existing restaurant" in report(db, admin, "Show restaurant performance")
    assert "name one existing restaurant" in report(db, admin, "Compare KFC and Burger King performance")


def test_client_denied(example):
    db, _, _, client = example
    with pytest.raises(HTTPException) as error:
        report(db, client, "Show KFC order performance")
    assert error.value.status_code == 403


def test_general_guidance_not_intercepted(example):
    db, admin, _, _ = example
    for question in [
        "How can I improve restaurant performance?",
        "How should I investigate high order cancellation rates?",
        "How do I check merchant performance?",
        "What are the four order statuses?",
        "How do I create a merchant account?",
        "Explain what cancellation rate means",
        "What is KFC revenue this month?",  # handled by existing revenue service
        "What is my name?",
    ]:
        assert report(db, admin, question) is None, question


def test_cancellation_trend_is_data_driven_not_a_causal_claim(example):
    db, _, merchant, _ = example
    result = report(db, merchant, "Why are cancelled orders increasing?")
    assert "Cancelled: 1" in result
    assert "previous month's first 3 day(s)" in result
    assert "does not establish why" in result
    assert "No records were modified" in result


def test_single_week_and_previous_week_comparison(example):
    db, admin, _, _ = example
    result = report(db, admin, "Compare KFC order trends this week vs last week")
    assert "this week through 2026-11-03" in result
    assert "previous week's matching 2 day(s)" in result


def test_read_only_select_statements(example):
    db, admin, _, _ = example
    statements = []
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().upper())
    event.listen(db.bind, "before_cursor_execute", record)
    try:
        report(db, admin, "Compare KFC order performance this month vs last month")
    finally:
        event.remove(db.bind, "before_cursor_execute", record)
    assert statements and all(s.startswith("SELECT") for s in statements)


def test_no_unrecognized_status_used_as_revenue(example):
    db, admin, _, _ = example
    db.add(SwiggyOrders(customer_name="unknown", order_number="odd", restaurant_id=1,
                        status="needs_review", amount=10000, order_date=date(2026, 11, 3)))
    db.commit()
    result = report(db, admin, "KFC order performance this month")
    assert "Other/unrecognized statuses: 1" in result
    assert "₹300.25" in result


def test_named_september_month_instead_of_november(example):
    db, _, merchant, _ = example
    answer = report(db, merchant, "Show my restaurant performance for September 2026")
    assert "September 2026" in answer
    assert "Total orders: 4" in answer
    assert "Completed: 2; Cancelled: 1" in answer
    assert "₹400.00" in answer
    assert "9000" not in answer


def test_named_month_comparison_merchant_does_not_look_like_restaurant(example):
    db, _, merchant, _ = example
    answer = report(db, merchant, "Compare September and August performance")
    assert "September 2026" in answer
    assert "August 2026" in answer
    assert "Total orders: 4" in answer
    assert "Total orders: 2" in answer
    assert "Completed-order revenue: +350.00 INR" in answer
    assert "Named-month comparisons use full calendar months." in answer
    assert "matched elapsed days" not in answer


def test_named_month_admin_and_merchant_scope(example):
    db, admin, merchant, client = example
    answer = report(db, admin, "Show KFC performance for September 2026")
    assert "Total orders: 4" in answer
    with pytest.raises(HTTPException) as error:
        report(db, merchant, "Show Burger King performance for September 2026")
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        report(db, client, "Show KFC performance for September 2026")
    assert error.value.status_code == 403


def test_named_month_no_year_finds_most_recent(example):
    db, _, merchant, _ = example
    answer = report(db, merchant, "Show my restaurant performance in September")
    assert "September 2026" in answer
    assert "Total orders: 4" in answer
