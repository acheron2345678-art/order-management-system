from datetime import (
    datetime,
    timedelta,
    timezone,
)

from uuid import uuid4

import jwt

from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from app.core.config import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET_KEY,
)


def create_access_token(
    user_id: int,
    session_id: str | None = None,
):
    now = datetime.now(
        timezone.utc
    )

    expires_at = (
        now
        +
        timedelta(
            minutes=(
                JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    if session_id:
        payload["sid"] = (
            session_id
        )

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(
    user_id: int,
):
    now = datetime.now(
        timezone.utc
    )

    expires_at = (
        now
        +
        timedelta(
            days=(
                JWT_REFRESH_TOKEN_EXPIRE_DAYS
            )
        )
    )

    token_id = uuid4().hex

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": token_id,
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return {
        "token":
            token,

        "token_id":
            token_id,

        "expires_at":
            expires_at,
    }


def decode_access_token(
    token: str,
):
    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[
                JWT_ALGORITHM
            ],
        )

        if (
            payload.get("type")
            != "access"
        ):
            return None

        if not payload.get("sub"):
            return None

        return payload

    except (
        ExpiredSignatureError,
        InvalidTokenError,
    ):
        return None


def decode_refresh_token(
    token: str,
):
    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[
                JWT_ALGORITHM
            ],
        )

        if (
            payload.get("type")
            != "refresh"
        ):
            return None

        if not payload.get("sub"):
            return None

        if not payload.get("jti"):
            return None

        return payload

    except (
        ExpiredSignatureError,
        InvalidTokenError,
    ):
        return None