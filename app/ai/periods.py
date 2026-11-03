"""Parse explicit named calendar months for read-only report requests.

No user-supplied SQL or arbitrary expressions. When no year is specified,
choose the most recent occurrence of that month (relative to ``as_of``).
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MONTH_WORDS = "|".join(sorted(_MONTHS, key=len, reverse=True))
MONTH_RE = re.compile(
    rf"(?<!\w)(?P<month>{_MONTH_WORDS})(?!\w)(?:[\s,]+(?P<year>(?:19|20)\d{{2}}))?",
    re.I,
)


@dataclass(frozen=True)
class NamedMonth:
    start: date
    end: date  # exclusive
    label: str


def named_months(question: str, as_of: date) -> list[NamedMonth]:
    """Return named month windows, in order mentioned, without duplicates."""
    matches = list(MONTH_RE.finditer(question))
    if not matches:
        return []

    # "September and August 2026" usually scopes both to 2026.
    explicit_years = {int(m.group("year")) for m in matches if m.group("year")}
    shared_year = next(iter(explicit_years)) if len(explicit_years) == 1 else None

    result = []
    seen = set()
    for match in matches:
        month = _MONTHS[match.group("month").lower()]
        year = int(match.group("year")) if match.group("year") else shared_year
        if year is None:
            year = as_of.year if month <= as_of.month else as_of.year - 1
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        key = (year, month)
        if key not in seen:
            result.append(NamedMonth(start, end, f"{calendar.month_name[month]} {year}"))
            seen.add(key)
    return result


def only_date_words(value: str) -> bool:
    """Don't mistake 'September and August' for a restaurant name."""
    if not MONTH_RE.search(value):
        return False
    remaining = MONTH_RE.sub(" ", value)
    remaining = re.sub(r"\b(?:and|or|vs|versus|in|for|of|the|from|to)\b", " ", remaining, flags=re.I)
    return not remaining.strip(" ,.!?\t\r\n")
