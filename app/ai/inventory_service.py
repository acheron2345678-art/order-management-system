"""Read-only, authorization-scoped inventory reporting for the AI assistant.

All figures come from the permitted restaurant's products table. Chat text never
changes the signed-in user's restaurant assignment or database permissions.
"""

import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.data_service import _select_restaurant
from app.products.models import Product
from app.users.models import User

INVENTORY_TERMS = re.compile(
    r"\b(?:inventory|stock|stockouts?|restock(?:ing)?|reorder(?:ing)?|"
    r"low[ -]stock|out[ -]of[ -]stock)\b|"
    r"\b(?:quantit(?:y|ies)|units?)\b.*\b(?:products?|items?|dishes)\b|"
    r"\b(?:products?|items?|dishes)\b.*\b(?:quantit(?:y|ies)|units?|stock)\b",
    re.I,
)
GENERAL_ADVICE = re.compile(
    r"\b(?:how (?:do|can|should) (?:i|we)|tips?|strategies|"
    r"best practices|explain|guide|steps? to|why is|what does)\b",
    re.I,
)
ITEMIZED_TERMS = re.compile(
    r"\b(?:quantit(?:y|ies)|units?|each|every|per[ -]product|"
    r"individual|how many of each|list all products)\b",
    re.I,
)
MAX_ATTENTION_ITEMS = 12
MAX_PRODUCT_ITEMS = 30

# Detect explicit restaurant targets in common inventory commands even when
# the named restaurant is *not present* in the database. Otherwise a merchant's
# request for an unknown/outside restaurant could silently return their own data.
_RESTAURANT_TARGET_PATTERNS = (
    re.compile(
        r"^\s*(?:what(?:'s|\s+is)|how much)\s+"
        r"(?P<name>[\w&.'\- ]{1,90}?)\s+"
        r"(?:inventory|stock)\b",
        re.I,
    ),
    re.compile(
        r"^\s*(?:please\s+)?(?:show|display|give(?:\s+me)?|list|check|find)\s+"
        r"(?:me\s+)?(?:the\s+)?(?P<name>[\w&.'\- ]{1,90}?)\s+"
        r"(?:inventory|low[ -]stock|out[ -]of[ -]stock|stock(?:\s+(?:levels?|counts?|quantit(?:y|ies)))?)\b",
        re.I,
    ),
    re.compile(
        r"^\s*(?!(?:show|display|give|list|check|find|what|which|how|tell)\b)"
        r"(?P<name>[\w&.'\- ]{1,90}?)\s+"
        r"(?:inventory|low[ -]stock|out[ -]of[ -]stock|stock(?:\s+(?:levels?|counts?|quantit(?:y|ies)))?)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:inventory|low[ -]stock(?:\s+(?:items?|products?))?|"
        r"out[ -]of[ -]stock(?:\s+(?:items?|products?))?|"
        r"stock(?:\s+(?:levels?|counts?|quantit(?:y|ies)))?)\s+"
        r"(?:of|for|at|in)\s+(?P<name>[\w&.'\- ]{1,90}?)\s*[?.!]*$",
        re.I,
    ),
    re.compile(
        r"\b(?:in|at|for|of)\s+(?P<name>[\w&.'\- ]{1,90}?)\s+"
        r"(?:inventory|low[ -]stock|out[ -]of[ -]stock|stock(?:\s+(?:levels?|counts?|quantit(?:y|ies)))?)\b",
        re.I,
    ),
)
_GENERIC_TARGETS = {
    "my", "our", "your", "the", "all", "each", "every", "current",
    "assigned", "my restaurant", "our restaurant", "my assigned restaurant",
    "our assigned restaurant", "the restaurant", "this restaurant",
    "all products", "all items", "the products", "the items",
    "every product", "each product", "all dishes", "every dish",
    "low", "high", "out", "stock", "inventory", "total",
}


def _safe_name(name: str) -> str:
    """Keep database-provided names from injecting extra output lines."""
    return re.sub(r"\s+", " ", name).strip()[:100]


def _explicit_restaurant_name(question: str) -> str | None:
    for pattern in _RESTAURANT_TARGET_PATTERNS:
        match = pattern.search(question)
        if not match:
            continue
        candidate = re.sub(r"\s+", " ", match.group("name")).strip(" .?!")
        if candidate.casefold() in _GENERIC_TARGETS:
            continue
        return candidate or None
    return None


def _verify_merchant_target(question: str, user: User, restaurant_name: str) -> None:
    """Reject unknown or other restaurants *before* reading inventory rows.

    Known restaurant names are checked by `_select_restaurant`; this extra check
    closes its fallback behavior when an explicitly named restaurant does not
    exist in the local restaurants table.
    """
    if user.role != "merchant":
        return
    explicit = _explicit_restaurant_name(question)
    if explicit is None:
        return
    # Allow the possessive form of the owned restaurant's name.
    normalized = explicit.casefold().removesuffix("'s").strip()
    if normalized != restaurant_name.casefold():
        raise HTTPException(
            status_code=403,
            detail="You can view inventory only for your assigned restaurant.",
        )


def answer_inventory_question(*, db: Session, user: User, question: str) -> str | None:
    """Return verified inventory data, or None for ordinary guidance questions.

    Reports include only active Swiggy products of one permitted restaurant.
    A request for per-product quantities returns individual stock counts rather
    than being routed to a probabilistic model. No database writes are issued.
    """
    if not INVENTORY_TERMS.search(question) or GENERAL_ADVICE.search(question):
        return None

    restaurant = _select_restaurant(db, user, question)
    if restaurant is None:
        return (
            "Please name one restaurant (an existing one) to report on, for example: "
            "'KFC inventory summary'. No inventory data was retrieved."
        )
    _verify_merchant_target(question, user, restaurant.name)

    products = (
        db.query(Product)
        .filter(
            Product.restaurant_id == restaurant.id,
            Product.platform.ilike("swiggy"),
            Product.is_active.is_(True),
        )
        .order_by(Product.stock_quantity.asc(), Product.id.asc())
        .all()
    )

    out_of_stock = [p for p in products if p.stock_quantity <= 0]
    low_stock = [p for p in products if 0 < p.stock_quantity <= p.reorder_level]
    healthy = [p for p in products if p.stock_quantity > p.reorder_level]
    total_units = sum(max(0, p.stock_quantity) for p in products)
    heading = (
        f"Verified inventory for {restaurant.name} (active Swiggy products only).\n"
        f"Products: {len(products)}; Total units: {total_units}; "
        f"Out of stock: {len(out_of_stock)}; "
        f"Low stock: {len(low_stock)}; Above reorder level: {len(healthy)}."
    )

    if ITEMIZED_TERMS.search(question):
        lines = [heading, "Current stock quantity by product:"]
        for p in products[:MAX_PRODUCT_ITEMS]:
            status = (
                "OUT OF STOCK" if p.stock_quantity <= 0 else
                "LOW STOCK" if p.stock_quantity <= p.reorder_level else "IN STOCK"
            )
            lines.append(
                f"- {_safe_name(p.product_name)} (ID {p.id}): "
                f"{p.stock_quantity} unit(s) available; "
                f"reorder level {p.reorder_level}; {status}."
            )
        if not products:
            lines.append("No active Swiggy products found for this restaurant.")
        if len(products) > MAX_PRODUCT_ITEMS:
            lines.append(
                f"Showing {MAX_PRODUCT_ITEMS} of {len(products)} products. "
                "Open /merchant/inventory to view the full inventory."
            )
        lines.append("These are current database values. No records were modified.")
        return "\n".join(lines)

    needs_attention = sorted(
        [*out_of_stock, *low_stock],
        key=lambda p: (
            0 if p.stock_quantity <= 0 else 1,
            p.stock_quantity - p.reorder_level,
            p.stock_quantity,
            p.id,
        ),
    )
    if not needs_attention:
        return (
            heading
            + "\nNo active products are at or below their reorder levels. "
            "Ask 'stock quantity of each product' to see individual stock counts. "
            "Inactive or non-Swiggy products are excluded. "
            "No inventory records were modified."
        )

    lines = [heading, "Items needing attention (highest priority first):"]
    for product in needs_attention[:MAX_ATTENTION_ITEMS]:
        suggested_units = max(0, product.reorder_level + 1 - product.stock_quantity)
        status = "OUT OF STOCK" if product.stock_quantity <= 0 else "LOW STOCK"
        lines.append(
            f"- {_safe_name(product.product_name)} (ID {product.id}): {status}; "
            f"available {product.stock_quantity}; reorder level {product.reorder_level}; "
            f"{suggested_units} unit(s) to rise above that level."
        )
    if len(needs_attention) > MAX_ATTENTION_ITEMS:
        lines.append(
            f"...and {len(needs_attention) - MAX_ATTENTION_ITEMS} additional items needing attention."
        )
    lines.append(
        "Suggestions are threshold-based, not demand forecasts or automatic "
        "purchase orders. Inactive and non-Swiggy products are excluded; "
        "no inventory records were modified."
    )
    return "\n".join(lines)
