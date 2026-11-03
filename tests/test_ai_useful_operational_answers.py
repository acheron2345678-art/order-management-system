"""Phase 12H.3.1: keep performance/planning responses useful and grounded."""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service as svc  # noqa: E402


FACTS = {
    "total_orders": 6, "pending": 2, "completed": 4, "cancelled": 0,
    "historical_period": True, "orders_older_than_current_month": True,
    "inventory_now": {
        "active_products": 2, "out_of_stock_products": 0,
        "at_or_below_reorder_level": 0,
    },
}


@pytest.mark.parametrize("question, expected_focus", [
    ("What should I focus on next month?", "planning"),
    ("Is my restaurant functioning well?", "restaurant_health"),
    ("Compare my sales and inventory situation.", "sales_inventory"),
])
def test_useful_questions_get_narrow_grounding_flags(question, expected_focus):
    assert svc._question_focus(question) == expected_focus
    flags = svc._relevant_report_flags(question, FACTS)
    assert flags["orders_recorded"] is True
    assert flags["completed_orders_recorded"] is True
    assert flags["pending_statuses_recorded"] is True
    assert flags["any_products_at_or_below_reorder_now"] is False
    assert "historical_stock_data_unavailable" not in flags
    assert "future_demand_and_capacity_unavailable" not in flags
    assert all(type(v) is bool for v in flags.values())


def test_planning_prompt_prioritizes_recorded_pending_not_completed():
    prompt = svc._interpretation_focus("What should I focus on next month?", FACTS)
    assert "orders recorded as pending" in prompt
    assert "do not prioritize completed orders" in prompt.lower()
    assert "No demand forecast is available" in prompt


def test_health_prompt_allows_partial_assessment_without_stock_history():
    prompt = svc._interpretation_focus("Is my restaurant functioning well?", FACTS)
    assert "LIMITED operational snapshot" in prompt
    assert "not a blanket 'cannot assess' refusal" in prompt
    assert "Historical inventory data" in prompt


def test_comparison_prompt_requests_actual_comparison():
    prompt = svc._interpretation_focus("Compare my sales and inventory situation.", FACTS)
    assert "Actually COMPARE" in prompt
    assert "different-time" in prompt
    assert "paid sales" in prompt


def test_generation_uses_safe_flags_without_numbers_or_extra_model_calls(monkeypatch):
    sent = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": (
                "The recorded orders show completed and pending outcomes, while "
                "current inventory has no products flagged at their reorder "
                "thresholds. Review pending records first; these snapshots "
                "cannot establish future capacity."
            )}}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            sent.append(json)
            return Response()

    monkeypatch.setattr(svc.httpx, "AsyncClient", Client)
    answer = asyncio.run(svc._generate_interpretation(
        "Compare my sales and inventory situation.",
        {**FACTS, "response_style": "brief_followup"},
    ))
    assert "recorded orders" in answer
    assert len(sent) == 1
    contents = "\n".join(message["content"] for message in sent[0]["messages"])
    assert "Actually COMPARE" in contents
    assert '"historical_stock_data_unavailable"' not in contents
    assert '"completed_orders_recorded": true' in contents
    assert "₹994" not in contents
