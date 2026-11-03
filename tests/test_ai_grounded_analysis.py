"""Grounded AI analysis and role isolation, using isolated SQLite data."""
import asyncio
import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import conversation, analysis_service, assignment_service  # noqa: E402
from app.ai.service import AIServiceUnavailable  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant, Product  # noqa: E402
from app.users.models import User  # noqa: E402

REAL_GENERATOR = analysis_service._generate_interpretation


@pytest.fixture
def sample(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        User.__table__, Restaurant.__table__, MerchantRestaurant.__table__,
        SwiggyOrders.__table__, Product.__table__,
    ])
    db = Session(engine)
    admin = User(username="admin", email="admin@sample.test", password_hash="x", role="admin")
    merchant = User(username="owner", email="owner@sample.test", password_hash="x", role="merchant")
    other = User(username="other", email="other@sample.test", password_hash="x", role="merchant")
    client = User(username="customer", email="customer@sample.test", password_hash="x", role="client")
    kitchen, kfc = Restaurant(name="City Kitchen"), Restaurant(name="KFC")
    db.add_all([admin, merchant, other, client, kitchen, kfc]); db.flush()
    db.add_all([
        MerchantRestaurant(user_id=merchant.id, restaurant_id=kitchen.id),
        MerchantRestaurant(user_id=other.id, restaurant_id=kfc.id),
    ])
    for idx, (r, status, amount, when) in enumerate([
        (kitchen, "completed", 200, date(2026, 9, 3)),
        (kitchen, "completed", 300, date(2026, 9, 4)),
        (kitchen, "completed", 400, date(2026, 9, 5)),
        (kitchen, "completed", 94, date(2026, 9, 6)),
        (kitchen, "pending", 100, date(2026, 9, 7)),
        (kitchen, "pending", 100, date(2026, 9, 8)),
        (kfc, "completed", 9999, date(2026, 9, 4)),
    ]):
        db.add(SwiggyOrders(
            order_number=f"sample-{idx}", customer_name="Customer PII",
            status=status, order_date=when, amount=amount, restaurant_id=r.id,
        ))
    db.add_all([
        Product(product_name="Lemon Soda", platform="swiggy", price=20,
                restaurant_id=kitchen.id, stock_quantity=7, reorder_level=5, is_active=True),
        Product(product_name="Fruit Salad", platform="swiggy", price=30,
                restaurant_id=kitchen.id, stock_quantity=21, reorder_level=5, is_active=True),
        Product(product_name="KFC Item", platform="swiggy", price=500,
                restaurant_id=kfc.id, stock_quantity=999, reorder_level=10, is_active=True),
    ])
    db.commit()
    captures = []

    async def fake_interpretation(question, facts):
        captures.append((question, facts))
        return "**Assessment**\nThere is some completed activity, but this is a limited sample.\n\n**Priorities**\nReview pending orders."

    monkeypatch.setattr(analysis_service, "_generate_interpretation", fake_interpretation)
    yield db, admin, merchant, other, client, captures
    db.close(); engine.dispose()


def ask(db, user, question, token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=user, question=question, history=[], context_token=token,
        as_of=date(2026, 11, 3),
    ))


def test_functioning_well_not_assignment_claim(sample):
    db, _, merchant, _, _, captures = sample
    assert assignment_service.answer_assignment_question(db=db, user=merchant, question="Is my restaurant functioning well?") is None
    answer, _ = ask(db, merchant, "Is my restaurant functioning well?")
    assert "AI interpretation" in answer
    assert "City Kitchen" in answer
    assert "Orders: 6" in answer
    assert "₹994.00" in answer
    assert "9999" not in answer
    assert len(captures) == 1
    assert captures[0][1]["total_orders"] == 6
    assert captures[0][1]["completed_order_amount_inr"] == "994.00"


def test_prior_september_report_is_requeried_for_ai_assessment(sample):
    db, _, merchant, _, _, captures = sample
    report, token = ask(db, merchant, "Show my restaurant performance for September 2026")
    assert "September 2026" in report
    answer, next_token = ask(db, merchant, "Is my restaurant functioning well?", token)
    assert "September 2026" in answer
    assert "Orders: 6" in answer
    assert captures[-1][1]["report_period"] == "September 2026"
    assert conversation.read_context(next_token, merchant).kind == "analysis"


def test_analysis_followup_what_about_august(sample):
    db, _, merchant, _, _, captures = sample
    _, token = ask(db, merchant, "Assess my restaurant performance in September 2026")
    answer, _ = ask(db, merchant, "What about August?", token)
    assert "August 2026" in answer
    assert "Orders: 0" in answer
    assert "N/A" in answer
    assert captures[-1][1]["total_orders"] == 0


def test_natural_improvement_question_uses_model(sample):
    db, _, merchant, _, _, captures = sample
    answer, _ = ask(db, merchant, "What should I improve?")
    assert "AI interpretation" in answer
    assert captures[-1][1]["inventory_now"]["active_products"] == 2
    assert captures[-1][1]["inventory_now"]["current_total_stock_units"] == 28
    assert "Customer PII" not in str(captures)
    assert "Lemon Soda" not in str(captures)


@pytest.mark.parametrize('text', [
    'Is KFC doing well?',
    'Is Unknown Cafe doing well?',
    'How is KFC performing well?',
    'How well is Unknown Cafe doing?',
    'How is KFC doing?',
    'How is KFC doing these days?',
    'How is Unknown Cafe doing these days?',
])
def test_merchant_other_or_unknown_restaurant_denied(sample, text):
    db, _, merchant, _, _, captures = sample
    with pytest.raises(HTTPException) as exc:
        ask(db, merchant, text)
    assert exc.value.status_code == 403
    assert not captures


def test_admin_needs_restaurant_or_signed_prior_context(sample):
    db, admin, _, _, _, captures = sample
    reply, token = ask(db, admin, "Is my restaurant functioning well?")
    assert "Please name one" in reply
    assert not captures
    _, token = ask(db, admin, "Show City Kitchen performance for September 2026")
    reply, _ = ask(db, admin, "Is my restaurant functioning well?", token)
    assert "City Kitchen" in reply and "September 2026" in reply
    assert captures[-1][1]["total_orders"] == 6


def test_client_cannot_request_restaurant_analysis(sample):
    db, _, _, _, client, captures = sample
    with pytest.raises(HTTPException) as exc:
        ask(db, client, "Is my restaurant functioning well?")
    assert exc.value.status_code == 403
    assert not captures


def test_direct_restaurant_assignment_claim_still_checked(sample):
    db, _, merchant, _, _, _ = sample
    reply, _ = ask(db, merchant, "Is my restaurant KFC?")
    assert "City Kitchen" in reply and "not KFC" in reply


def test_ollama_unavailable_falls_back_to_verified_numbers(sample, monkeypatch):
    db, _, merchant, _, _, _ = sample

    async def unavailable(*args, **kwargs):
        raise AIServiceUnavailable()

    monkeypatch.setattr(analysis_service, "_generate_interpretation", unavailable)
    answer, _ = ask(db, merchant, "Is my restaurant functioning well?")
    assert "interpretation is currently unavailable" in answer
    assert "₹994.00" in answer


def test_ai_analysis_uses_only_select_queries(sample):
    db, _, merchant, _, _, _ = sample
    statements = []

    def capture(conn, cursor, statement, params, context, executemany):
        statements.append(statement.strip().upper())

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        ask(db, merchant, "Is my restaurant functioning well?")
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert statements and all(s.startswith("SELECT") for s in statements)


def test_model_does_not_receive_raw_order_or_user_records(sample):
    db, _, merchant, _, _, captures = sample
    ask(db, merchant, "How can I improve my restaurant?")
    _, facts = captures[-1]
    serialized = repr(facts)
    assert 'Customer PII' not in serialized
    assert 'owner@sample.test' not in serialized
    assert 'KFC' not in serialized
    assert 'Lemon Soda' not in serialized
    assert '9999' not in serialized


def test_numbers_generated_by_model_are_not_accepted(monkeypatch):
    class DummyResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"message": {"content": "You earned ₹1,000,000 and sold 1000 items."}}

    class FakeHTTPClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return DummyResponse()

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeHTTPClient)
    from app.ai.service import AIServiceFailed
    with pytest.raises(AIServiceFailed):
        asyncio.run(analysis_service._generate_interpretation("How am I doing?", {}))


def test_ollama_receives_verified_context_not_sql_or_raw_orders(sample, monkeypatch):
    db, _, merchant, _, _, _ = sample
    posted = []

    class DummyResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"message": {"content": "**Assessment**\nLimited data prevents a definitive rating."}}

    class FakeHTTPClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            posted.append((url, json))
            return DummyResponse()

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeHTTPClient)
    # Replace the fixture's short-circuited model with the real HTTP path.
    # The HTTP client is mocked, so no Ollama server is needed for this test.
    async def via_api(question, facts):
        return await REAL_GENERATOR(question, facts)
    monkeypatch.setattr(analysis_service, "_generate_interpretation", via_api)

    answer, _ = ask(db, merchant, "Is my restaurant functioning well?")
    assert "Limited data" in answer and "₹994.00" in answer
    assert len(posted) == 1
    url, payload = posted[0]
    assert url.endswith('/api/chat')
    assert payload['model'] == analysis_service.MODEL
    assert payload['think'] is False and payload['stream'] is False
    messages = repr(payload['messages'])
    assert 'QUALITATIVE_REPORT_FLAGS' in messages
    assert 'City Kitchen' not in messages and '994.00' not in messages
    assert 'orders_recorded' in messages
    assert 'Customer PII' not in messages
    assert 'owner@sample.test' not in messages
    assert 'SELECT ' not in messages
    assert 'KFC Item' not in messages


def test_model_retries_once_after_unverified_numeric_reply(monkeypatch):
    """A stray model number should not immediately lose AI interpretation."""
    calls = []

    class DummyResponse:
        def __init__(self, content):
            self.content = content
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": self.content}}

    class FakeHTTPClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json):
            calls.append(json)
            if len(calls) == 1:
                return DummyResponse("Revenue is ₹994 with 6 orders")
            return DummyResponse("**Assessment**\nThe sample is small.\n\n**Priorities**\nReview pending orders.")

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeHTTPClient)
    answer = asyncio.run(REAL_GENERATOR("Is my restaurant functioning well?", {"total_orders": 6}))
    assert "sample is small" in answer
    assert "₹" not in answer and "6" not in answer
    assert len(calls) == 2
    assert "Do not include any digits" in calls[1]["messages"][-1]["content"]


def test_valid_model_reply_uses_single_request(monkeypatch):
    calls = []

    class DummyResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": "**Assessment**\nEarly signs are mixed."}}

    class FakeHTTPClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json):
            calls.append(json)
            return DummyResponse()

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", FakeHTTPClient)
    reply = asyncio.run(REAL_GENERATOR("How is the restaurant?", {}))
    assert "Early signs are mixed" in reply
    assert len(calls) == 1
