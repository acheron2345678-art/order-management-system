"""Fail-closed topic enforcement for the Order Management AI assistant.

This gate runs in FastAPI *before* Ollama, semantic intent classification or
report routing. It does not make authorization decisions. The existing
role-aware report services remain responsible for restaurant access.

Scope is intentionally narrow: guidance on the deployed app and analysis of
authorized operational data. No code generation, fictional simulations or
unrelated chat. For uncertain questions we ask for an app-specific question.
"""

from __future__ import annotations

import re
import unicodedata

SCOPE_MESSAGE = (
    "I can only help with the Order Management System: orders, restaurant "
    "performance, revenue, inventory, menus, checkout and account workflows. "
    "I can't discuss unrelated topics or run fictional simulations."
)
CODE_MESSAGE = (
    "I'm the Order Management assistant, so I can explain how to use the "
    "application, but I don't write, generate or debug code."
)
WELCOME_MESSAGE = (
    "I can help with Order Management orders, statuses, revenue reports, "
    "inventory, menus, checkout and account workflows. What would you "
    "like to check?"
)
CONTEXT_MESSAGE = (
    "Please ask an Order Management question or request a verified order, "
    "revenue, performance or inventory report first."
)

# Precedence matters: code and unrelated-subject requests must be denied even
# if the user adds 'in my restaurant' to make them look in scope.
_CODE_ACTION = re.compile(
    r"\b(?:write|generate|produce|build|create|develop|implement|provide|"
    r"show|send|give|make|debug|refactor|fix|review|explain|convert|"
    r"modify|design|draft)\b.{0,105}\b(?:code|codes|source\s*code|"
    r"scripts?|snippets?|program(?:ming)?|python|javascript|typescript|"
    r"fastapi|sql|sqlalchemy|jinja2|html|css|functions?|classes?|"
    r"endpoints?|schemas?|git|github|patch|repository|migrations?|apis?)\b",
    re.I | re.S,
)
_CODE_ARTIFACT = re.compile(
    r"\b(?:source\s*code|code\s*(?:for|of|to)|full\s+code|"
    r"complete\s+code|entire\s+code|code\s+block|"
    r"python\s+script|sql\s+query|database\s+schema|"
    r"api\s+endpoint|programming\s+(?:help|tutorial)|"
    r"technical\s+(?:implementation|architecture|design)|"
    r"git\s+(?:commit|push|clone)|github\s+repo(?:sitory)?|"
    r"pull\s+request)\b",
    re.I,
)
_BUILD_FEATURE = re.compile(
    r"\b(?:build|implement|develop|code|create)\b.{0,85}"
    r"\b(?:entire|whole|full|complete)\s+(?:project|website|app|"
    r"application|feature|implementation|system)\b",
    re.I | re.S,
)
_UNRELATED_SUBJECT = re.compile(
    r"\b(?:pok[eé]mon|pikachu|charizard|mewtwo|anime|minecraft|"
    r"fortnite|video\s*games?|games?|movies?|films?|music|songs?|"
    r"stock\s+market|share\s+prices?|exchange\s+rates?|bitcoin|"
    r"crypto(?:currency)?|investing|investments?|forex|"
    r"lyrics|poems?|jokes?|riddles?|stor(?:y|ies)|fairy\s*tales?|"
    r"horoscopes?|astrology|politics|elections?|sports?|cricket|"
    r"football|weather|temperature|recipes?|tourism|dating|"
    r"celebrity|celebrities)\b",
    re.I,
)
_CREATIVE_REQUEST = re.compile(
    r"\b(?:role[ -]?play|pretend|simulat(?:e|ion|ing)|fictional|"
    r"fantasy|hypothetical|imagine|humou?r\s+me|entertain\s+me|"
    r"make\s+believe|act\s+as\s+a\s+character)\b",
    re.I,
)
_OUT_OF_SCOPE_INTENT = re.compile(
    r"\b(?:best\s+restaurants?\s+(?:near|in)|restaurants?\s+near\s+me|"
    r"restaurant\s+reviews?|places?\s+to\s+eat|"
    r"how\s+to\s+start\s+a\s+restaurant\s+business)\b",
    re.I,
)
_OPERATIONAL_WORDS = re.compile(
    r"\b(?:orders?|order\s+numbers?|swiggy|insights|inventory|stocks?|"
    r"reorder(?:ing|ed)?|restock(?:ing|ed)?|revenues?|sales|menus?|dishes|products?|"
    r"checkouts?|carts?|merchants?|clients?|customers?|admins?|"
    r"dashboards?|profiles?|usernames?|accounts?|passwords?|"
    r"logins?|log\s+in|log\s+out|logout|sign\s+in|sign\s+up|"
    r"register|registration|roles?|assignments?|"
    r"fulfill?ment|processing|pending|cancelled|canceled|completed|"
    r"cancellations?|order\s+statuses?|status\s+filters?|"
    r"amounts?|reports?|payments?|refunds?|"
    r"performance|restaurant\s+operations?|"
    r"order\s+management)\b",
    re.I,
)
_RESTAURANT_SCOPE = re.compile(r"\b(?:restaurants?|business|operations?)\b", re.I)
_OWNED_CONTEXT = re.compile(r"\b(?:i|my|our|we|us|assigned|this|the)\b", re.I)
_SELF_ANALYSIS = re.compile(
    r"^\s*(?:what|how|which)\s+(?:should|can|could)\s+"
    r"(?:i|we)\s+(?:improve|focus|prioriti[sz]e)\b",
    re.I,
)
_NAMED_PERFORMANCE = re.compile(
    r"^\s*(?:is|how\s+(?:is|well\s+is))\s+.{1,95}?\s+"
    r"(?:doing|performing|running|operating|functioning)"
    r"(?:\s+(?:well|badly|poorly|okay|ok|fine|these\s+days))?\s*[?.!]*$",
    re.I,
)
_ACCOUNT_QUESTION = re.compile(
    r"^\s*(?:who\s+am\s+i|what(?:'s|\s+is)\s+my\s+(?:name|role)|"
    r"what\s+account\s+am\s+i\s+logged\s+in\s+as)\s*[?!.]*$",
    re.I,
)
_WELCOME = re.compile(
    r"^\s*(?:hi|hello|hey|good\s+(?:morning|afternoon|evening)|"
    r"thanks|thank\s+you|bye|goodbye|help)\s*[!?.]*$",
    re.I,
)
_CONTEXTUAL_QUERY = re.compile(
    r"\b(?:that|this|those|these|it|them|previous|before|"
    r"what\s+about|how\s+about|next|first|better|improve|"
    r"focus|why|explain|compare|last\s+month|"
    r"this\s+month|previous\s+month)\b",
    re.I,
)
_MONTH_FOLLOWUP = re.compile(
    r"^(?:(?:and\s+)?(?:what|how)\s+about\s+)?"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)(?:\s+(?:19|20)\d{2})?\s*[?.!]*$",
    re.I,
)

# Applies to model *output* only. Markdown inline route names are fine;
# source code fences, raw SQL and executable snippets are never displayed.
_GENERATED_SOURCE = re.compile(
    r"```|^\s*(?:from\s+[\w.]+\s+import\s+|"
    r"import\s+[\w.]+|async\s+def\s+\w+\s*\(|def\s+\w+\s*\(|"
    r"class\s+\w+\s*[:(]|CREATE\s+TABLE\b|ALTER\s+TABLE\b|"
    r"SELECT\s+.+\s+FROM\s+|UPDATE\s+\w+\s+SET\s+|"
    r"git\s+(?:add|commit|push)|<script\b|<!DOCTYPE|<html\b|"
    r"\{%\s*extends\b)",
    re.I | re.M,
)


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()


def scope_reply(
    question: str, *, has_report_context: bool = False,
    known_restaurant_target: bool = False,
) -> str | None:
    """Return a deterministic response when outside scope; None if allowed.

    `known_restaurant_target` is determined separately from the trusted DB;
    never use a restaurant name claimed by the client as an access grant.
    """
    text = _normalized(question)
    if (_CODE_ACTION.search(text) or _CODE_ARTIFACT.search(text)
            or _BUILD_FEATURE.search(text)):
        return CODE_MESSAGE
    if (_UNRELATED_SUBJECT.search(text) or _CREATIVE_REQUEST.search(text)
            or _OUT_OF_SCOPE_INTENT.search(text)):
        return SCOPE_MESSAGE
    if _WELCOME.fullmatch(text):
        return WELCOME_MESSAGE
    if _ACCOUNT_QUESTION.fullmatch(text):
        return None
    if _SELF_ANALYSIS.match(text) or _NAMED_PERFORMANCE.fullmatch(text):
        return None
    if _OPERATIONAL_WORDS.search(text):
        return None
    if (_RESTAURANT_SCOPE.search(text) and _OWNED_CONTEXT.search(text)):
        return None
    if known_restaurant_target:
        return None
    if has_report_context and _CONTEXTUAL_QUERY.search(text):
        return None
    if _MONTH_FOLLOWUP.fullmatch(text):
        return CONTEXT_MESSAGE
    return SCOPE_MESSAGE


def disallowed_generated_text(text: str) -> bool:
    """Check for programmatic or unrelated text in either model output path."""
    return bool(
        _GENERATED_SOURCE.search(text) or _CODE_ARTIFACT.search(text)
        or _UNRELATED_SUBJECT.search(text) or _CREATIVE_REQUEST.search(text)
    )


def validated_guidance(text: str) -> str:
    """Do not expose a general-chat or code response from the LLM.

    This is defense in depth, not a substitute for the pre-model scope gate.
    """
    output = text.strip()
    if _GENERATED_SOURCE.search(output) or _CODE_ARTIFACT.search(output):
        return CODE_MESSAGE
    if _UNRELATED_SUBJECT.search(output) or _CREATIVE_REQUEST.search(output):
        return SCOPE_MESSAGE
    if not _OPERATIONAL_WORDS.search(output) and not _RESTAURANT_SCOPE.search(output):
        return SCOPE_MESSAGE
    return output
