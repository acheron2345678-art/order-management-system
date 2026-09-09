import secrets

from fastapi import (
    HTTPException,
    Request,
    status,
)

from app.core.config import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
)


SAFE_METHODS = {
    "GET",
    "HEAD",
    "OPTIONS",
}


CSRF_EXEMPT_PATHS = {
    "/login",
    "/api/auth/token",
}


def create_csrf_token():
    return secrets.token_urlsafe(32)


def _uses_bearer_auth(
    request: Request,
):
    authorization = (
        request.headers.get(
            "authorization",
            "",
        )
        .strip()
    )

    return authorization.lower().startswith(
        "bearer "
    )


async def validate_csrf(
    request: Request,
):
    method = request.method.upper()

    if method in SAFE_METHODS:
        return

    path = request.url.path

    if path in CSRF_EXEMPT_PATHS:
        return


    # =========================================
    # BEARER API AUTH
    # =========================================

    # API requests using an Authorization:
    # Bearer token do not depend on browser
    # authentication cookies, so browser CSRF
    # protection is not required for them.

    if _uses_bearer_auth(
        request
    ):
        return


    # =========================================
    # COOKIE TOKEN
    # =========================================

    cookie_token = (
        request.cookies.get(
            CSRF_COOKIE_NAME
        )
    )

    if not cookie_token:

        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="CSRF token missing",
        )


    # =========================================
    # HEADER TOKEN
    # =========================================

    submitted_token = (
        request.headers.get(
            CSRF_HEADER_NAME
        )
    )


    # =========================================
    # FORM TOKEN
    # =========================================

    if not submitted_token:

        content_type = (
            request.headers.get(
                "content-type",
                "",
            )
            .lower()
        )


        if (
            "application/x-www-form-urlencoded"
            in content_type
            or
            "multipart/form-data"
            in content_type
        ):

            form = await request.form()

            submitted_token = (
                form.get(
                    "csrf_token"
                )
            )


    # =========================================
    # TOKEN REQUIRED
    # =========================================

    if not submitted_token:

        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="CSRF token missing",
        )


    # =========================================
    # CONSTANT-TIME COMPARISON
    # =========================================

    try:

        valid = (
            secrets.compare_digest(
                str(
                    cookie_token
                ),
                str(
                    submitted_token
                ),
            )
        )

    except TypeError:

        valid = False


    if not valid:

        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="Invalid CSRF token",
        )