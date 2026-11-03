"""Phase 12G: intent is a hint, never an authorization or SQL instruction."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import analysis_service, conversation, intent_service  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant, Product  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.mark.parametrize("question,context,eligible", [
    ("Do I have enough stock to handle more orders?", False, True),
    ("Which orders should I investigate first?", False, True),
    ("What are the biggest problems with my restaurant?", False, True),
    ("Compare my sales and inventory situation", False, True),
    ("What should I focus on next month?", False, True),
    ("Show my restaurant performance for September 2026", False, False),
    ("What is my name?", True, False),
    ("How do I register a merchant?", False, False),
    ("Hello", False, False),
])
def test_prefilter(question, context, eligible):
    assert intent_service.eligible_for_classification(question, has_report_context=context) is eligible


@pytest.mark.parametrize("body, expected", [
    ({"intent": "analyze", "confidence": 0.93}, True),
    ({"intent": "general", "confidence": 1.0}, False),
    ({"intent": "analyze", "confidence": 0.51}, False),
    ({"intent": "analyze", "confidence": "0.99"}, False),
    ({"intent": "analyze", "confidence": 1.3}, False),
    ({"intent": "analyze", "confidence": 0.99, "sql": "DROP TABLE users"}, False),
])
def test_structured_classifier_validates_result(monkeypatch, body, expected):
    calls = []

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": json.dumps(body)}}

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            calls.append(json)
            return Response()

    monkeypatch.setattr(intent_service.httpx, "AsyncClient", Client)
    result = asyncio.run(intent_service.wants_grounded_analysis("Do I have enough stock to handle more orders?"))
    assert result is expected
    assert calls[0]["format"] == intent_service.INTENT_SCHEMA
    assert calls[0]["messages"][-1] == {"role": "user", "content": "Do I have enough stock to handle more orders?"}
    assert "tools" not in calls[0]


def test_classifier_unavailable_returns_false(monkeypatch):
    import httpx
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("Ollama not running")
    monkeypatch.setattr(intent_service.httpx, "AsyncClient", Client)
    assert asyncio.run(intent_service.wants_grounded_analysis("Which orders should I check?")) is False


@pytest.fixture
def data(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    with Session(engine) as db:
        owner = User(username="merchant1", email="merchant1@example.test", role="merchant", password_hash="x")
        other = User(username="merchant2", email="merchant2@example.test", role="merchant", password_hash="x")
        client = User(username="client", email="client@example.test", role="client", password_hash="x")
        city = Restaurant(name="City Kitchen")
        kfc = Restaurant(name="KFC")
        db.add_all([owner, other, client, city, kfc]); db.flush()
        db.add_all([
            MerchantRestaurant(user_id=owner.id, restaurant_id=city.id),
            MerchantRestaurant(user_id=other.id, restaurant_id=kfc.id),
            SwiggyOrders(order_number="c01", customer_name="Private Customer", amount=400,
                         status="completed", order_date=date(2026, 9, 3), restaurant_id=city.id),
            SwiggyOrders(order_number="c02", customer_name="Private Customer", amount=30,
                         status="pending", order_date=date(2026, 9, 4), restaurant_id=city.id),
            SwiggyOrders(order_number="kfc01", customer_name="Sensitive Customer", amount=99999,
                         status="completed", order_date=date(2026, 9, 4), restaurant_id=kfc.id),
            Product(product_name="Test Lemon Soda", platform="swiggy", stock_quantity=8,
                    reorder_level=5, restaurant_id=city.id, is_active=True, price=10),
        ])
        db.commit()
        captured = []
        async def model(question, facts):
            captured.append((question, facts))
            return "Review recorded pending orders and their status history. Current stock alone cannot predict capacity."
        async def general(**kwargs):
            return "General guidance only."
        async def classifier(text):
            return True
        monkeypatch.setattr(analysis_service, "_generate_interpretation", model)
        monkeypatch.setattr(conversation, "answer_question", general)
        monkeypatch.setattr(conversation, "wants_grounded_analysis", classifier)
        yield db, owner, other, client, captured
    engine.dispose()


def ask(db, user, question, token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=user, question=question, history=[],
        context_token=token, as_of=date(2026, 11, 3),
    ))


@pytest.mark.parametrize("question", [
    "Do I have enough stock to handle more orders?",
    "Which orders should I investigate first?",
    "What are the biggest problems with my restaurant?",
    "Compare my sales and inventory situation",
    "What should I focus on next month?",
])
def test_flexible_questions_get_authorized_aggregates(data, question):
    db, owner, _, _, captured = data
    reply, token = ask(db, owner, question)
    assert "AI interpretation" in reply
    assert "City Kitchen" in reply
    assert "Verified figures" in reply
    assert captured[-1][0] == question
    facts = captured[-1][1]
    assert facts["total_orders"] == 2
    assert facts["inventory_now"]["active_products"] == 1
    assert "Private Customer" not in str(captured)
    assert "Sensitive Customer" not in str(captured)
    assert "99999" not in str(captured)
    assert "KFC" not in str(captured)
    assert conversation.read_context(token, owner).kind == "analysis"


def test_semantic_followup_preserves_verified_september(data):
    db, owner, _, _, captured = data
    _, token = ask(db, owner, "Show my restaurant performance for September 2026")
    result, token = ask(db, owner, "Which orders should I investigate first?", token)
    assert captured[-1][0] == "Which orders should I investigate first?"
    assert captured[-1][1]["report_period"] == "September 2026"
    assert "Verified context: City Kitchen · September 2026" in result
    assert conversation.read_context(token, owner).period == "2026-09"


def test_cross_restaurant_semantic_request_is_denied(data):
    db, owner, _, _, captured = data
    with pytest.raises(HTTPException) as error:
        ask(db, owner, "Should I focus on KFC operations?")
    assert error.value.status_code == 403
    assert captured == []


def test_unknown_named_restaurant_does_not_use_merchants_own(data):
    db, owner, _, _, captured = data
    with pytest.raises(HTTPException) as error:
        ask(db, owner, "Should I focus on Ghost Cafe operations?")
    assert error.value.status_code == 403
    assert not captured


def test_lowercase_unknown_restaurant_is_not_silently_substituted(data):
    db, owner, _, _, captured = data
    with pytest.raises(HTTPException) as error:
        ask(db, owner, "Should I focus on ghost cafe operations?")
    assert error.value.status_code == 403
    assert not captured


def test_general_modifier_is_not_a_fake_restaurant(data):
    db, owner, _, _, captured = data
    answer, _ = ask(db, owner, "Should I focus on improving operations?")
    assert "AI interpretation" in answer
    assert captured[-1][1]["restaurant"] == "City Kitchen"


def test_client_does_not_get_private_analytics_from_classifier(data):
    db, _, _, client, captured = data
    with pytest.raises(HTTPException) as error:
        ask(db, client, "Do I have enough stock to handle more orders?")
    assert error.value.status_code == 403
    assert not captured


def test_classifier_declines_keeps_existing_guidance(data, monkeypatch):
    db, owner, _, _, captured = data
    async def decline(question): return False
    monkeypatch.setattr(conversation, "wants_grounded_analysis", decline)
    result, _ = ask(db, owner, "What are the biggest problems with my restaurant?")
    assert result == "General guidance only."
    assert captured == []


def test_explicit_reports_skip_intent_classifier(data, monkeypatch):
    db, owner, _, _, _ = data
    async def forbidden(question):
        raise AssertionError("Explicit reports should never need intent classification")
    monkeypatch.setattr(conversation, "wants_grounded_analysis", forbidden)
    result, _ = ask(db, owner, "Show my restaurant performance for September 2026")
    assert "Verified Swiggy order-performance report" in result
