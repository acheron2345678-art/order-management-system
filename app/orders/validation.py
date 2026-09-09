from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from app.core.config import ORDER_STATUSES, VALID_PLATFORMS


MONEY_PLACES = Decimal("0.01")
ORDER_NUMBER_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{2,49}$"
)


def clean_required_text(
    value: str | None,
    field_name: str,
    *,
    max_length: int,
    min_length: int = 1,
) -> str:
    cleaned = (value or "").strip()

    if not cleaned:
        raise ValueError(
            f"{field_name} is required."
        )

    if "\x00" in cleaned:
        raise ValueError(
            f"{field_name} contains invalid characters."
        )

    if len(cleaned) < min_length:
        raise ValueError(
            f"{field_name} must be at least "
            f"{min_length} characters."
        )

    if len(cleaned) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed "
            f"{max_length} characters."
        )

    return cleaned


def clean_optional_text(
    value: str | None,
    field_name: str,
    *,
    max_length: int,
) -> str | None:
    cleaned = (value or "").strip()

    if not cleaned:
        return None

    if "\x00" in cleaned:
        raise ValueError(
            f"{field_name} contains invalid characters."
        )

    if len(cleaned) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed "
            f"{max_length} characters."
        )

    return cleaned


def parse_required_date(
    value: date | str | None,
    field_name: str,
) -> date:
    if isinstance(value, date):
        return value

    cleaned = str(
        value or ""
    ).strip()

    if not cleaned:
        raise ValueError(
            f"{field_name} is required."
        )

    try:
        return date.fromisoformat(
            cleaned
        )

    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid date."
        ) from exc


def validate_not_in_past(
    value: date | None,
    field_name: str,
) -> date | None:
    if (
        value is not None
        and value < date.today()
    ):
        raise ValueError(
            f"{field_name} cannot be in the past."
        )

    return value


def validate_platform(
    platform: str,
) -> str:
    platform_key = (
        platform or ""
    ).strip().lower()

    if platform_key not in VALID_PLATFORMS:
        raise ValueError(
            "Invalid platform."
        )

    return platform_key


def validate_status(
    status: str,
) -> str:
    normalized_status = (
        status or ""
    ).strip().lower()

    if normalized_status not in ORDER_STATUSES:
        raise ValueError(
            "Invalid order status."
        )

    return normalized_status


def validate_positive_id(
    value,
    field_name: str = "ID",
) -> int:
    try:
        normalized = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be a valid integer."
        ) from exc

    if normalized <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return normalized


def validate_positive_quantity(
    value,
    field_name: str = "Quantity",
) -> int:
    try:
        quantity = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be a valid integer."
        ) from exc

    if quantity <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return quantity


def validate_non_negative_integer(
    value,
    field_name: str,
) -> int:
    try:
        normalized = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be a valid integer."
        ) from exc

    if normalized < 0:
        raise ValueError(
            f"{field_name} cannot be negative."
        )

    return normalized


def validate_positive_money(
    value,
    field_name: str,
) -> Decimal:
    try:
        amount = Decimal(
            str(value)
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be a valid number."
        ) from exc

    if not amount.is_finite():
        raise ValueError(
            f"{field_name} must be a finite number."
        )

    if amount <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return amount.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def validate_order_number(
    value: str | None,
) -> str:
    order_number = clean_required_text(
        value,
        "Order number",
        min_length=3,
        max_length=50,
    )

    if not ORDER_NUMBER_PATTERN.fullmatch(
        order_number
    ):
        raise ValueError(
            "Order number may contain only letters, "
            "numbers, hyphens, and underscores, "
            "and must start with a letter or number."
        )

    return order_number