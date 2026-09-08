GMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
}


def normalize_email(
    email: str | None,
) -> str:

    if not email:
        return ""

    return email.strip().lower()


def is_gmail_address(
    email: str | None,
) -> bool:

    email = normalize_email(
        email
    )

    if not email:
        return False

    if email.count("@") != 1:
        return False

    local_part, domain = (
        email.rsplit("@", 1)
    )

    if not local_part:
        return False

    return domain in GMAIL_DOMAINS


def require_gmail_address(
    email: str | None,
) -> str:

    email = normalize_email(
        email
    )

    if not is_gmail_address(
        email
    ):
        raise ValueError(
            "Only Gmail accounts are supported. "
            "Please use an @gmail.com address."
        )

    return email