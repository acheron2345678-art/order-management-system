"""Phase 12H.3: question-relevant context, shorter answers, unchanged security."""
from __future__ import annotations

import asyncio
import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service as svc, conversation  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Product, Restaurant  # noqa: E402
from app.users.models import User  # noqa: E402


FACTS = {
    "total_orders": 6, "pending": 2, "completed": 4, "cancelled": 0,
    "historical_period": True, "orders_older_than_current_month": True,
    "inventory_now": {
        "active_products": 2, "out_of_stock_products": 0,
        "at_or_below_reorder_level": 0,
    },
}


@pytest.mark.parametrize("question, expected", [
    ("Which orders should I investigate first?", "order_priority"),
    ("Do I have enough stock to handle more orders?", "stock_capacity"),
    ("Compare my sales and inventory situation.", "sales_inventory"),
    ("What could explain the pending orders?", "order_cause"),
    ("What should I focus on next month?", "planning"),
    ("Is my restaurant functioning well?", "restaurant_health"),
])
def test_focus_is_about_presentation_not_report_scope(question, expected):
    assert svc._question_focus(question) == expected


def test_order_priority_does_not_pass_stock_or_demand_flags_to_model():
    flags = svc._relevant_report_flags("Which orders should I investigate first?", FACTS)
    assert flags["pending_statuses_recorded"] is True
    assert flags["historical_order_period"] is True
    assert "products_in_current_inventory" not in flags
    assert "future_demand_and_capacity_unavailable" not in flags
    assert all(type(value) is bool for value in flags.values())


def test_stock_capacity_does_not_pass_unrelated_order_flags_to_model():
    flags = svc._relevant_report_flags("Do I have enough stock to handle more orders?", FACTS)
    assert flags["any_products_at_or_below_reorder_now"] is False
    assert flags["future_demand_and_capacity_unavailable"] is True
    assert "pending_statuses_recorded" not in flags
    assert "completed_orders_recorded" not in flags


def test_cross_domain_comparison_still_gets_both_relevant_flag_groups():
    flags = svc._relevant_report_flags("Compare my sales and inventory situation", FACTS)
    assert flags["completed_orders_recorded"]
    assert flags["pending_statuses_recorded"]
    assert "any_products_at_or_below_reorder_now" in flags


def test_detail_overrides_first_turn_conciseness():
    assert svc.is_focused_analysis_question("Which orders should I investigate first?")
    assert not svc.is_focused_analysis_question(
        "Which orders should I investigate first? Explain in detail."
    )
    assert svc._requests_detailed_answer("Please provide a comprehensive explanation")


def test_short_generation_budget_and_subject_specific_prompt(monkeypatch):
    requests = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "Review the orders recorded as pending and confirm their status history."}}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            requests.append(json)
            return Response()

    monkeypatch.setattr(svc.httpx, "AsyncClient", Client)
    asyncio.run(svc._generate_interpretation(
        "Which orders should I investigate first?", {**FACTS, "response_style": "brief_followup"},
    ))
    assert len(requests) == 1
    req = requests[0]
    assert req["options"]["num_predict"] == 92
    context = "\n".join(m["content"] for m in req["messages"][:-1])
    assert '"pending_statuses_recorded": true' in context
    assert '"products_in_current_inventory"' not in context
    assert "do not discuss inventory" in context.lower()
    assert "994.00" not in context


def test_detailed_generation_budget_is_available_when_requested(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "Review the authorized order details and available history before assigning priority."}}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            calls.append(json)
            return Response()

    monkeypatch.setattr(svc.httpx, "AsyncClient", Client)
    asyncio.run(svc._generate_interpretation(
        "Which orders should I investigate first? Explain in detail.",
        {**FACTS, "response_style": "standard"},
    ))
    assert calls[0]["options"]["num_predict"] == 180
    assert "detailed explanation" in calls[0]["messages"][1]["content"]


@pytest.fixture
def merchant_case(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    with Session(engine) as db:
        owner = User(username="owner", email="owner@example.test", role="merchant", password_hash="x")
        other = User(username="other", email="other@example.test", role="merchant", password_hash="x")
        city = Restaurant(name="City Kitchen")
        kfc = Restaurant(name="KFC")
        db.add_all([owner, other, city, kfc])
        db.flush()
        db.add_all([
            MerchantRestaurant(user_id=owner.id, restaurant_id=city.id),
            MerchantRestaurant(user_id=other.id, restaurant_id=kfc.id),
            SwiggyOrders(order_number="c1", customer_name="Private", amount=300,
                         status="completed", order_date=date(2026, 9, 3), restaurant_id=city.id),
            SwiggyOrders(order_number="p1", customer_name="Private", amount=100,
                         status="pending", order_date=date(2026, 9, 4), restaurant_id=city.id),
            SwiggyOrders(order_number="k1", customer_name="Other", amount=90000,
                         status="completed", order_date=date(2026, 9, 4), restaurant_id=kfc.id),
            Product(product_name="Soda", platform="swiggy", stock_quantity=7,
                    reorder_level=5, restaurant_id=city.id, is_active=True, price=25),
        ])
        db.commit()
        seen = []

        async def model(question, facts):
            seen.append((question, facts.copy()))
            return "Review the relevant authorized records before making an operational decision."

        monkeypatch.setattr(svc, "_generate_interpretation", model)
        yield db, owner, seen
    engine.dispose()


def ask(db, owner, q, token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=owner, question=q, history=[],
        context_token=token, as_of=date(2026, 11, 3),
    ))


def test_first_turn_order_priority_is_short_and_not_about_revenue(merchant_case):
    db, owner, seen = merchant_case
    answer, token = ask(db, owner, "Which orders should I investigate first?")
    assert seen[-1][1]["response_style"] == "brief_followup"
    assert "Orders: 2; Pending: 1 recorded; Completed: 1" in answer
    assert "₹300.00" not in answer
    assert "Current active Swiggy products" not in answer
    assert conversation.read_context(token, owner).kind == "analysis"


def test_first_turn_capacity_reports_only_current_inventory_flags(merchant_case):
    db, owner, seen = merchant_case
    answer, _ = ask(db, owner, "Do I have enough stock to handle more orders?")
    assert seen[-1][1]["response_style"] == "brief_followup"
    assert "Current active Swiggy products: 1" in answer
    assert "out of stock: 0" in answer
    assert "Orders:" not in answer
    assert "historical status records" not in answer
    assert "₹300.00" not in answer


def test_first_turn_planning_is_brief_and_verified(merchant_case):
    db, owner, seen = merchant_case
    answer, _ = ask(db, owner, "What should I focus on next month?")
    assert seen[-1][1]["response_style"] == "brief_followup"
    assert "Orders: 2; Pending: 1 recorded" in answer
    assert "products at/below reorder now: 0" in answer
    assert "₹300.00" not in answer


def test_broad_assessment_keeps_complete_verified_report(merchant_case):
    db, owner, seen = merchant_case
    answer, _ = ask(db, owner, "Is my restaurant functioning well?")
    assert seen[-1][1]["response_style"] == "standard"
    assert "**Verified figures" in answer
    assert "Completed-order value: ₹300.00" in answer


def test_other_merchant_stays_forbidden_for_narrow_questions(merchant_case):
    db, owner, seen = merchant_case
    with pytest.raises(HTTPException) as exc:
        ask(db, owner, "Which KFC orders should I investigate first?")
    assert exc.value.status_code == 403
    assert not seen


def test_stock_fallback_uses_inventory_not_unrelated_pending_statuses():
    fallback = svc._verified_fallback("Do I have enough stock to handle more orders?", FACTS)
    assert "out of stock" in fallback
    assert "order quantities" in fallback or "items and quantities" in fallback
    assert "pending status" not in fallback
