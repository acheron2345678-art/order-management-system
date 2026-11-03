"""Verified, read-only guidance for order-status updates.

Paths and permissions match the shipped FastAPI routers. The status transition
matrix is imported from the same config used by the update endpoints, rather
than invented by an LLM. Never accesses or mutates order records.
"""

import re

from app.core.config import ORDER_STATUSES, ORDER_STATUS_TRANSITIONS


_UPDATE_ORDER_STATUS = re.compile(
    r"\b(?:change|update|set|edit|modify|move)\b.{0,100}"
    r"\b(?:order\s+)?status(?:es)?\b|"
    r"\b(?:change|update|set|edit|modify|move)\b.{0,100}"
    r"\borders?\b.{0,50}\bstatus(?:es)?\b|"
    r"\bstatus(?:es)?\b.{0,55}\b(?:change|update|edit|modify)\b",
    re.IGNORECASE | re.DOTALL,
)


def _transitions() -> str:
    pieces = []
    for current in ORDER_STATUSES:
        next_states = [s for s in ORDER_STATUSES
                       if s in ORDER_STATUS_TRANSITIONS.get(current, set())]
        if next_states:
            pieces.append(f"- **{current}** → " + " or ".join(f"**{s}**" for s in next_states))
        else:
            pieces.append(f"- **{current}** → final; no further status change")
    return "\n".join(pieces)


def verified_workflow_answer(question: str, role: str) -> str | None:
    """Answer order status editing requests using deployed routes and rules.

    Users may ask how another role works; do not give clients editing access.
    Role comes from the authenticated backend, never from the question.
    """
    if not _UPDATE_ORDER_STATUS.search(question):
        return None

    if role == "merchant":
        route = (
            "1. Open **/merchant/orders** and select an order assigned to your restaurant.\n"
            "2. Open its detail page at **/merchant/orders/{order_id}**.\n"
            "3. In **Update Status**, choose one of the offered next statuses.\n"
            "4. Select **Update Order Status** to submit the change.\n\n"
            "The available options depend on the order's recorded status."
        )
    elif role == "admin":
        route = (
            "1. Open **/swiggy/orders** or **/insights/orders**.\n"
            "2. Find the order and open its **Edit** page.\n"
            "3. Choose one of the available status values in the order form, then save.\n\n"
            "These editing controls are for administrators, not clients."
        )
    else:
        route = (
            "Client accounts can view their authorized orders, but cannot "
            "change order statuses. A merchant can change statuses for orders "
            "at their assigned restaurant; admins can edit eligible platform orders."
        )

    return (
        "**Updating an order status**\n\n"
        + route
        + "\n\n**Allowed status transitions**\n\n"
        + _transitions()
        + "\n\nThis assistant is read-only and cannot make the change for you."
    )
