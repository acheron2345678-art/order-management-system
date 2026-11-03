"""Regression: status-specific causal follow-ups use verified reports, not generic chat."""
import asyncio
import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service, conversation  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant, Product  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture
def scenario(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    with Session(engine) as db:
        owner = User(username="owner", email="owner@example.test", password_hash="x", role="merchant")
        other = User(username="other", email="other@example.test", password_hash="x", role="merchant")
        kitchen = Restaurant(name="City Kitchen")
        kfc = Restaurant(name="KFC")
        db.add_all([owner, other, kitchen, kfc]); db.flush()
        db.add_all([
            MerchantRestaurant(user_id=owner.id, restaurant_id=kitchen.id),
            MerchantRestaurant(user_id=other.id, restaurant_id=kfc.id),
            SwiggyOrders(order_number="c1", customer_name="Private User", amount=200,
                         status="completed", order_date=date(2026, 9, 3), restaurant_id=kitchen.id),
            SwiggyOrders(order_number="p1", customer_name="Private User", amount=90,
                         status="pending", order_date=date(2026, 9, 4), restaurant_id=kitchen.id),
            SwiggyOrders(order_number="k1", customer_name="Another User", amount=9999,
                         status="completed", order_date=date(2026, 9, 4), restaurant_id=kfc.id),
        ])
        db.commit()
        captured = []

        async def fake_model(question, facts):
            captured.append((question, facts))
            return "The data does not show why these historical orders were recorded as pending. Check the available order status history."

        async def forbidden_generic(**kwargs):
            raise AssertionError("Pending-order causal follow-ups must not use generic chat")

        monkeypatch.setattr(analysis_service, "_generate_interpretation", fake_model)
        monkeypatch.setattr(conversation, "answer_question", forbidden_generic)
        yield db, owner, captured
    engine.dispose()


def ask(db, owner, question, token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=owner, question=question, history=[],
        context_token=token, as_of=date(2026, 11, 3),
    ))


@pytest.mark.parametrize("question", [
    "What could explain the pending orders?",
    "What might cause these pending orders?",
    "Why are my orders pending?",
    "Why were the pending orders?",
])
def test_pending_order_followup_uses_verified_report(scenario, question):
    db, owner, captured = scenario
    _, token = ask(db, owner, "Show my restaurant performance for September 2026")
    result, new_token = ask(db, owner, question, token)
    assert captured[-1][0] == question
    facts = captured[-1][1]
    assert facts["report_period"] == "September 2026"
    assert facts["historical_period"] is True
    assert facts["pending"] == 1
    assert facts["completed"] == 1
    assert facts["response_style"] == "brief_followup"
    assert "Verified context: City Kitchen · September 2026" in result
    assert "Private User" not in str(captured) and "KFC" not in str(captured)
    assert conversation.read_context(new_token, owner).kind == "analysis"


def test_without_report_requires_verified_context(scenario):
    db, owner, captured = scenario
    answer, token = ask(db, owner, "What could explain the pending orders?")
    assert "verified report" in answer
    assert token is None
    assert not captured


def test_named_other_restaurant_still_forbidden(scenario):
    db, owner, captured = scenario
    _, token = ask(db, owner, "Show my restaurant performance for September 2026")
    with pytest.raises(HTTPException) as exc:
        ask(db, owner, "Is KFC performing well?", token)
    assert exc.value.status_code == 403
    assert not captured


def test_prompt_warns_against_unsupported_status_workflows():
    prompt = analysis_service.ANALYSIS_SYSTEM_PROMPT
    assert "delivery partner" in prompt
    assert "cancellation request" in prompt
    assert "historical order status" in prompt


def test_rejected_model_produces_specific_verified_historical_guidance(scenario, monkeypatch):
    db, owner, _ = scenario
    _, token = ask(db, owner, "Show my restaurant performance for September 2026")

    async def rejected(question, facts):
        assert facts["report_period"] == "September 2026"
        raise analysis_service.AIInterpretationRejected("unsafe model response")

    monkeypatch.setattr(analysis_service, "_generate_interpretation", rejected)
    text, _ = ask(db, owner, "What could explain the pending orders?", token)
    assert "Verified guidance (AI response failed validation)" in text
    assert "historical period" in text
    assert "status history" in text
    assert "does not establish why" in text
    assert "Orders: 2" in text
    assert "interpretation is currently unavailable" not in text


def test_numeric_echo_retry_uses_qualitative_facts_only(monkeypatch):
    captured = []

    class Response:
        def __init__(self, text):
            self.text = text
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": self.text}}

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json):
            captured.append(json)
            if len(captured) == 1:
                return Response("There were 2 pending orders in September 2026.")
            return Response(
                "The recorded statuses do not reveal the cause. "
                "Check the available order details and status history."
            )

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", Client)
    result = asyncio.run(analysis_service._generate_interpretation(
        "What could explain the pending orders?",
        {
            "total_orders": 6, "pending": 2,
            "completed_order_amount_inr": "994.00",
            "historical_period": True,
            "response_style": "brief_followup",
        },
    ))
    assert "do not reveal the cause" in result
    assert len(captured) == 2
    assert "QUALITATIVE_REPORT_FLAGS" in str(captured[0]["messages"])
    assert '"total_orders": 6' not in str(captured[0]["messages"])
    second_messages = str(captured[1]["messages"])
    assert "QUALITATIVE_REPORT_FLAGS" in second_messages
    assert '"total_orders": 6' not in second_messages
    assert '994.00' not in second_messages


def test_persistent_invalid_numeric_echo_is_labeled_rejected(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": "Invented ₹99999999 in revenue."}}

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", Client)
    with pytest.raises(analysis_service.AIInterpretationRejected):
        asyncio.run(analysis_service._generate_interpretation(
            "What could explain the pending orders?",
            {"pending": 2, "total_orders": 6, "historical_period": True}
        ))
