"""Read-only, session-scoped conversation orchestration for the OM assistant.

No report figures or authorization claims are taken from client history. A signed
context token remembers only report intent, selected month and restaurant id;
each follow-up re-queries the database under the authenticated user's role.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.ai.domain_service import scope_reply
from app.ai.assignment_service import answer_assignment_question
from app.ai.analysis_service import answer_analysis_question, is_analysis_request
from app.ai.data_service import (
    _mentioned_restaurants,
    _select_restaurant,
    answer_data_question,
)
from app.ai.inventory_service import answer_inventory_question
from app.ai.intent_service import eligible_for_classification, wants_grounded_analysis
from app.ai.performance_service import answer_performance_question
from app.ai.periods import named_months, only_date_words
from app.ai.service import answer_question
from app.core.config import JWT_SECRET_KEY
from app.products.models import Restaurant
from app.users.models import User

MAX_QUESTIONS = 5
CONTEXT_AGE_SECONDS = 3600
_KINDS = {"revenue", "performance", "inventory", "analysis"}
_serializer = URLSafeTimedSerializer(JWT_SECRET_KEY, salt="om-ai-followup-v1")

_NUMBERED_LINE = re.compile(r"^\s*\d{1,2}[.)]\s+(.+?)\s*$")
_FOLLOWUP_PREFIX = re.compile(
    r"^(?:what\s+about|how\s+about|and\b|also\b|what\s+if|"
    r"compare\b|versus\b|vs\.?\b|and\s+then\b)", re.I
)
_COMPARISON = re.compile(r"\b(?:compare|vs\.?|versus|comparison)\b", re.I)
_REPORT_WORDS = re.compile(
    r"\b(?:revenue|sales|orders?|completed|cancelled|cancellations?|pending|"
    r"processing|performance|trends?|inventory|stock|restock|quantit(?:y|ies)|"
    r"items?|products?)\b", re.I
)
_INVENTORY_WORDS = re.compile(r"\b(?:inventory|stock|restock|reorder|quantit(?:y|ies))\b", re.I)
_PERFORMANCE_WORDS = re.compile(r"\b(?:performance|trends?|completion\s+rate|cancellation\s+rate)\b", re.I)
_REVENUE_WORDS = re.compile(r"\b(?:revenue|sales|earnings|turnover)\b", re.I)
_ABOUT = re.compile(r"^\s*(?:and\s+)?(?:what|how)\s+about\s+(.+?)\s*[?!.]*$", re.I)
_QUESTION_WORDS = re.compile(r"^(?:what|how|which|show|compare|and|also|give|tell)\b", re.I)
_EXPLAIN_PREVIOUS = re.compile(
    r"^\s*(?:what\s+does\s+(?:that|this)\s+mean|"
    r"(?:please\s+)?explain\s+(?:that|this|those results|the results|the report)|"
    r"summari[sz]e\s+(?:that|this|the report)|"
    r"what\s+should\s+i\s+do\s+next)\s*[?.!]*$",
    re.I,
)
# Short reasoning follow-ups need a signed previous report, not client-provided
# history or claimed metrics. Without that context they remain normal chat.
_REASONING_FOLLOWUP = re.compile(
    r"^\s*(?:why\s+(?:is|was)\s+(?:that|this)\s+happening|"
    r"why\s+did\s+(?:that|this)\s+happen|"
    r"what\s+(?:might|could)\s+(?:explain|cause)\s+(?:that|this)|"
    # Status-specific WHY questions must not fall through to generic chat;
    # they require fresh, authorized performance aggregates.
    r"what\s+(?:might|could)\s+(?:explain|cause)\s+"
    r"(?:(?:the|my|our|these|those)\s+)?"
    r"(?:pending|cancelled|canceled|incomplete|uncompleted)\s+orders?|"
    r"why\s+(?:are|were)\s+"
    r"(?:(?:the|my|our|these|those)\s+)?"
    r"(?:orders?\s+pending|pending\s+orders?)|"
    r"what\s+should\s+(?:i|we)\s+(?:do|check|improve|focus\s+on|prioriti[sz]e)\s+(?:first|next)|"
    r"what(?:'s|\s+is)\s+the\s+first\s+thing\s+(?:i|we)\s+should\s+do|"
    r"what\s+does\s+(?:that|this)\s+mean\s+for\s+(?:my|our)\s+(?:restaurant|business))"
    r"\s*[?.!]*$",
    re.I,
)
_CAUSAL_FOLLOWUP = re.compile(
    r"^\s*(?:why\b|what\s+caused\b|what\s+might\s+explain\b)"
    r".*\b(?:cancelled|cancellations?|revenue|sales|orders?|performance)\b",
    re.I,
)
_EXPLICIT_REPORT_TARGET = re.compile(
    r"^\s*(?:show|display|list|give me|what is|what was|how much|check)\s+"
    r"(?P<name>[\w&.'\- ]{1,75}?)\s+"
    r"(?:order\s+)?(?:revenue|sales|performance|inventory|stock|"
    r"low[ -]stock|out[ -]of[ -]stock)\b",
    re.I,
)
_GENERIC_REPORT_TARGET = {
    "my", "my restaurant", "my restaurant's", "our restaurant", "our", "the",
    "the restaurant", "this restaurant", "total", "current", "overall",
    "the total", "the current", "all", "our current", "my current",
    "a", "restaurant", "restaurant's",
}


@dataclass(frozen=True)
class ReportContext:
    kind: str
    restaurant_id: int | None
    period: str | None  # YYYY-MM; never data or SQL


def split_questions(text: str) -> list[str]:
    """Split clearly numbered or line-separated questions, not prose paragraphs."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    numbered = [_NUMBERED_LINE.fullmatch(line) for line in lines]
    if 2 <= len(lines) <= MAX_QUESTIONS and all(numbered):
        return [m.group(1).strip(' "\'') for m in numbered]
    # Also support '1. question 2. question' on a single line.
    if len(lines) == 1 and re.match(r"^\s*1[.)]\s+", lines[0]):
        chunks = re.split(r"\s+(?=\d{1,2}[.)]\s+)", lines[0])
        matches = [_NUMBERED_LINE.fullmatch(chunk) for chunk in chunks]
        if 2 <= len(matches) <= MAX_QUESTIONS and all(matches):
            return [m.group(1).strip(' "\'') for m in matches]
    if 2 <= len(lines) <= MAX_QUESTIONS and all(
        line.endswith('?') and _QUESTION_WORDS.match(line.lstrip('"\'')) for line in lines
    ):
        return [line.strip(' "\'') for line in lines]
    return [text.strip()]


def read_context(token: str | None, user: User) -> ReportContext | None:
    if not token or len(token) > 1500:
        return None
    try:
        value = _serializer.loads(token, max_age=CONTEXT_AGE_SECONDS)
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return None
    if not isinstance(value, dict) or value.get("uid") != user.id or value.get("role") != user.role:
        return None
    kind = value.get("kind")
    rid = value.get("restaurant_id")
    period = value.get("period")
    if kind not in _KINDS or (rid is not None and (not isinstance(rid, int) or rid <= 0)):
        return None
    if period is not None:
        if not isinstance(period, str) or not re.fullmatch(r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])", period):
            return None
    return ReportContext(kind, rid, period)


def make_context(context: ReportContext | None, user: User) -> str | None:
    if context is None:
        return None
    return _serializer.dumps({
        "uid": user.id,
        "role": user.role,
        "kind": context.kind,
        "restaurant_id": context.restaurant_id,
        "period": context.period,
    })


def _previous_period(period: str) -> str:
    first = date.fromisoformat(period + "-01")
    return (first - timedelta(days=1)).strftime("%Y-%m")


def _month_string(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    return f"{calendar.month_name[month]} {year}"


def _period_of_question(question: str, today: date, previous: str | None = None) -> str | None:
    named = named_months(question, today)
    if named:
        return named[0].start.strftime("%Y-%m")
    q = question.casefold()
    if "this month" in q or "current month" in q:
        return today.strftime("%Y-%m")
    if "last month" in q or "previous month" in q:
        return _previous_period(previous or today.strftime("%Y-%m"))
    if "all time" in q or "all-time" in q or "all recorded" in q:
        return None
    return previous


def _get_stored_restaurant(db: Session, user: User, ctx: ReportContext) -> Restaurant | None:
    if user.role != "admin" or ctx.restaurant_id is None:
        return None
    return db.query(Restaurant).filter(Restaurant.id == ctx.restaurant_id).first()


def _kind_for(question: str, previous: ReportContext | None) -> str | None:
    if _INVENTORY_WORDS.search(question):
        return "inventory"
    if _PERFORMANCE_WORDS.search(question) or _COMPARISON.search(question):
        return "performance"
    if _REVENUE_WORDS.search(question):
        return "revenue"
    if re.search(r"\b(?:orders?|completed|cancelled|pending|processing)\b", question, re.I):
        return "revenue"
    if previous and (_FOLLOWUP_PREFIX.search(question) or named_months(question, date.today())):
        return previous.kind
    return None


def _unrecognized_report_target(db: Session, question: str) -> bool:
    """Catch explicitly named unknown restaurants before scoping reports.

    Other known restaurants are left to the normal role-aware resolvers, which
    reject cross-restaurant merchant requests.
    """
    match = _EXPLICIT_REPORT_TARGET.search(question)
    if not match:
        return False
    proposed = " ".join(match.group("name").split()).casefold()
    # Generic modifiers are not restaurant names. For example, "my total"
    # must not be interpreted as an unknown restaurant in a revenue request.
    generic_words = {
        "my", "our", "your", "the", "this", "all", "current", "total",
        "overall", "restaurant", "restaurants", "business", "monthly",
        "latest", "recorded", "completed", "historical", "own", "assigned",
        "available", "low", "out", "of", "last", "month", "months",
        "this", "previous", "week", "weekly", "today", "yesterday",
        "products", "product", "items", "item", "dishes", "dish", "each", "every",
    }
    normalized_words = re.findall(r"[a-z]+", proposed.replace("’", "'"))
    if (proposed in _GENERIC_REPORT_TARGET
            or (normalized_words and all(w in generic_words or w == "s" for w in normalized_words))
            or only_date_words(proposed)):
        return False
    return not bool(_mentioned_restaurants(db, question))


# Detect an explicitly named unknown target in a new semantic-analysis query.
# Never turn "How could I improve Ghost Cafe operations?" into a report for
# the merchant's own City Kitchen merely because Ghost Cafe isn't in MySQL.
_POSSIBLE_SEMANTIC_TARGET = re.compile(
    r"\b(?:for|about|at|on)\s+(?P<name>"
    r"[\w&'-]+(?:\s+[\w&'-]+){0,3})\s+"
    r"(?:restaurant\s+)?(?:operations?|performance|inventory|stock|"
    r"orders?|revenue|sales)\b", re.I,
)
_SEMANTIC_GENERIC_TARGET_WORDS = {
    "my", "our", "the", "this", "a", "an", "your", "current",
    "existing", "next", "month", "previous", "last", "overall",
    "restaurant", "business", "own", "all", "more", "future",
    "planning", "improving", "managing", "optimizing", "better",
}


def _unrecognized_semantic_target(db: Session, question: str) -> bool:
    for match in _POSSIBLE_SEMANTIC_TARGET.finditer(question):
        name = " ".join(match.group("name").split())
        words = name.casefold().split()
        # A lowercase single adjective/verb is not evidence of a restaurant
        # name ("focus on improving operations"). Two-word names such as
        # "ghost cafe" can still be detected before merchant fallback.
        if (all(word in _SEMANTIC_GENERIC_TARGET_WORDS for word in words)
                or (len(words) == 1 and name[0].islower())):
            continue
        known = _mentioned_restaurants(db, name)
        if not any(item.name.casefold() == name.casefold() for item in known):
            return True
    return False



def _looks_like_named_target(question: str, today: date) -> bool:
    """Unknown explicit target must not inherit a previous restaurant."""
    # E.g. 'What about Unknown Cafe?' is not a date follow-up.
    match = _ABOUT.fullmatch(question)
    if match:
        term = match.group(1).strip()
        if only_date_words(term) or re.fullmatch(
            r"(?:this|last|previous|next)\s+(?:month|week)|(?:today|yesterday)", term, re.I
        ):
            return False
        if _REPORT_WORDS.search(term):
            return False
        return True
    return False


def _followup_question(
    *, db: Session, user: User, question: str,
    previous: ReportContext | None, today: date,
) -> tuple[str, str | None]:
    """Reformulate metadata-only followups; return (query, inferred_kind)."""
    if previous is None:
        return question, None

    kind = _kind_for(question, previous)
    explanation = bool(_EXPLAIN_PREVIOUS.fullmatch(question))
    cause_question = bool(_CAUSAL_FOLLOWUP.match(question))
    reasoning_followup = bool(_REASONING_FOLLOWUP.fullmatch(question))
    if reasoning_followup:
        # Re-run authorization-scoped queries and let Qwen explain verified
        # aggregates. Do not transmit old model prose or purported data.
        kind = "analysis"
    if explanation:
        kind = previous.kind
    if cause_question:
        kind = "performance"
    # A broad decision-support question is not merely an instruction to
    # redisplay the old report. Let the optional intent classifier assess it.
    # Preserve deterministic date comparisons and established WHY follow-ups.
    if (not (explanation or cause_question or reasoning_followup)
            and eligible_for_classification(question, has_report_context=True)
            and not (_COMPARISON.search(question) and named_months(question, today))):
        return question, None
    relevant = bool(
        explanation or cause_question or reasoning_followup
        or
        _FOLLOWUP_PREFIX.search(question)
        or named_months(question, today)
        or re.search(r"\b(?:in|for|during)\s+(?:this|last|previous)\s+month\b", question, re.I)
        or re.match(r"^\s*(?:how many|what was|show|which|what is)\b", question, re.I)
        and _REPORT_WORDS.search(question)
    )
    if not kind or not relevant:
        return question, None

    # Never erase an explicitly supplied restaurant in a complete report query.
    # Otherwise "Show Unknown Cafe inventory" might silently become "my inventory".
    if _unrecognized_report_target(db, question):
        return question, "unknown-restaurant"
    named = _mentioned_restaurants(db, question)
    if len(named) > 1:
        return question, None
    if named:
        target = named[0].name
    else:
        if _looks_like_named_target(question, today):
            # Keep unknown-name claims away from silently defaulting to the
            # authenticated merchant. Return a deterministic clarification.
            return question, "unknown-restaurant"
        r = _get_stored_restaurant(db, user, previous)
        target = r.name if r else "my restaurant"
        if user.role == "admin" and r is None:
            return question, None

    if kind == "inventory":
        if named_months(question, today) or re.search(r"\b(?:last|previous|this)\s+month\b", question, re.I):
            return question, "historical-inventory"
        return f"Show {target} inventory summary", kind

    new_period = _period_of_question(question, today, previous.period)
    period_text = f" for {_month_string(new_period)}" if new_period else " all time"

    if reasoning_followup:
        # Preserve the user's objective but never assume a cause or previous
        # numbers. The model sees only freshly computed aggregate facts.
        return (
            f"Assess {target} restaurant performance{period_text} and explain "
            "verified observations, possible concerns, and the first useful "
            "check. Do not assert a cause without evidence.",
            "analysis",
        )
    if cause_question and previous.period:
        # Never invent causal explanations. Show comparable verified figures
        # and existing non-causal operational recommendations instead.
        return (
            f"Compare {target} order performance for "
            f"{_month_string(previous.period)} and "
            f"{_month_string(_previous_period(previous.period))}",
            "performance",
        )
    if _COMPARISON.search(question) and previous.period:
        # Compare the last selected month against the requested month.
        compared = new_period or _previous_period(previous.period)
        if compared == previous.period:
            compared = _previous_period(previous.period)
        return (
            f"Compare {target} order performance for "
            f"{_month_string(previous.period)} and {_month_string(compared)}",
            "performance",
        )
    if kind == "analysis":
        return f"Assess {target} performance{period_text}", kind
    if kind == "performance":
        return f"Show {target} order performance{period_text}", kind
    return f"Show {target} order summary{period_text}", kind


async def answer_conversation(
    *, db: Session, user: User, question: str,
    history: list[dict], context_token: str | None = None,
    as_of: date | None = None,
) -> tuple[str, str | None]:
    """Dispatch up to five questions, returning response and signed context.

    Every individual query uses the existing authorization-scoped services.
    The token is never treated as a permission grant or a source of figures.
    """
    today = as_of or date.today()
    prior = read_context(context_token, user)
    questions = split_questions(question)
    responses: list[str] = []
    for raw in questions:
        if prior is None and _REASONING_FOLLOWUP.fullmatch(raw):
            responses.append(
                "I need a verified report before interpreting that. Ask for "
                "your restaurant performance for a specific month, then ask "
                "what it means or what to check first."
            )
            continue
        # Enforce the application's subject boundary *before* any Ollama call,
        # optional classifier or report resolver. Previous browser history is
        # untrusted; only a signed, account-bound report token may authorize
        # a contextual reporting follow-up (never another restaurant's data).
        scope = scope_reply(raw, has_report_context=prior is not None)
        if scope is not None:
            responses.append(scope)
            continue
        # This also checks the first question when there is no prior context.
        if _unrecognized_report_target(db, raw):
            if user.role == "merchant":
                raise HTTPException(
                    status_code=403,
                    detail="You can view reports only for your assigned restaurant.",
                )
            responses.append(
                "I couldn't verify that restaurant name. Please use the exact "
                "name of an existing restaurant. No report was generated."
            )
            continue
        query, special = _followup_question(
            db=db, user=user, question=raw, previous=prior, today=today
        )
        if special == "historical-inventory":
            result = (
                "Inventory shows current stock quantities, not historical snapshots. "
                "I cannot verify inventory quantities for a past month from this report."
            )
            responses.append(result)
            continue
        if special == "unknown-restaurant":
            if user.role == "merchant":
                raise HTTPException(
                    status_code=403,
                    detail="You can view reports only for your assigned restaurant.",
                )
            responses.append(
                "I couldn't verify that restaurant name. No report was generated."
            )
            continue

        # An optional structured-output Ollama classifier recognizes broader
        # first-person operational questions. Only its *intent* is accepted;
        # the ORIGINAL question still goes through FastAPI's authenticated
        # restaurant resolver and date parser. No model-selected SQL or scope.
        semantic_analysis = False
        if (user.role in ("merchant", "admin")
                and special is None
                and not is_analysis_request(query)
                and eligible_for_classification(raw, has_report_context=prior is not None)):
            semantic_analysis = await wants_grounded_analysis(raw)

        if semantic_analysis and _unrecognized_semantic_target(db, raw):
            if user.role == "merchant":
                raise HTTPException(
                    status_code=403,
                    detail="You can view reports only for your assigned restaurant.",
                )
            responses.append(
                "I couldn't verify that restaurant name. No report was generated."
            )
            continue

        # Interpretation questions use actual scoped metrics plus Qwen. This
        # must run before the assignment-claim matcher and report templates.
        # The signed previous context contains only selection metadata.
        analysis = await answer_analysis_question(
            db=db, user=user, question=query,
            previous_month=prior.period if prior else None,
            restaurant_id_hint=(prior.restaurant_id if prior and user.role == "admin" else None),
            as_of=today,
            # The rewritten query is used for scoping; the original question
            # tells Qwen what the user actually needs from this follow-up.
            user_intent=raw if special == "analysis" else None,
            concise=(special == "analysis" or semantic_analysis) and prior is not None,
            force_analysis=semantic_analysis,
        ) if (is_analysis_request(query) or semantic_analysis) else None
        result = None
        dispatched_kind: str | None = None
        if analysis is not None:
            result, analysis_period, analysis_restaurant_id = analysis
            dispatched_kind = "analysis" if analysis_restaurant_id is not None else None
            if dispatched_kind:
                prior = ReportContext(
                    kind="analysis",
                    restaurant_id=analysis_restaurant_id if user.role == "admin" else None,
                    period=analysis_period,
                )
        if result is None:
            result = answer_assignment_question(db=db, user=user, question=query)
        if result is None:
            result = answer_performance_question(db=db, user=user, question=query, as_of=today)
            if result is not None:
                dispatched_kind = "performance"
        if result is None:
            result = answer_data_question(db=db, user=user, question=query, as_of=today)
            if result is not None:
                dispatched_kind = "revenue"
        if result is None:
            result = answer_inventory_question(db=db, user=user, question=query)
            if result is not None:
                dispatched_kind = "inventory"
        if result is None:
            # The fallback is app guidance only. Do not pass browser-supplied
            # previous assistant text, which can contain fake instructions or
            # unverified claims about the app and user identity.
            result = await answer_question(
                question=query, role=user.role, username=user.username,
                history=[],
            )

        if dispatched_kind is not None and dispatched_kind != "analysis" and not result.startswith("Please name one"):
            restaurant = _select_restaurant(db, user, query)
            if restaurant is not None:
                prior = ReportContext(
                    kind=dispatched_kind,
                    restaurant_id=restaurant.id if user.role == "admin" else None,
                    period=(
                        _period_of_question(query, today, None)
                        if dispatched_kind != "inventory" else None
                    ),
                )
        responses.append(result)
        if len(questions) > 1:
            history = [*history, {"role": "user", "content": raw},
                       {"role": "assistant", "content": result[:1200]}][-8:]

    if len(responses) == 1:
        answer = responses[0]
    else:
        answer = "\n\n".join(
            f"{idx}. {raw}\n{value}"
            for idx, (raw, value) in enumerate(zip(questions, responses), start=1)
        )
    return answer[:18000], make_context(prior, user)
