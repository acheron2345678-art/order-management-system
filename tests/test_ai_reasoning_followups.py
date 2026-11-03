"""Reasoning followups use freshly scoped data, not chat-provided metrics."""
import asyncio
import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service, conversation  # noqa: E402
from app.ai.service import AIServiceFailed  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant, Product  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    with Session(engine) as db:
        alice = User(username="alice", email="alice@sample.test", password_hash="x", role="merchant")
        bob = User(username="bob", email="bob@sample.test", password_hash="x", role="merchant")
        kitchen = Restaurant(name="City Kitchen")
        kfc = Restaurant(name="KFC")
        db.add_all([alice, bob, kitchen, kfc])
        db.flush()
        db.add_all([
            MerchantRestaurant(user_id=alice.id, restaurant_id=kitchen.id),
            MerchantRestaurant(user_id=bob.id, restaurant_id=kfc.id),
            SwiggyOrders(order_number="a", customer_name="Private Customer", status="completed", order_date=date(2026, 9, 2), amount=150, restaurant_id=kitchen.id),
            SwiggyOrders(order_number="b", customer_name="Private Customer", status="pending", order_date=date(2026, 9, 3), amount=50, restaurant_id=kitchen.id),
            SwiggyOrders(order_number="c", customer_name="Private Customer", status="completed", order_date=date(2026, 9, 4), amount=4000, restaurant_id=kfc.id),
        ])
        db.commit()
        captures = []

        async def fake_interpretation(question, facts):
            captures.append((question, facts))
            return "**Assessment**\nLimited evidence.\n\n**Priorities**\nReview pending orders."

        monkeypatch.setattr(analysis_service, "_generate_interpretation", fake_interpretation)
        yield db, alice, bob, captures
    engine.dispose()


def ask(db, user, question, context_token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=user, question=question, history=[],
        context_token=context_token, as_of=date(2026, 11, 3)
    ))


@pytest.mark.parametrize("followup", [
    "Why is that happening?",
    "What should I do first?",
    "What should we focus on next?",
    "What could explain this?",
    "What does that mean for my restaurant?",
])
def test_followup_reuses_verified_september_scope(setup, followup):
    db, alice, _, captures = setup
    _, token = ask(db, alice, "Show my restaurant performance for September 2026")
    result, new_token = ask(db, alice, followup, token)
    assert "AI interpretation" in result
    assert "September 2026" in result
    assert "Orders: 2" in result
    if "focus on" in followup.lower():
        # A priority question only needs its relevant verified status and
        # inventory flags; repeating revenue would distract from the answer.
        assert "products at/below reorder now" in result
        assert "₹150.00" not in result
    else:
        assert "₹150.00" in result
    assert "Private Customer" not in str(captures)
    assert "KFC" not in str(captures)
    assert captures[-1][1]["report_period"] == "September 2026"
    assert conversation.read_context(new_token, alice).kind == "analysis"


def test_cross_user_token_cannot_retrieve_other_restaurant(setup, monkeypatch):
    db, alice, bob, captures = setup
    _, token = ask(db, alice, "Show my restaurant performance for September 2026")
    called = []

    async def fake_general(**kwargs):
        called.append(kwargs)
        return "This must not run for an ungrounded follow-up."

    monkeypatch.setattr(conversation, "answer_question", fake_general)
    response, _ = ask(db, bob, "Why is that happening?", token)
    assert "I need a verified report" in response
    assert not captures
    assert not called


def test_no_prior_report_followup_requests_context(setup, monkeypatch):
    db, alice, _, captures = setup
    async def fail_general(**kwargs):
        raise AssertionError("Unverified follow-up must not reach generic Ollama")
    monkeypatch.setattr(conversation, "answer_question", fail_general)
    reply, token = ask(db, alice, "What should I do first?")
    assert "I need a verified report" in reply
    assert token is None
    assert not captures


def test_explicit_cross_restaurant_request_still_denied(setup):
    db, alice, _, captures = setup
    _, token = ask(db, alice, "Show my restaurant performance for September 2026")
    with pytest.raises(HTTPException) as exc:
        ask(db, alice, "Is KFC doing well?", token)
    assert exc.value.status_code == 403
    assert not captures


def test_review_rejects_historical_inventory_overclaim():
    with pytest.raises(ValueError):
        analysis_service._validate_interpretation(
            "Supply-side constraints do not appear to be the bottleneck for those orders."
        )
    assert "current snapshot" in analysis_service._validate_interpretation(
        "Inventory is a current snapshot; it cannot establish historical stock issues."
    )


def test_interpretation_retries_causal_overclaim(monkeypatch):
    replies = [
        "Inventory is healthy, so supply-side constraints are not the bottleneck.",
        "**Assessment**\nThere is not enough evidence to establish a cause. "
        "**Priorities**\nReview open tickets and historical stock logs.",
    ]
    posts = []

    class FakeResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": self.content}}

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            posts.append(json)
            return FakeResponse(replies.pop(0))

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(analysis_service._generate_interpretation("Why is that happening?", {}))
    assert "not enough evidence" in result
    assert len(posts) == 2
    assert "stock shortages" in posts[-1]["messages"][-1]["content"]


def test_persistent_overclaim_is_rejected(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "Current stock is fine, so inventory was not the cause of the delays."}}

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return FakeResponse()

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeClient)
    with pytest.raises(AIServiceFailed):
        asyncio.run(analysis_service._generate_interpretation("Why?", {}))
