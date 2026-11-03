"""Phase 12F.2: contextual, concise, historically accurate AI answers."""
import asyncio
import os
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import conversation, analysis_service  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.orders.models import SwiggyOrders  # noqa: E402
from app.products.models import Restaurant, Product  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture
def case(monkeypatch):
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
            SwiggyOrders(order_number="c1", customer_name="Personal name", amount=300,
                         status="completed", order_date=date(2026, 9, 3), restaurant_id=kitchen.id),
            SwiggyOrders(order_number="p1", customer_name="Personal name", amount=100,
                         status="pending", order_date=date(2026, 9, 4), restaurant_id=kitchen.id),
            SwiggyOrders(order_number="k1", customer_name="Other", amount=90000,
                         status="completed", order_date=date(2026, 9, 4), restaurant_id=kfc.id),
        ])
        db.commit()
        calls = []

        async def model(question, facts):
            calls.append((question, facts))
            return "**Assessment**\nHistorical status records warrant checking.\n\n**Priorities**\nVerify whether the pending order was updated."

        monkeypatch.setattr(analysis_service, "_generate_interpretation", model)
        yield db, owner, calls
    engine.dispose()


def ask(db, owner, q, token=None):
    return asyncio.run(conversation.answer_conversation(
        db=db, user=owner, question=q, history=[],
        context_token=token, as_of=date(2026, 11, 3),
    ))


@pytest.mark.parametrize("followup", [
    "Why is that happening?", "What should I do first?", "What could explain this?",
])
def test_followup_uses_original_question_and_compact_verified_context(case, followup):
    db, owner, calls = case
    _, token = ask(db, owner, "Show my restaurant performance for September 2026")
    answer, updated_token = ask(db, owner, followup, token)
    assert calls[-1][0] == followup
    assert calls[-1][1]["response_style"] == "brief_followup"
    assert calls[-1][1]["historical_period"] is True
    assert calls[-1][1]["historical_pending_statuses_need_verification"] is True
    assert "Verified context" in answer
    assert "Orders: 2" in answer and "₹300.00" in answer
    assert "historical status records" in answer.lower()
    assert "**Verified figures" not in answer
    assert "KFC" not in answer and "Personal name" not in answer
    assert updated_token


def test_first_analysis_has_full_verified_figures(case):
    db, owner, calls = case
    response, _ = ask(db, owner, "Is my restaurant functioning well?")
    assert calls[-1][1]["response_style"] == "standard"
    assert "**Verified figures" in response
    assert "Completed-order value" in response


def test_concise_formatter_suppresses_repeated_headings():
    raw = "**Assessment**\nCheck historical records.\n\n**Priorities**\nReview stale statuses.\n\n**Limits**\nTiming is unknown."
    out = analysis_service._compact_followup(raw)
    assert "Assessment" not in out and "Priorities" not in out and "Limits" not in out
    assert out == "Check historical records. Review stale statuses. Timing is unknown."


def test_cross_restaurant_denied_after_context(case):
    db, owner, calls = case
    _, token = ask(db, owner, "Show my restaurant performance for September 2026")
    with pytest.raises(HTTPException) as exc:
        ask(db, owner, "Is KFC doing well?", token)
    assert exc.value.status_code == 403
    assert not calls


def test_no_context_prevents_invented_followup(case):
    db, owner, calls = case
    reply, token = ask(db, owner, "Why is that happening?")
    assert "verified report" in reply
    assert token is None
    assert not calls


def test_grounded_model_prompt_uses_brief_style(monkeypatch):
    payloads = []

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "Check whether the historical status was updated."}}

    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            payloads.append(json)
            return Response()

    monkeypatch.setattr(analysis_service.httpx, "AsyncClient", Client)
    result = asyncio.run(analysis_service._generate_interpretation(
        "What should I do first?", {"response_style": "brief_followup", "historical_period": True}
    ))
    assert "historical status" in result
    assert payloads[0]["messages"][-1]["content"] == "What should I do first?"
    assert "No Assessment/Priorities/Limits headings" in payloads[0]["messages"][1]["content"]
