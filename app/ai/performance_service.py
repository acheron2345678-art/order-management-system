"""Verified, read-only restaurant performance and operational feedback.

Only the authenticated role and merchant assignment determine access. All
numbers are calculated from Swiggy order records in SQLAlchemy; Qwen never
receives database credentials and does not generate SQL or numeric results.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.data_service import _select_restaurant
from app.ai.periods import named_months, only_date_words
from app.orders.models import SwiggyOrders
from app.users.models import User

STATUSES = ("pending", "processing", "completed", "cancelled")

# A deliberately narrow whitelist. Ordinary application-help questions still
# reach the guidance model rather than being mistaken for a data request.
PERFORMANCE_INTENT = re.compile(
    r"\bperformance\b"
    r"|\b(?:order|restaurant|merchant|business)\s+(?:performance|trends?|analysis|health)\b"
    r"|\b(?:completion|cancellation|cancelled|pending)\s+(?:rates?|trends?|analysis|backlog)\b"
    r"|\b(?:revenue|sales|order|orders|cancellation|cancelled)\s+trends?\b"
    r"|\b(?:operational|business)\s+(?:feedback|recommendations?|analysis|insights)\b"
    r"|\b(?:compare|comparison|versus)\b.*\b(?:revenue|sales|orders?|performance|cancellations?|completion)\b"
    r"|\b(?:revenue|sales|orders?|performance|cancellations?|completion)\b.*\b(?:vs\.?|versus|compared\s+to)\b"
    r"|\b(?:cancellations?|cancelled\s+orders?|pending\s+orders?)\b.*\b(?:increas\w*|decreas\w*|ris\w*|fall\w*|high|trends?)\b"
    r"|\b(?:how\s+is|how\s+are)\b.*\b(?:restaurant|orders?|performing|doing)\b",
    re.I,
)
COMPARE_INTENT = re.compile(
    r"\b(?:compare|comparison|vs\.?|versus|compared|trends?|increasing|decreasing|rising|falling)\b",
    re.I,
)
# 'How can I improve restaurant performance?' is general advice, not a
# request for a verified report. Keep that question available to Ollama.
GENERAL_HELP = re.compile(
    r"^\s*(?:what\s+does|what\s+is\s+a|explain|define|"
    r"how\s+(?:can|do|should)\s+(?:i|we)\s+"
    r"(?:improve|investigate|reduce|increase|manage|check|analy[sz]e)|"
    r"tips?\s+for|best\s+practices\s+for)\b",
    re.I,
)
_EXPLICIT_TARGET = (
    re.compile(
        r"\b(?:show|analyse|analyze|explain|compare|what\s+is|how\s+is)\s+"
        r"(?P<name>[\w&.'\- ]{2,85}?)\s+(?:order\s+)?"
        r"(?:performance|trends?|analysis|completion\s+rate|cancellation\s+rate|"
        r"revenue\s+trends?|sales\s+trends?)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:performance|completion\s+rate|cancellation\s+rate|order\s+trends?|"
        r"order\s+analysis)\s+(?:for|of|at|in)\s+"
        r"(?P<name>[\w&.'\- ]{2,85}?)(?:\s+(?:this|last|previous)\s+"
        r"(?:month|week)|\s+today|\s+yesterday)?\s*[?.!]*$",
        re.I,
    ),
)
_GENERIC_TARGETS = {
    "my", "our", "the", "this", "your", "my restaurant", "our restaurant",
    "the restaurant", "my assigned restaurant", "my own restaurant", "my orders",
    "my restaurant's", "our restaurant's", "the orders", "my business",
}


@dataclass(frozen=True)
class Window:
    start: date | None
    end: date | None  # exclusive
    label: str


@dataclass(frozen=True)
class Metrics:
    counts: dict[str, int]
    other: int
    total: int
    revenue: Decimal

    @property
    def completion_rate(self) -> Decimal | None:
        return _rate(self.counts["completed"], self.total)

    @property
    def cancellation_rate(self) -> Decimal | None:
        return _rate(self.counts["cancelled"], self.total)


def _rate(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def _previous_month_start(first_day: date) -> date:
    return (first_day - timedelta(days=1)).replace(day=1)


def _month_window(today: date, last: bool = False) -> Window:
    this_start = today.replace(day=1)
    if last:
        start = _previous_month_start(this_start)
        return Window(start, this_start, f"last month ({start:%B %Y})")
    return Window(this_start, today + timedelta(days=1), f"this month through {today.isoformat()}")


def _week_window(today: date, last: bool = False) -> Window:
    this_monday = today - timedelta(days=today.weekday())
    if last:
        start = this_monday - timedelta(days=7)
        return Window(start, this_monday, f"last week ({start.isoformat()} to {(this_monday - timedelta(days=1)).isoformat()})")
    return Window(this_monday, today + timedelta(days=1), f"this week through {today.isoformat()}")


def _windows(question: str, today: date) -> tuple[Window, Window | None]:
    """Compare equal elapsed days instead of MTD against a full month."""
    q = question.casefold()
    comparing = bool(COMPARE_INTENT.search(q))
    explicit_months = named_months(question, today)
    if explicit_months:
        first = explicit_months[0]
        current = Window(first.start, first.end, first.label)
        if comparing:
            if len(explicit_months) >= 2:
                second = explicit_months[1]
                previous = Window(second.start, second.end, second.label)
            else:
                prior_start = _previous_month_start(first.start)
                previous = Window(prior_start, first.start, f"{prior_start:%B %Y}")
            return current, previous
        return current, None
    if comparing:
        if "week" in q:
            current = _week_window(today)
            prior_start = current.start - timedelta(days=7)
            days = (current.end - current.start).days
            previous = Window(
                prior_start, prior_start + timedelta(days=days),
                f"previous week's matching {days} day(s)",
            )
        else:
            current = _month_window(today)
            prior_start = _previous_month_start(current.start)
            days = (current.end - current.start).days
            # E.g. March 31 vs Feb 28: no spilling into March.
            available = calendar.monthrange(prior_start.year, prior_start.month)[1]
            included = min(days, available)
            previous = Window(
                prior_start, prior_start + timedelta(days=included),
                f"previous month's first {included} day(s) ({prior_start:%B %Y})",
            )
        return current, previous

    if "last month" in q or "previous month" in q:
        return _month_window(today, last=True), None
    if "this week" in q or "current week" in q:
        return _week_window(today), None
    if "last week" in q or "previous week" in q:
        return _week_window(today, last=True), None
    if re.search(r"\byesterday\b", q):
        yesterday = today - timedelta(days=1)
        return Window(yesterday, today, f"yesterday ({yesterday.isoformat()})"), None
    if re.search(r"\btoday\b", q):
        return Window(today, today + timedelta(days=1), f"today ({today.isoformat()})"), None
    if "all time" in q or "all-time" in q or "all recorded" in q:
        return Window(None, None, "all recorded dates"), None
    return _month_window(today), None


def _explicit_target(question: str) -> str | None:
    for pattern in _EXPLICIT_TARGET:
        match = pattern.search(question)
        if match:
            name = " ".join(match.group("name").strip(" .?!").split())
            if name and name.casefold() not in _GENERIC_TARGETS and not only_date_words(name):
                return name
    return None


def _get_metrics(db: Session, restaurant_id: int, period: Window) -> Metrics:
    status = func.lower(func.trim(SwiggyOrders.status))
    query = db.query(
        status.label("status"),
        func.count(SwiggyOrders.id),
        func.coalesce(func.sum(SwiggyOrders.amount), 0),
    ).filter(SwiggyOrders.restaurant_id == restaurant_id)
    if period.start is not None:
        query = query.filter(SwiggyOrders.order_date >= period.start)
    if period.end is not None:
        query = query.filter(SwiggyOrders.order_date < period.end)

    counts = {s: 0 for s in STATUSES}
    revenue = Decimal("0.00")
    other = 0
    for normalized_status, count, amount in query.group_by(status).all():
        count = int(count or 0)
        if normalized_status in counts:
            counts[normalized_status] += count
            if normalized_status == "completed":
                revenue += Decimal(str(amount or 0))
        else:
            other += count
    revenue = revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Metrics(counts, other, sum(counts.values()) + other, revenue)


def _percentage(value: Decimal | None) -> str:
    return "N/A (no orders)" if value is None else f"{value:.1f}%"


def _render_metrics(label: str, metrics: Metrics) -> list[str]:
    c = metrics.counts
    return [
        f"{label}:",
        f"- Total orders: {metrics.total}; Pending: {c['pending']}; Processing: {c['processing']}; "
        f"Completed: {c['completed']}; Cancelled: {c['cancelled']}"
        + (f"; Other/unrecognized statuses: {metrics.other}" if metrics.other else ""),
        f"- Completion rate: {_percentage(metrics.completion_rate)}; "
        f"Cancellation rate: {_percentage(metrics.cancellation_rate)} "
        "(each as a share of all recorded orders in the period)",
        f"- Completed-order revenue: ₹{metrics.revenue:,.2f}",
    ]


def _recommendations(current: Metrics, previous: Metrics | None = None) -> list[str]:
    notes: list[str] = []
    if current.total == 0:
        return ["No orders in this period. Check a longer period before drawing conclusions."]
    if current.counts["pending"]:
        notes.append(
            f"Review {current.counts['pending']} pending order(s) and prioritize follow-up; "
            "order_date alone cannot establish an hours-long delay."
        )
    if current.counts["processing"]:
        notes.append(f"Check progress on {current.counts['processing']} processing order(s).")
    if current.counts["cancelled"]:
        notes.append(
            f"Review {current.counts['cancelled']} cancelled order(s) for operational patterns; "
            "the stored status does not establish why they were cancelled."
        )
    if previous is not None and previous.total > 0:
        if current.counts["completed"] < previous.counts["completed"]:
            notes.append(
                "Completed-order count is lower than in the comparison period; "
                "check order volume and workflow before attributing a cause."
            )
        if (current.cancellation_rate is not None and previous.cancellation_rate is not None
                and current.cancellation_rate > previous.cancellation_rate):
            notes.append(
                "Cancellation rate is higher than in the comparison period; "
                "investigate individual cases rather than assuming a cause."
            )
    if not notes:
        notes.append("No pending or cancelled orders are flagged in this period; keep monitoring trends.")
    return notes


def answer_performance_question(
    *, db: Session, user: User, question: str, as_of: date | None = None
) -> str | None:
    """Return verified, role-scoped performance analysis or None for guidance.

    No ad-hoc SQL, database writes, model-generated numeric facts, or records
    from other merchants. Comparisons use equal elapsed days when possible.
    """
    if not PERFORMANCE_INTENT.search(question) or GENERAL_HELP.search(question):
        return None

    restaurant = _select_restaurant(db, user, question)
    if restaurant is None:
        return (
            "Please name one existing restaurant for the performance report, "
            "for example 'KFC order performance this month'. No report was generated."
        )

    # The normal restaurant resolver checks *known* restaurant names. Do not
    # silently substitute a merchant's own restaurant for an explicitly named
    # unknown target in a performance request.
    if user.role == "merchant":
        target = _explicit_target(question)
        if target and target.casefold().removesuffix("'s").strip() != restaurant.name.casefold():
            raise HTTPException(
                status_code=403,
                detail="You can view performance only for your assigned restaurant.",
            )

    today = as_of or date.today()
    current_window, previous_window = _windows(question, today)
    current = _get_metrics(db, restaurant.id, current_window)
    previous = _get_metrics(db, restaurant.id, previous_window) if previous_window else None

    # Database-sourced name is kept to a single line, not treated as instructions.
    safe_name = re.sub(r"\s+", " ", restaurant.name).strip()[:120]
    result = [
        f"Verified Swiggy order-performance report for {safe_name}.",
        *_render_metrics(current_window.label, current),
    ]
    if previous is not None:
        result += [
            *_render_metrics(previous_window.label, previous),
            "Period comparison (current minus previous):",
            f"- Orders: {current.total - previous.total:+d}; "
            f"Completed orders: {current.counts['completed'] - previous.counts['completed']:+d}; "
            f"Cancelled orders: {current.counts['cancelled'] - previous.counts['cancelled']:+d}",
            f"- Completed-order revenue: {current.revenue - previous.revenue:+,.2f} INR",
        ]
        if current.cancellation_rate is not None and previous.cancellation_rate is not None:
            result.append(
                f"- Cancellation-rate change: "
                f"{current.cancellation_rate - previous.cancellation_rate:+.1f} percentage points"
            )
        else:
            result.append("- Cancellation-rate change: N/A (one period has no orders)")
        if not named_months(question, today):
            result.append(
                "Comparison windows use matched elapsed days, not a partial month versus a full month."
            )
        else:
            result.append("Named-month comparisons use full calendar months.")
    result.extend(["Operational suggestions (rules-based, not causal conclusions):"])
    result.extend(f"- {note}" for note in _recommendations(current, previous))
    result.append(
        "Based on dated restaurant-linked Swiggy order records only. "
        "Amounts are recorded order values, not confirmed payments, profit or refunds. "
        "Date fields do not establish preparation times. No records were modified."
    )
    return "\n".join(result)
