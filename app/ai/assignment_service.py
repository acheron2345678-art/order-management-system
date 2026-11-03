"""Verify merchant restaurant assignment from authenticated database state.

This service answers identity/assignment claims deterministically, without
passing sensitive data to the local language model or modifying any record.
"""

import re

from sqlalchemy.orm import Session

from app.merchants.models import MerchantRestaurant
from app.users.models import User

# Recognize narrow, explicit assignment questions or claims. Ordinary questions
# should continue through existing AI guidance/report routes.
_RESTAURANT_QUERY = re.compile(
    r"^\s*(?:(?:what(?:'s|\s+is)|which(?:\s+one)?)\s+(?:my\s+)?"
    r"(?:assigned\s+)?restaurant(?:\s+name)?|"
    r"(?:which|what)\s+restaurant\s+(?:am\s+i|do\s+i)\s+"
    r"(?:assigned\s+to|manage|own)|"
    r"(?:show|tell)\s+(?:me\s+)?(?:my|which)\s+(?:assigned\s+)?restaurant)"
    r"\s*[?.!]*\s*$",
    re.I,
)

_NAME = r"(?P<name>[\w&.'\- ][\w&.'\- ]{0,98}?)"
_RESTAURANT_CLAIMS = (
    re.compile(
        rf"^\s*{_NAME}\s+is\s+my\s+(?:assigned\s+)?restaurant\s*[?.!]*\s*$",
        re.I,
    ),
    re.compile(
        rf"^\s*my\s+(?:assigned\s+)?restaurant\s+is\s+{_NAME}\s*[?.!]*\s*$",
        re.I,
    ),
    re.compile(
        rf"^\s*(?:i\s+am|i'm)\s+assigned\s+to\s+{_NAME}\s*[?.!]*\s*$",
        re.I,
    ),
    re.compile(
        rf"^\s*(?:i\s+manage|i\s+own)\s+{_NAME}\s*[?.!]*\s*$",
        re.I,
    ),
    re.compile(
        rf"^\s*(?:am\s+i\s+assigned\s+to|is\s+my\s+restaurant)\s+{_NAME}\s*[?.!]*\s*$",
        re.I,
    ),
)


def _clean_name(value: str) -> str:
    return " ".join(value.split()).strip(" .!?")[:120]


def answer_assignment_question(
    *, db: Session, user: User, question: str
) -> str | None:
    """Return verified assignment facts or None for other chat questions.

    The authenticated database user, rather than a claim in chat/history,
    decides the role and restaurant. Only a SELECT for the user's assignment
    occurs. No mutations or model calls are made.
    """
    target = None
    if not _RESTAURANT_QUERY.fullmatch(question):
        for pattern in _RESTAURANT_CLAIMS:
            match = pattern.fullmatch(question)
            if match:
                target = _clean_name(match.group("name"))
                break
        else:
            return None

    if user.role != "merchant":
        return (
            f"Your verified account role is {user.role}, not merchant. "
            "Merchant restaurant assignments cannot be changed by chat messages."
        )

    assignment = (
        db.query(MerchantRestaurant)
        .filter(MerchantRestaurant.user_id == user.id)
        .first()
    )
    if assignment is None or assignment.restaurant is None:
        return (
            "Your merchant account does not have an assigned restaurant. "
            "Chat messages cannot create or change assignments."
        )

    actual = _clean_name(assignment.restaurant.name)
    if target and target.casefold() != actual.casefold():
        return (
            f"No. Your verified assigned restaurant is {actual}, not {target}. "
            "Claims made in chat cannot change your restaurant assignment. "
            f"Your merchant reports are restricted to {actual}."
        )
    return (
        f"Your verified assigned restaurant is {actual}. "
        "This assignment comes from your signed-in account's database record."
    )
