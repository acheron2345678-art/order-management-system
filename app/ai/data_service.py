"""Read-only, authorization-scoped restaurant reporting for AI chat.

No LLM-supplied SQL or database writes. Only aggregate, restaurant-scoped
Swiggy order facts are returned. Client accounts may not read merchant revenue.
"""

import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.merchants.models import MerchantRestaurant
from app.orders.models import SwiggyOrders
from app.products.models import Restaurant
from app.users.models import User

STATUS_NAMES = ("pending", "processing", "completed", "cancelled")
REVENUE_TERMS = re.compile(r"\b(?:revenue|sales|earnings|turnover)\b", re.I)
ORDER_TERMS = re.compile(
    r"\b(?:order (?:summary|statistics|stats|counts?|breakdown)|"
    r"orders? (?:summary|statistics|stats|counts?|breakdown)|"
    r"how many (?:pending |processing |completed |cancelled )?orders|"
    r"(?:pending|processing|completed|cancelled) orders|"
    r"restaurant performance)\b", re.I
)
ADVICE_TERMS = re.compile(
    r"\b(?:how (?:can|do|should) i (?:improve|increase|boost|manage)|"
    r"tips|advice|strategies|best practices|meaning|definition|explain)\b", re.I
)


def _report_window(question: str, today: date) -> tuple[date | None, date | None, str]:
    q = question.casefold()
    if "last month" in q or "previous month" in q:
        end = today.replace(day=1)
        start = (end - timedelta(days=1)).replace(day=1)
        return start, end, f"last month ({start:%B %Y})"
    if "this month" in q or "current month" in q:
        start = today.replace(day=1)
        return start, today + timedelta(days=1), f"this month ({start:%B %Y})"
    if re.search(r"\byesterday\b", q):
        start = today - timedelta(days=1)
        return start, today, f"yesterday ({start.isoformat()})"
    if re.search(r"\btoday\b", q):
        return today, today + timedelta(days=1), f"today ({today.isoformat()})"
    return None, None, "all recorded dates"


def _mentioned_restaurants(db: Session, question: str) -> list[Restaurant]:
    """Match known restaurant names as complete words, not fuzzy guesses."""
    restaurants = db.query(Restaurant).all()
    matches = [
        restaurant for restaurant in restaurants
        if re.search(
            r"(?<!\w)" + re.escape(restaurant.name) + r"(?!\w)",
            question,
            re.I,
        )
    ]
    if not matches:
        return []
    # "KFC Express" should not separately match the shorter "KFC".
    return [
        restaurant for restaurant in matches
        if not any(
            other.id != restaurant.id and len(other.name) > len(restaurant.name)
            and re.search(
                r"(?<!\w)" + re.escape(restaurant.name) + r"(?!\w)",
                other.name, re.I,
            )
            for other in matches
        )
    ]


def _select_restaurant(db: Session, user: User, question: str) -> Restaurant | None:
    if user.role == "client":
        raise HTTPException(status_code=403, detail="Restaurant financial reports are not available to client accounts.")
    if user.role == "merchant":
        assignment = (
            db.query(MerchantRestaurant)
            .filter(MerchantRestaurant.user_id == user.id)
            .first()
        )
        if assignment is None or assignment.restaurant is None:
            raise HTTPException(status_code=403, detail="Your merchant account has no assigned restaurant.")
        restaurant = assignment.restaurant
        mentioned = _mentioned_restaurants(db, question)
        if mentioned and (
            len(mentioned) != 1 or mentioned[0].id != restaurant.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You can view reports only for your assigned restaurant.",
            )
        return restaurant
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Restaurant reports are not available to this account.")

    # Admin may name any restaurant. Require one unambiguous restaurant; don't
    # quietly aggregate other restaurants or guess based on a partial name.
    mentioned = _mentioned_restaurants(db, question)
    return mentioned[0] if len(mentioned) == 1 else None


def answer_data_question(
    *, db: Session, user: User, question: str, as_of: date | None = None
) -> str | None:
    """Return exact aggregate metrics, or None for ordinary guidance questions.

    This is deliberately a narrow whitelist of recognized report requests.
    Unrecognized questions proceed to guidance-only Ollama, with no DB rows.
    """
    if not (REVENUE_TERMS.search(question) or ORDER_TERMS.search(question)):
        return None
    if ADVICE_TERMS.search(question):
        return None

    restaurant = _select_restaurant(db, user, question)
    if restaurant is None:
        return (
            "Please name one restaurant to report on, for example: "
            "'KFC revenue this month'. No report was generated."
        )

    start, end, label = _report_window(question, as_of or date.today())
    status_expr = func.lower(func.trim(SwiggyOrders.status))
    query = (
        db.query(
            status_expr.label("status"),
            func.count(SwiggyOrders.id).label("order_count"),
            func.coalesce(func.sum(SwiggyOrders.amount), 0).label("total_amount"),
        )
        .filter(SwiggyOrders.restaurant_id == restaurant.id)
    )
    if start is not None:
        query = query.filter(SwiggyOrders.order_date >= start)
    if end is not None:
        query = query.filter(SwiggyOrders.order_date < end)
    rows = query.group_by(status_expr).all()

    counts = {name: 0 for name in STATUS_NAMES}
    completed_total = Decimal("0.00")
    other_count = 0
    for status, count, amount in rows:
        if status in counts:
            counts[status] += int(count or 0)
            if status == "completed":
                completed_total += Decimal(str(amount or 0))
        else:
            other_count += int(count or 0)

    completed_total = completed_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = sum(counts.values()) + other_count
    return (
        f"Verified Swiggy order report for {restaurant.name} — {label}.\n"
        f"Completed-order revenue: ₹{completed_total:,.2f} "
        "(sum of completed order amounts only).\n"
        f"Total recorded orders: {total}.\n"
        f"Pending: {counts['pending']}; Processing: {counts['processing']}; "
        f"Completed: {counts['completed']}; Cancelled: {counts['cancelled']}."
        + (f" Other/unrecognized statuses: {other_count}." if other_count else "")
        + "\nThese values come from the database, not an AI estimate. "
        "Insights orders and payments/refunds are not included."
    )
