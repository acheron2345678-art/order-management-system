from urllib.parse import quote

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)

from fastapi.security import (
    OAuth2PasswordBearer,
)

from sqlalchemy.orm import Session

from app.auth.jwt import (
    decode_access_token,
)

from app.auth.refresh_service import (
    get_refresh_token_record,
    is_refresh_token_active,
    touch_refresh_token,
)

from app.core.config import (
    JWT_ACCESS_COOKIE_NAME,
    JWT_REFRESH_COOKIE_NAME,
)

from app.database import get_db

from app.users.models import User

from app.users.service import (
    get_user_by_id,
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    auto_error=False,
)


def get_user_from_token(
    db: Session,
    token: str | None,
):
    if not token:
        return None

    payload = decode_access_token(
        token
    )

    if not payload:
        return None

    user_id = payload.get(
        "sub"
    )

    try:

        user_id = int(
            user_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


    user = get_user_by_id(
        db,
        user_id,
    )


    if not user:
        return None


    if not user.is_active:
        return None


    return user


def get_current_user(
    request: Request,
    db: Session = Depends(
        get_db
    ),
):
    access_token = (
        request.cookies.get(
            JWT_ACCESS_COOKIE_NAME
        )
    )


    if not access_token:
        return None


    payload = decode_access_token(
        access_token
    )


    if not payload:
        return None


    user_id = payload.get(
        "sub"
    )


    session_id = payload.get(
        "sid"
    )


    try:

        user_id = int(
            user_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


    if not session_id:
        return None


    record = get_refresh_token_record(
        db=db,
        token_id=session_id,
    )


    if not record:
        return None


    if (
        record.user_id
        !=
        user_id
    ):
        return None


    if not is_refresh_token_active(
        record
    ):
        return None


    user = get_user_by_id(
        db,
        user_id,
    )


    if (
        not user
        or not user.is_active
    ):
        return None


    return user


def require_authenticated_user(
    request: Request,
    db: Session = Depends(
        get_db
    ),
):
    access_token = (
        request.cookies.get(
            JWT_ACCESS_COOKIE_NAME
        )
    )


    # =========================================
    # VALID ACCESS TOKEN
    # =========================================

    if access_token:

        payload = decode_access_token(
            access_token
        )


        if payload:

            user_id = payload.get(
                "sub"
            )


            session_id = payload.get(
                "sid"
            )


            try:

                user_id = int(
                    user_id
                )

            except (
                TypeError,
                ValueError,
            ):

                user_id = None


            if (
                user_id
                and
                session_id
            ):

                record = (
                    get_refresh_token_record(
                        db=db,
                        token_id=session_id,
                    )
                )


                if (
                    record
                    and
                    record.user_id
                    ==
                    user_id
                    and
                    is_refresh_token_active(
                        record
                    )
                ):

                    user = (
                        get_user_by_id(
                            db,
                            user_id,
                        )
                    )


                    if (
                        user
                        and
                        user.is_active
                    ):

                        touch_refresh_token(
                            db=db,
                            record=record,
                        )


                        return user


    # =========================================
    # ACCESS TOKEN EXPIRED
    # =========================================

    refresh_token = (
        request.cookies.get(
            JWT_REFRESH_COOKIE_NAME
        )
    )


    if refresh_token:

        requested_url = (
            request.url.path
        )


        if request.url.query:

            requested_url += (
                "?"
                +
                request.url.query
            )


        encoded_next = quote(
            requested_url,
            safe="",
        )


        # IMPORTANT:
        #
        # This GET page does NOT refresh tokens.
        #
        # It displays a secure session renewal
        # screen. The actual refresh is performed
        # using POST /auth/refresh.

        raise HTTPException(
            status_code=303,
            headers={
                "Location": (
                    "/auth/session"
                    f"?next={encoded_next}"
                )
            },
        )


    # =========================================
    # NO SESSION
    # =========================================

    raise HTTPException(
        status_code=303,
        headers={
            "Location":
                "/login"
        },
    )


def require_admin(
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    if (
        current_user.role
        !=
        "admin"
    ):

        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )


    return current_user


def require_client(
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    if (
        current_user.role
        !=
        "client"
    ):

        raise HTTPException(
            status_code=403,
            detail="Client access required",
        )


    return current_user


def get_current_api_user(
    token: str | None = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(
        get_db
    ),
):
    if not token:

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Not authenticated",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )


    user = get_user_from_token(
        db=db,
        token=token,
    )


    if not user:

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid or expired token"
            ),
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )


    return user


def require_admin_api(
    current_user: User = Depends(
        get_current_api_user
    ),
):
    if (
        current_user.role
        !=
        "admin"
    ):

        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )


    return current_user


def require_client_api(
    current_user: User = Depends(
        get_current_api_user
    ),
):
    if (
        current_user.role
        !=
        "client"
    ):

        raise HTTPException(
            status_code=403,
            detail="Client access required",
        )


    return current_user