"""Phase 12H.2.1 regression tests from live RTX 5050 responses."""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service as svc  # noqa: E402


FACTS = {
    "total_orders": 6,
    "pending": 2,
    "completed": 4,
    "cancelled": 0,
    "historical_period": True,
    "orders_older_than_current_month": True,
    "inventory_now": {
        "active_products": 2,
        "out_of_stock_products": 0,
        "at_or_below_reorder_level": 0,
    },
}


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self.content}}


def simulate(monkeypatch, replies):
    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            calls.append(json)
            return FakeResponse(replies[len(calls) - 1])

    monkeypatch.setattr(svc.httpx, "AsyncClient", Client)
    return calls


def test_priority_question_supplies_safe_focus_and_needs_one_call(monkeypatch):
    calls = simulate(monkeypatch, [
        "Start with orders recorded as pending. Verify their history without "
        "assuming they remain active today."
    ])
    result = asyncio.run(svc._generate_interpretation(
        "Which orders should I investigate first?", FACTS
    ))
    assert "recorded as pending" in result
    assert len(calls) == 1
    prompt = " ".join(p["content"] for p in calls[0]["messages"][:-1])
    assert "before routine checks of completed orders" in prompt
    assert '"pending_statuses_recorded": true' in prompt
    assert "994" not in prompt and "September 2026" not in prompt


def test_completed_first_priority_answer_rejected_and_corrected(monkeypatch):
    calls = simulate(monkeypatch, [
        "Investigate the recorded completed orders to verify their historical "
        "status since pending records exist.",
        "Review orders recorded as pending first, then verify their available "
        "status history before deciding what needs attention.",
    ])
    result = asyncio.run(svc._generate_interpretation(
        "Which orders should I investigate first?", FACTS
    ))
    assert "recorded as pending first" in result
    assert len(calls) == 2
    assert "prioritized completed orders" in calls[1]["messages"][-1]["content"]


def test_investigation_fallback_is_not_completed_first():
    result = svc._verified_fallback("Which orders should I investigate first?", FACTS)
    assert "orders recorded as pending" in result
    assert "current delay" in result


def test_stock_capacity_focus_distinguishes_current_from_historical(monkeypatch):
    calls = simulate(monkeypatch, [
        "No products are flagged out of stock now, but additional fulfillment "
        "capacity depends on item-level demand and order requirements."
    ])
    result = asyncio.run(svc._generate_interpretation(
        "Do I have enough stock to handle more orders?", FACTS
    ))
    assert "item-level demand" in result
    assert len(calls) == 1
    prompt = " ".join(m["content"] for m in calls[0]["messages"][:-1])
    assert "lack of historical stock logs is NOT the main reason" in prompt


def test_comparison_focus_is_specific_and_uses_no_totals(monkeypatch):
    calls = simulate(monkeypatch, [
        "Completed and pending order records are present. No products are "
        "currently flagged below their reorder levels, but this does not "
        "show how past sales affected inventory."
    ])
    asyncio.run(svc._generate_interpretation(
        "Compare my sales and inventory situation.", FACTS
    ))
    assert len(calls) == 1
    prompt = " ".join(m["content"] for m in calls[0]["messages"][:-1])
    assert "Compare recorded order outcomes with the current inventory flags" in prompt
    assert '"any_products_at_or_below_reorder_now": false' in prompt
    assert "994" not in prompt


def test_live_tautology_rejected_in_comparison_then_corrected(monkeypatch):
    calls = simulate(monkeypatch, [
        "RECORDED orders exist alongside RECORDED completed orders, but "
        "cancelled records are absent.",
        "Completed and pending order records exist, while current inventory "
        "has no products at or below the reorder threshold. Past stock usage "
        "cannot be inferred from this snapshot.",
    ])
    result = asyncio.run(svc._generate_interpretation(
        "Compare my sales and inventory situation.", FACTS
    ))
    assert len(calls) == 2
    assert "Completed and pending" in result
    assert "tautology" in calls[1]["messages"][-1]["content"]


def test_all_caps_recorded_is_normalized_not_retired(monkeypatch):
    calls = simulate(monkeypatch, [
        "RECORDED pending statuses should be verified in the authorized order list."
    ])
    result = asyncio.run(svc._generate_interpretation("What should I do first?", FACTS))
    assert result.startswith("recorded pending")
    assert len(calls) == 1


def test_completed_first_not_blocked_for_explicit_completed_order_audit():
    # A user may legitimately ask about completed orders specifically. Do not
    # impose a priority rule outside open-ended investigation requests.
    result = svc._validate_interpretation(
        "Investigate the recorded completed orders for accounting discrepancies.",
        {**FACTS, "original_question": "How do I audit completed orders?"},
    )
    assert "completed orders" in result


def test_out_of_scope_checks_still_reject_code_and_numbers():
    with pytest.raises(ValueError):
        svc._validate_interpretation("There were 6 orders.", FACTS)
    with pytest.raises(ValueError):
        svc._validate_interpretation("Here is Python code: ```python\nprint('x')\n```", FACTS)
