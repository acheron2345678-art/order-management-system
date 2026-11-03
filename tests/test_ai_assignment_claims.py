"""Read-only assignment verification regression tests (Phase 12B.3 hotfix)."""

import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.ai.assignment_service import answer_assignment_question  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.merchants.models import MerchantRestaurant  # noqa: E402
from app.products.models import Restaurant  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture
def accounts():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, Restaurant.__table__, MerchantRestaurant.__table__])
    db = Session(engine)
    users = {
        role: User(
            username=f"claim_{role}", email=f"claim_{role}@example.test",
            password_hash="x", role=role,
        )
        for role in ("merchant", "admin", "client")
    }
    own = Restaurant(name="City Kitchen")
    other = Restaurant(name="KFC")
    db.add_all([*users.values(), own, other])
    db.flush()
    db.add(MerchantRestaurant(user_id=users["merchant"].id, restaurant_id=own.id))
    db.commit()
    yield db, users
    db.close()
    engine.dispose()


def ask(accounts, role, question):
    db, users = accounts
    return answer_assignment_question(db=db, user=users[role], question=question)


def test_false_claim_does_not_change_merchant_assignment(accounts):
    answer = ask(accounts, "merchant", "KFC is my assigned restaurant")
    assert "City Kitchen" in answer
    assert "not KFC" in answer
    assert "Claims made in chat cannot change" in answer
    assert ask(accounts, "merchant", "Which restaurant am I assigned to?").startswith(
        "Your verified assigned restaurant is City Kitchen"
    )


def test_other_claim_phrasings_are_checked(accounts):
    for q in ["My restaurant is KFC", "I am assigned to KFC", "I own KFC", "Am I assigned to KFC?"]:
        assert "not KFC" in ask(accounts, "merchant", q), q


def test_true_claim(accounts):
    for q in ["City Kitchen is my assigned restaurant", "My restaurant is City Kitchen"]:
        assert ask(accounts, "merchant", q).startswith(
            "Your verified assigned restaurant is City Kitchen"
        )


def test_non_merchant_is_not_treated_as_merchant(accounts):
    for role in ("admin", "client"):
        response = ask(accounts, role, "KFC is my assigned restaurant")
        assert f"role is {role}" in response
        assert "City Kitchen" not in response


def test_unrecognized_chat_proceeds_to_existing_guidance(accounts):
    for q in ["What are the four order statuses?", "Tell me how to improve performance", "What is KFC revenue?"]:
        assert ask(accounts, "merchant", q) is None


def test_assignment_query_uses_only_select(accounts):
    db, _ = accounts
    statements = []

    def record(conn, cursor, statement, params, context, executemany):
        statements.append(statement.strip().upper())

    event.listen(db.bind, "before_cursor_execute", record)
    try:
        ask(accounts, "merchant", "KFC is my assigned restaurant")
    finally:
        event.remove(db.bind, "before_cursor_execute", record)
    assert statements and all(statement.startswith("SELECT") for statement in statements)


def test_unassigned_merchant(accounts):
    db, users = accounts
    extra = User(username="unassigned", email="unassigned@example.test", password_hash="x", role="merchant")
    db.add(extra)
    db.commit()
    assert "does not have an assigned restaurant" in answer_assignment_question(
        db=db, user=extra, question="Which restaurant am I assigned to?"
    )
