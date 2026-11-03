"""Phase 12G.1: prevent misleading stock and temporal claims in grounded AI."""
import asyncio
import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant, Product  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.mark.parametrize("answer", [
    "Your recent data shows six orders with a two-thirds completion rate.",
    "Current stock levels are low at just twenty-eight units.",
    "Stock is sufficient to handle more orders.",
    "Inventory levels are adequate.",
])
def test_rejects_unsupported_numeric_or_inventory_judgments(answer):
    with pytest.raises(ValueError):
        analysis_service._validate_interpretation(answer)


@pytest.mark.parametrize("answer", [
    "The orders currently marked as pending need immediate delivery.",
    "Orders still pending should be sent out right now.",
    "Pending orders remain unfulfilled today.",
])
def test_cannot_present_old_pending_status_as_active(answer):
    with pytest.raises(ValueError):
        analysis_service._validate_interpretation(answer, {"historical_period": True})


def test_old_all_time_data_is_not_recent():
    with pytest.raises(ValueError):
        analysis_service._validate_interpretation(
            "Your recent data looks promising.",
            {"orders_older_than_current_month": True},
        )


def test_legitimate_uncertain_explanation_allowed():
    answer = (
        "Some orders are recorded as pending. None of the current products "
        "are at or below reorder thresholds, but that does not predict demand."
    )
    assert analysis_service._validate_interpretation(
        answer, {"historical_period": True, "orders_older_than_current_month": True},
    ) == answer


@pytest.mark.parametrize("latest,expected_historical", [
    (date(2026, 9, 7), True),
    (date(2026, 11, 3), False),
])
def test_all_time_uses_actual_latest_order_date(monkeypatch, latest, expected_historical):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    with Session(engine) as db:
        user = User(username="merchant", email="merchant@example.test", password_hash="x", role="merchant")
        restaurant = Restaurant(name="City Kitchen")
        other = Restaurant(name="Other Restaurant")
        db.add_all([user, restaurant, other]); db.flush()
        db.add_all([
            MerchantRestaurant(user_id=user.id, restaurant_id=restaurant.id),
            SwiggyOrders(order_number="owned", customer_name="Private", status="pending",
                         order_date=latest, amount=100, restaurant_id=restaurant.id),
            SwiggyOrders(order_number="not-owned", customer_name="Private", status="completed",
                         order_date=date(2026, 11, 3), amount=999999, restaurant_id=other.id),
        ])
        db.commit()
        captured = []
        async def fake_model(question, facts):
            captured.append(facts)
            return "Review the recorded order status before inferring a cause."
        monkeypatch.setattr(analysis_service, "_generate_interpretation", fake_model)
        result = asyncio.run(analysis_service.answer_analysis_question(
            db=db, user=user, question="Is my restaurant functioning well?",
            as_of=date(2026, 11, 3),
        ))
        assert result is not None
        assert captured[0]["total_orders"] == 1
        assert captured[0]["historical_period"] is expected_historical
        assert captured[0]["orders_older_than_current_month"] is expected_historical
        assert captured[0]["latest_recorded_order_month"] == latest.strftime("%B %Y")
        assert "999999" not in result[0]
        if expected_historical:
            assert "Most recent recorded order month: September 2026" in result[0]
        else:
            assert "Most recent recorded order month" not in result[0]
    engine.dispose()


def test_one_next_step_is_not_an_invented_metric():
    answer = "One useful next step is reviewing recorded order statuses."
    assert analysis_service._validate_interpretation(answer) == answer


def test_model_retries_when_inventory_claim_is_unverified(monkeypatch):
    calls = []

    class Response:
        def __init__(self, content):
            self.content = content
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": self.content}}

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json):
            calls.append(json)
            return Response(
                "Inventory is low at just twenty-eight units."
                if len(calls) == 1 else
                "These current stock totals cannot establish whether future orders can be fulfilled."
            )

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", Client)
    result = asyncio.run(analysis_service._generate_interpretation(
        "Can I handle more orders?",
        {"total_orders": 6, "inventory_now": {"current_total_stock_units": 28}},
    ))
    assert "cannot establish" in result
    assert len(calls) == 2
    assert calls[1]["messages"][-1]["role"] == "system"
    assert "QUALITATIVE_REPORT_FLAGS" in calls[1]["messages"][2]["content"]


@pytest.mark.parametrize("answer", [
    "These historical records are no longer active today.",
    "Those pending orders have been resolved.",
    "The old entries are already completed.",
])
def test_historical_statuses_must_not_be_declared_resolved(answer):
    with pytest.raises(ValueError, match="definitely resolved"):
        analysis_service._validate_interpretation(answer, {"historical_period": True})


def test_uncertainty_about_historical_resolution_is_allowed():
    answer = "The records might have been resolved; verify their status history."
    assert analysis_service._validate_interpretation(
        answer, {"historical_period": True}
    ) == answer


def test_sales_inventory_comparison_fallback_is_specific_and_safe():
    facts = {
        "completed": 4,
        "pending": 2,
        "inventory_now": {"active_products": 2, "at_or_below_reorder_level": 0},
    }
    result = analysis_service._verified_fallback(
        "Compare my sales and inventory situation", facts
    )
    assert "completed orders" in result
    assert "No active Swiggy products" in result
    assert "cannot establish earlier shortages" in result
    assert "low at" not in result


def test_sales_inventory_comparison_fallback_without_stock():
    facts = {
        "completed": 0,
        "pending": 0,
        "inventory_now": {"active_products": 0, "at_or_below_reorder_level": 0},
    }
    result = analysis_service._verified_fallback(
        "Compare my sales and stock situation", facts
    )
    assert "no active swiggy products" in result.casefold()
