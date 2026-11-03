"""Phase 12G.4: order-status help matches deployed routes and shared rules."""
import asyncio
import os
from datetime import date
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai import conversation, domain_service, workflow_service  # noqa: E402
from app.core.config import ORDER_STATUSES, ORDER_STATUS_TRANSITIONS  # noqa: E402


@pytest.mark.parametrize("question", [
    "How do I update an order status?",
    "How can I update the status of my restaurant orders?",
    "Where can I change my order status?",
    "Can I modify the order status?",
])
def test_merchant_status_workflow_is_route_accurate(question):
    assert domain_service.scope_reply(question) is None
    reply = workflow_service.verified_workflow_answer(question, "merchant")
    assert reply is not None
    assert "/merchant/orders" in reply
    assert "/merchant/orders/{order_id}" in reply
    assert "Update Order Status" in reply
    assert "one of the offered next statuses" in reply
    assert "read-only" in reply


def test_status_rules_derived_from_shared_config():
    reply = workflow_service.verified_workflow_answer("How do I change order status?", "merchant")
    assert reply is not None
    for status in ORDER_STATUSES:
        allowed = [x for x in ORDER_STATUSES if x in ORDER_STATUS_TRANSITIONS[status]]
        if allowed:
            assert f"**{status}** → " + " or ".join(f"**{x}**" for x in allowed) in reply
        else:
            assert f"**{status}** → final; no further status change" in reply
    assert "delivered" not in reply.lower()
    assert "prepared" not in reply.lower()


def test_admin_guidance_uses_platform_editing_routes():
    reply = workflow_service.verified_workflow_answer("How can I update an order status?", "admin")
    assert "/swiggy/orders" in reply
    assert "/insights/orders" in reply
    assert "**Edit**" in reply
    assert "/merchant/orders/{order_id}" not in reply


def test_client_guidance_does_not_offer_edit_access():
    reply = workflow_service.verified_workflow_answer("How do I update order status?", "client")
    assert "cannot change order statuses" in reply
    assert "/merchant/orders/{order_id}" not in reply


def test_status_tracking_question_not_misrouted_as_editing():
    assert workflow_service.verified_workflow_answer(
        "How can I see the current status of my orders?", "client"
    ) is None


def test_non_status_workflow_not_misrouted():
    assert workflow_service.verified_workflow_answer("How do I update my profile?", "merchant") is None


def test_coding_question_remains_out_of_scope():
    assert "don't write" in domain_service.scope_reply("Write code to update order status?")


@pytest.mark.parametrize("role", ["merchant", "admin", "client"])
def test_conversation_answers_without_calling_ollama_or_database(monkeypatch, role):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Ollama must not be called for verified status help")

    monkeypatch.setattr(conversation, "answer_question", forbidden)
    monkeypatch.setattr(conversation, "wants_grounded_analysis", forbidden)
    user = SimpleNamespace(id=99, role=role, username="example")
    reply, token = asyncio.run(conversation.answer_conversation(
        db=None, user=user, question="How do I update an order status?",
        history=[], as_of=date(2026, 11, 3),
    ))
    assert "Allowed status transitions" in reply
    assert token is None
    if role == "client":
        assert "cannot change order statuses" in reply
    else:
        assert "order status" in reply
