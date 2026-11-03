"""Phase 12H: fewer Ollama calls, no stale/unauthorized data, safe diagnostics."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import (  # noqa: E402
    analysis_service, conversation, domain_service, intent_service,
    ollama_runtime, service,
)
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Product, Restaurant  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.mark.parametrize("question", [
    "Do I have enough stock to handle more orders?",
    "Do we have enough inventory to fulfill additional orders?",
    "Which orders should I investigate first?",
    "Which orders should we prioritize next?",
    "What are the biggest problems with my restaurant?",
    "What are our main concerns for our business?",
    "Compare my sales and inventory situation.",
    "Compare our revenue with stock levels",
    "What should I focus on next month?",
    "What should we focus on next quarter?",
])
def test_high_confidence_cases(question):
    assert intent_service.eligible_for_classification(question, has_report_context=False)
    assert intent_service.high_confidence_analysis_intent(question)


@pytest.mark.parametrize("question", [
    "Hello", "pokemon", "Write Python code to analyze my inventory",
    "Should I focus on KFC operations?", "Should I focus on improving operations?",
    "How do I update an order status?", "Show my restaurant performance for September 2026",
    "Do I have enough stock to handle more orders at Ghost Cafe?",
])
def test_ambiguous_or_other_intents_do_not_get_fast_path(question):
    assert not intent_service.high_confidence_analysis_intent(question)


@pytest.fixture
def merchant_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    with Session(engine) as db:
        merchant = User(username="m1", email="m1@example.test", role="merchant", password_hash="x")
        merchant2 = User(username="m2", email="m2@example.test", role="merchant", password_hash="x")
        city = Restaurant(name="City Kitchen")
        other = Restaurant(name="KFC")
        db.add_all([merchant, merchant2, city, other]); db.flush()
        db.add_all([
            MerchantRestaurant(user_id=merchant.id, restaurant_id=city.id),
            MerchantRestaurant(user_id=merchant2.id, restaurant_id=other.id),
            SwiggyOrders(order_number="a01", customer_name="Private Customer", status="pending",
                         amount=50, order_date=date(2026, 9, 4), restaurant_id=city.id),
            SwiggyOrders(order_number="b01", customer_name="Other Customer", status="completed",
                         amount=9000, order_date=date(2026, 9, 4), restaurant_id=other.id),
            Product(product_name="Soda", platform="swiggy", price=20,
                    stock_quantity=9, reorder_level=5, restaurant_id=city.id, is_active=True),
        ])
        db.commit()
        yield db, merchant, merchant2
    engine.dispose()


def ask(db, user, query, token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=user, question=query, history=[], context_token=token,
        as_of=date(2026, 11, 3),
    ))


@pytest.mark.parametrize("question", [
    "Do I have enough stock to handle more orders?",
    "Which orders should I investigate first?",
    "What are the biggest problems with my restaurant?",
    "Compare my sales and inventory situation.",
    "What should I focus on next month?",
])
def test_fast_analysis_skips_model_classification_but_rechecks_db(
    merchant_db, monkeypatch, question,
):
    db, owner, _ = merchant_db
    calls = []

    async def forbidden_classifier(question):
        raise AssertionError("Unambiguous analysis intent must not call classifier")

    async def fake_model(question, facts):
        calls.append(facts)
        return "Review recorded orders and inventory thresholds before making decisions."

    monkeypatch.setattr(conversation, "wants_grounded_analysis", forbidden_classifier)
    monkeypatch.setattr(analysis_service, "_generate_interpretation", fake_model)
    reply, token = ask(db, owner, question)
    assert "AI interpretation" in reply
    assert "City Kitchen" in reply
    assert "Orders: 1" in reply
    assert "9000" not in reply
    assert len(calls) == 1
    assert calls[0]["total_orders"] == 1
    assert conversation.read_context(token, owner).kind == "analysis"


def test_followup_requeries_current_records_not_cached(merchant_db, monkeypatch):
    db, owner, _ = merchant_db
    snapshots = []

    async def forbidden_classifier(question):
        raise AssertionError("High-confidence question must bypass classification")

    async def fake_model(question, facts):
        snapshots.append((facts["pending"], facts["completed"]))
        return "Review the recorded statuses and their history."

    monkeypatch.setattr(conversation, "wants_grounded_analysis", forbidden_classifier)
    monkeypatch.setattr(analysis_service, "_generate_interpretation", fake_model)
    reply, token = ask(db, owner, "Which orders should I investigate first?")
    assert "Pending: 1" in reply
    order = db.query(SwiggyOrders).filter(SwiggyOrders.order_number == "a01").one()
    order.status = "completed"
    db.commit()
    reply2, _ = ask(db, owner, "Which orders should I investigate first?", token)
    assert "Pending: 0" in reply2 or "0 recorded as pending" in reply2
    assert snapshots == [(1, 0), (0, 1)]


def test_ambiguous_request_uses_optional_classifier(merchant_db, monkeypatch):
    db, owner, _ = merchant_db
    called = []

    async def classifier(question):
        called.append(question)
        return True

    async def model(question, facts):
        return "Review relevant authorized order records before changing processes."

    monkeypatch.setattr(conversation, "wants_grounded_analysis", classifier)
    monkeypatch.setattr(analysis_service, "_generate_interpretation", model)
    reply, _ = ask(db, owner, "Should I focus on improving operations?")
    assert "AI interpretation" in reply
    assert called == ["Should I focus on improving operations?"]


def test_other_restaurant_still_forbidden_without_classifier(merchant_db, monkeypatch):
    db, owner, _ = merchant_db

    async def forbidden_classifier(question):
        raise AssertionError("Explicit named targets must be blocked first")

    monkeypatch.setattr(conversation, "wants_grounded_analysis", forbidden_classifier)
    with pytest.raises(HTTPException) as error:
        ask(db, owner, "How is KFC doing these days?")
    assert error.value.status_code == 403


def test_out_of_scope_never_reaches_classifier(merchant_db, monkeypatch):
    db, owner, _ = merchant_db

    async def forbidden_classifier(question):
        raise AssertionError("Scope gate should answer before model calls")

    monkeypatch.setattr(conversation, "wants_grounded_analysis", forbidden_classifier)
    reply, _ = ask(db, owner, "pokemon")
    assert reply == domain_service.SCOPE_MESSAGE


def test_keepalive_setting_is_bounded(monkeypatch):
    monkeypatch.setenv("OM_AI_KEEP_ALIVE", "15m")
    assert ollama_runtime._keep_alive_setting() == "15m"
    monkeypatch.setenv("OM_AI_KEEP_ALIVE", "0")
    assert ollama_runtime._keep_alive_setting() == "0"
    monkeypatch.setenv("OM_AI_KEEP_ALIVE", "-1")
    assert ollama_runtime._keep_alive_setting() == "10m"
    monkeypatch.setenv("OM_AI_KEEP_ALIVE", "a bad config")
    assert ollama_runtime._keep_alive_setting() == "10m"


def test_timing_logger_is_opt_in_and_leaks_no_text(monkeypatch, caplog):
    result = {
        "message": {"content": "Customer Private and Order Secret"},
        "total_duration": 3_000_000_000, "load_duration": 250_000_000,
        "prompt_eval_count": 150, "eval_count": 45,
    }
    caplog.set_level(logging.WARNING, logger="app.ai.ollama_performance")
    monkeypatch.setattr(ollama_runtime, "LOG_TIMINGS", False)
    ollama_runtime.log_ollama_result("analysis", result, 3.12)
    assert not caplog.records
    monkeypatch.setattr(ollama_runtime, "LOG_TIMINGS", True)
    ollama_runtime.log_ollama_result("analysis", result, 3.12)
    assert "wall=3.120s" in caplog.text
    assert "load=0.250s" in caplog.text
    assert "prompt_tokens=150" in caplog.text
    assert "Customer Private" not in caplog.text
    assert "Order Secret" not in caplog.text


@pytest.mark.parametrize("module,invoke,valid_answer", [
    (intent_service, "intent", '{"intent":"analyze","confidence":0.95}'),
    (analysis_service, "analysis", "Review recorded orders and current stock flags; future demand is unknown."),
    (service, "guidance", "Check your orders at /merchant/orders."),
])
def test_all_model_requests_specify_keepalive(module, invoke, valid_answer, monkeypatch):
    captured = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": valid_answer}}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            captured.append(json)
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    if invoke == "intent":
        answer = asyncio.run(intent_service.wants_grounded_analysis(
            "Should I focus on improving operations?"
        ))
        assert answer is True
    elif invoke == "analysis":
        answer = asyncio.run(analysis_service._generate_interpretation(
            "What should I investigate?", {"pending": 1, "response_style": "brief_followup"}
        ))
        assert "Review recorded orders" in answer
    else:
        answer = asyncio.run(service.answer_question(
            question="How do I check my orders?", role="merchant", username="m1", history=[],
        ))
        assert "Check your orders" in answer
    assert len(captured) == 1
    assert captured[0]["keep_alive"] == ollama_runtime.KEEP_ALIVE
    assert captured[0]["stream"] is False
    assert captured[0]["think"] is False
