from datetime import date


CONTROL_CHARACTERS = {
    "\x00",
}


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

    if any(
        character in cleaned
        for character in CONTROL_CHARACTERS
    ):
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

    if any(
        character in cleaned
        for character in CONTROL_CHARACTERS
    ):
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