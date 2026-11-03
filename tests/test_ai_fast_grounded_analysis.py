"""Phase 12H.2: one short safe inference when valid, bounded retry otherwise."""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service  # noqa: E402


class FakeResponse:
    def __init__(self, answer: str):
        self.answer = answer

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self.answer}}


def fake_http(monkeypatch, replies: list[str]):
    requests: list[dict] = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, _url, json):
            requests.append(json)
            return FakeResponse(replies[len(requests) - 1])

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeClient)
    return requests


FACTS = {
    "restaurant": "City Kitchen",
    "total_orders": 6,
    "pending": 2,
    "completed": 4,
    "cancelled": 0,
    "completed_order_amount_inr": "994.00",
    "historical_period": True,
    "orders_older_than_current_month": True,
    "latest_recorded_order_month": "September 2026",
    "inventory_now": {
        "active_products": 2,
        "current_total_stock_units": 28,
        "out_of_stock_products": 0,
        "at_or_below_reorder_level": 0,
    },
}


def test_no_raw_counts_dates_or_restaurant_reach_model_in_first_request(monkeypatch):
    requests = fake_http(monkeypatch, [
        "Recorded order statuses do not establish the cause of delays. "
        "Review the available status history before making changes."
    ])
    answer = asyncio.run(analysis_service._generate_interpretation(
        "Do I have enough stock to handle more orders?", FACTS,
    ))
    assert "status history" in answer
    assert len(requests) == 1
    payload = requests[0]
    model_context = " ".join(msg["content"] for msg in payload["messages"][:-1])
    assert "QUALITATIVE_REPORT_FLAGS" in model_context
    # The stock question needs *inventory* flags, not unrelated order status
    # context that used to make Qwen drift into historical-order discussion.
    assert '"pending_statuses_recorded"' not in model_context
    assert '"latest_order_precedes_current_month"' not in model_context
    assert '"any_products_at_or_below_reorder_now": false' in model_context
    for forbidden in ("City Kitchen", "994.00", "September 2026", '"total_orders": 6', '"current_total_stock_units": 28'):
        assert forbidden not in model_context
    assert payload["options"]["num_predict"] <= 128
    assert payload["stream"] is False and payload["think"] is False


def test_first_valid_reply_is_not_regenerated(monkeypatch):
    requests = fake_http(monkeypatch, [
        "The records show a mix of outcomes, but do not identify any specific "
        "operational cause. Review the authorized order details first."
    ])
    asyncio.run(analysis_service._generate_interpretation(
        "What are the biggest operational problems?", FACTS,
    ))
    assert len(requests) == 1


def test_short_followup_has_smaller_generation_limit(monkeypatch):
    requests = fake_http(monkeypatch, [
        "Review recorded pending statuses in the authorized order list."
    ])
    asyncio.run(analysis_service._generate_interpretation(
        "What should I do first?", {**FACTS, "response_style": "brief_followup"},
    ))
    assert len(requests) == 1
    assert requests[0]["options"]["num_predict"] <= 100


def test_numeric_failure_gets_only_one_corrective_retry(monkeypatch):
    requests = fake_http(monkeypatch, [
        "There were 6 orders and ₹994 in revenue.",
        "The recorded order statuses require investigation. "
        "Check available order details before inferring a cause.",
    ])
    answer = asyncio.run(analysis_service._generate_interpretation(
        "How is my restaurant doing?", FACTS,
    ))
    assert "require investigation" in answer
    assert len(requests) == 2
    retry_context = str(requests[1]["messages"])
    assert "Do not include any digits" in retry_context
    assert '"total_orders": 6' not in retry_context
    assert "994.00" not in retry_context


def test_rejected_recent_history_never_reaches_user(monkeypatch):
    requests = fake_http(monkeypatch, [
        "Recent orders are still pending today.",
        "Recently the orders have been delayed.",
    ])
    with pytest.raises(analysis_service.AIInterpretationRejected):
        asyncio.run(analysis_service._generate_interpretation(
            "Which orders should I investigate first?", FACTS,
        ))
    assert len(requests) == 2
    assert "recorded orders" in requests[1]["messages"][-1]["content"]


def test_boolean_flags_include_no_stock_when_none(monkeypatch):
    flags = analysis_service._qualitative_report_flags({
        "total_orders": 0,
        "inventory_now": {"active_products": 0},
    })
    assert not flags["orders_recorded"]
    assert not flags["products_in_current_inventory"]
    assert flags["future_demand_and_capacity_unavailable"]
    assert all(type(value) is bool for value in flags.values())


def test_existing_validation_not_relaxed():
    for unsafe in (
        "Inventory levels are adequate.",
        "Current stock is sufficient for more orders.",
        "There were 6 orders.",
        "Two orders remain pending today.",
        "Your recent data looks promising.",
        "Those old orders are definitely resolved.",
    ):
        with pytest.raises(ValueError):
            analysis_service._validate_interpretation(
                unsafe, {"historical_period": True, "orders_older_than_current_month": True}
            )
