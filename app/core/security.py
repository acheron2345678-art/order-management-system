from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


COMMON_PASSWORDS = {
    "password",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty123",
    "admin123",
    "letmein123",
    "welcome123",
}


def validate_password(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
) -> str:
    if not isinstance(password, str):
        raise ValueError(
            "Password is required."
        )

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be no more than {MAX_PASSWORD_LENGTH} characters long."
        )

    if not password.strip():
        raise ValueError(
            "Password cannot contain only spaces."
        )

    normalized_password = (
        password.casefold()
    )

    if normalized_password in COMMON_PASSWORDS:
        raise ValueError(
            "Choose a less common password or passphrase."
        )

    if username:
        normalized_username = (
            username.strip().casefold()
        )

        if (
            len(normalized_username) >= 4
            and normalized_username
            in normalized_password
        ):
            raise ValueError(
                "Password must not contain the username."
            )

    if email:
        email_local_part = (
            email.split("@", 1)[0]
            .strip()
            .casefold()
        )

        if (
            len(email_local_part) >= 4
            and email_local_part
            in normalized_password
        ):
            raise ValueError(
                "Password must not contain the email name."
            )

    return password


def hash_password(
    password: str,
) -> str:
    return password_hash.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return password_hash.verify(
            plain_password,
            hashed_password,
        )
    except Exception:
        return False
