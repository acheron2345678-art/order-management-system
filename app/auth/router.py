from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    status,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from fastapi.security import (
    OAuth2PasswordRequestForm,
)

from sqlalchemy.orm import Session

from app.auth.csrf import (
    create_csrf_token,
)

from app.auth.dependencies import (
    get_current_user,
)

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

from app.auth.refresh_service import (
    create_refresh_token_record,
    get_refresh_token_record,
    has_refresh_token_timed_out,
    is_refresh_token_valid,
    revoke_refresh_token,
    rotate_refresh_token_record,
)

from app.auth.service import (
    authenticate_user,
)

from app.auth.rate_limit import (
    clear_account_login_failures,
    get_login_retry_after,
    record_failed_login,
)

from app.core import templates

from app.core.config import (
    CSRF_COOKIE_NAME,
    JWT_ACCESS_COOKIE_NAME,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_COOKIE_SAMESITE,
    JWT_COOKIE_SECURE,
    JWT_REFRESH_COOKIE_NAME,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS,
)

from app.database import get_db

from app.users.service import (
    get_user_by_id,
)

from app.auth.registration_router import (
    router as registration_router,
)


router = APIRouter(
    tags=["authentication"]
)

router.include_router(
    registration_router
)

def get_login_destination(
    user,
):
    if user.role == "merchant":

        # Temporary destination until
        # the Merchant Dashboard is
        # added in 11E.
        return "/swiggy"

    return "/home"

def clear_auth_cookies(
    response,
):
    response.delete_cookie(
        key=JWT_ACCESS_COOKIE_NAME,
        path="/",
    )

    response.delete_cookie(
        key=JWT_REFRESH_COOKIE_NAME,
        path="/",
    )

    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
    )

    return response


def redirect_to_login(
    reason: str | None = None,
):
    login_url = "/login"

    if reason:
        login_url += (
            "?reason="
            +
            quote(
                reason,
                safe="",
            )
        )

    response = RedirectResponse(
        url=login_url,
        status_code=303,
    )

    return clear_auth_cookies(
        response
    )


def normalize_next_url(
    next_url: str | None,
):
    if not next_url:
        return "/home"

    if (
        not next_url.startswith("/")
        or next_url.startswith("//")
    ):
        return "/home"

    return next_url


def set_session_cookies(
    response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
):
    response.set_cookie(
        key=JWT_ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=(
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            * 60
        ),
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        path="/",
    )

    response.set_cookie(
        key=JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=(
            JWT_REFRESH_TOKEN_EXPIRE_DAYS
            * 24
            * 60
            * 60
        ),
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        path="/",
    )

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=(
            JWT_REFRESH_TOKEN_EXPIRE_DAYS
            * 24
            * 60
            * 60
        ),
        httponly=False,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        path="/",
    )

    return response


@router.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_current_user(
        request=request,
        db=db,
    )

    if current_user:
        return RedirectResponse(
            url=get_login_destination(
                current_user
            ),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "request": request,
            "error": None,
        },
    )


@router.post(
    "/login",
    response_class=HTMLResponse,
)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()

    retry_after = get_login_retry_after(
        request=request,
        username=username,
    )

    if retry_after:
        minutes = max(
            1,
            (retry_after + 59) // 60,
        )

        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": (
                    "Too many sign-in attempts. "
                    f"Try again in about {minutes} "
                    f"minute{'s' if minutes != 1 else ''}."
                ),
            },
            status_code=429,
            headers={
                "Retry-After": str(retry_after),
            },
        )

    user = authenticate_user(
        db=db,
        username=username,
        password=password,
    )

    if not user:
        record_failed_login(
            request=request,
            username=username,
        )

        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": (
                    "Invalid username or password"
                ),
            },
            status_code=401,
        )

    clear_account_login_failures(
        username
    )

    refresh_data = create_refresh_token(
        user_id=user.id,
    )

    create_refresh_token_record(
        db=db,
        user_id=user.id,
        token_id=refresh_data[
            "token_id"
        ],
        expires_at=refresh_data[
            "expires_at"
        ],
    )

    access_token = create_access_token(
        user_id=user.id,
        session_id=refresh_data[
            "token_id"
        ],
    )

    csrf_token = create_csrf_token()

    response = RedirectResponse(
        url=get_login_destination(
            user
        ),
        status_code=303,
    )

    return set_session_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_data[
            "token"
        ],
        csrf_token=csrf_token,
    )


@router.post(
    "/api/auth/token"
)
def create_api_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    username = form_data.username.strip()

    retry_after = get_login_retry_after(
        request=request,
        username=username,
    )

    if retry_after:
        raise HTTPException(
            status_code=(
                status.HTTP_429_TOO_MANY_REQUESTS
            ),
            detail=(
                "Too many authentication attempts. "
                "Try again later."
            ),
            headers={
                "Retry-After": str(retry_after),
            },
        )

    user = authenticate_user(
        db=db,
        username=username,
        password=form_data.password,
    )

    if not user:
        record_failed_login(
            request=request,
            username=username,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid username or password"
            ),
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )

    clear_account_login_failures(
        username
    )

    access_token = create_access_token(
        user_id=user.id,
    )

    return {
        "access_token":
            access_token,

        "token_type":
            "bearer",

        "expires_in":
            (
                JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                * 60
            ),
    }


@router.get(
    "/auth/session",
    response_class=HTMLResponse,
)
def session_refresh_page(
    request: Request,
    next_url: str = Query(
        default="/home",
        alias="next",
    ),
):
    refresh_token = request.cookies.get(
        JWT_REFRESH_COOKIE_NAME
    )

    csrf_token = request.cookies.get(
        CSRF_COOKIE_NAME
    )

    if (
        not refresh_token
        or not csrf_token
    ):
        return redirect_to_login()

    next_url = normalize_next_url(
        next_url
    )

    encoded_next = quote(
        next_url,
        safe="",
    )

    return templates.TemplateResponse(
        request=request,
        name="auth/session_refresh.html",
        context={
            "request": request,
            "csrf_token": csrf_token,
            "refresh_action": (
                "/auth/refresh"
                f"?next={encoded_next}"
            ),
        },
    )


@router.post(
    "/auth/refresh"
)
def refresh_access_token(
    request: Request,
    next_url: str = Query(
        default="/home",
        alias="next",
    ),
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(
        JWT_REFRESH_COOKIE_NAME
    )

    if not refresh_token:
        return redirect_to_login()

    payload = decode_refresh_token(
        refresh_token
    )

    if not payload:
        return redirect_to_login()

    token_id = payload.get(
        "jti"
    )

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
        return redirect_to_login()

    record = get_refresh_token_record(
        db=db,
        token_id=token_id,
    )

    if not is_refresh_token_valid(
        record
    ):
        return redirect_to_login()

    if has_refresh_token_timed_out(
        record
    ):
        revoke_refresh_token(
            db=db,
            record=record,
        )

        return redirect_to_login(
            reason="inactive"
        )

    if (
        record.user_id
        !=
        user_id
    ):
        return redirect_to_login()

    user = get_user_by_id(
        db,
        user_id,
    )

    if (
        not user
        or not user.is_active
    ):
        revoke_refresh_token(
            db=db,
            record=record,
        )

        return redirect_to_login()

    new_refresh_data = create_refresh_token(
        user_id=user.id,
    )

    new_record = rotate_refresh_token_record(
        db=db,
        old_record=record,
        user_id=user.id,
        new_token_id=new_refresh_data[
            "token_id"
        ],
        new_expires_at=new_refresh_data[
            "expires_at"
        ],
    )

    new_access_token = create_access_token(
        user_id=user.id,
        session_id=new_record.token_id,
    )

    new_csrf_token = create_csrf_token()

    next_url = normalize_next_url(
        next_url
    )

    response = RedirectResponse(
        url=next_url,
        status_code=303,
    )

    return set_session_cookies(
        response=response,
        access_token=new_access_token,
        refresh_token=new_refresh_data[
            "token"
        ],
        csrf_token=new_csrf_token,
    )


@router.post(
    "/logout"
)
def logout(
    request: Request,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(
        JWT_REFRESH_COOKIE_NAME
    )

    if refresh_token:
        payload = decode_refresh_token(
            refresh_token
        )

        if payload:
            token_id = payload.get(
                "jti"
            )

            record = get_refresh_token_record(
                db=db,
                token_id=token_id,
            )

            if (
                record
                and
                record.revoked_at is None
            ):
                revoke_refresh_token(
                    db=db,
                    record=record,
                )

    response = RedirectResponse(
        url="/login",
        status_code=303,
    )

    return clear_auth_cookies(
        response
    )
