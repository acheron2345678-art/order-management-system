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


router = APIRouter(
    tags=[
        "authentication"
    ]
)


# =========================================
# AUTH COOKIE HELPERS
# =========================================

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
        or
        next_url.startswith("//")
    ):

        return "/home"


    return next_url


def set_session_cookies(
    response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
):

    # =========================================
    # ACCESS TOKEN
    # =========================================

    response.set_cookie(
        key=JWT_ACCESS_COOKIE_NAME,
        value=access_token,

        max_age=(
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            *
            60
        ),

        httponly=True,

        secure=JWT_COOKIE_SECURE,

        samesite=JWT_COOKIE_SAMESITE,

        path="/",
    )


    # =========================================
    # REFRESH TOKEN
    # =========================================

    response.set_cookie(
        key=JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,

        max_age=(
            JWT_REFRESH_TOKEN_EXPIRE_DAYS
            *
            24
            *
            60
            *
            60
        ),

        httponly=True,

        secure=JWT_COOKIE_SECURE,

        samesite=JWT_COOKIE_SAMESITE,

        path="/",
    )


    # =========================================
    # CSRF TOKEN
    # =========================================

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,

        max_age=(
            JWT_REFRESH_TOKEN_EXPIRE_DAYS
            *
            24
            *
            60
            *
            60
        ),

        httponly=False,

        secure=JWT_COOKIE_SECURE,

        samesite=JWT_COOKIE_SAMESITE,

        path="/",
    )


    return response


# =========================================
# LOGIN PAGE
# =========================================

@router.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),
):

    current_user = get_current_user(
        request=request,
        db=db,
    )


    if current_user:

        return RedirectResponse(
            url="/home",
            status_code=303,
        )


    return templates.TemplateResponse(
        request=request,

        name="auth/login.html",

        context={

            "request":
                request,

            "error":
                None,

        },
    )


# =========================================
# LOGIN
# =========================================

@router.post(
    "/login",
    response_class=HTMLResponse,
)
def login(
    request: Request,

    username: str = Form(...),

    password: str = Form(...),

    db: Session = Depends(
        get_db
    ),
):

    username = (
        username.strip()
    )


    user = authenticate_user(
        db=db,
        username=username,
        password=password,
    )


    if not user:

        return templates.TemplateResponse(
            request=request,

            name="auth/login.html",

            context={

                "request":
                    request,

                "error":
                    "Invalid username or password",

            },

            status_code=401,
        )


    # =========================================
    # REFRESH TOKEN
    # =========================================

    refresh_data = (
        create_refresh_token(
            user_id=user.id,
        )
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


    # =========================================
    # ACCESS TOKEN
    # =========================================

    access_token = (
        create_access_token(
            user_id=user.id,

            session_id=refresh_data[
                "token_id"
            ],
        )
    )


    # =========================================
    # CSRF TOKEN
    # =========================================

    csrf_token = (
        create_csrf_token()
    )


    response = RedirectResponse(
        url="/home",
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


# =========================================
# API TOKEN
# =========================================

@router.post(
    "/api/auth/token"
)
def create_api_token(
    form_data: OAuth2PasswordRequestForm = Depends(),

    db: Session = Depends(
        get_db
    ),
):

    user = authenticate_user(
        db=db,

        username=(
            form_data.username.strip()
        ),

        password=form_data.password,
    )


    if not user:

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


    access_token = (
        create_access_token(
            user_id=user.id,
        )
    )


    return {

        "access_token":
            access_token,

        "token_type":
            "bearer",

        "expires_in":
            (
                JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                *
                60
            ),

    }


# =========================================
# SESSION RENEWAL PAGE
# =========================================
#
# IMPORTANT:
#
# This GET endpoint does NOT rotate tokens.
# It only displays a page containing a
# CSRF-protected POST form.
#
# =========================================

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

    refresh_token = (
        request.cookies.get(
            JWT_REFRESH_COOKIE_NAME
        )
    )


    csrf_token = (
        request.cookies.get(
            CSRF_COOKIE_NAME
        )
    )


    if (
        not refresh_token
        or
        not csrf_token
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

            "request":
                request,

            "csrf_token":
                csrf_token,

            "refresh_action":
                (
                    "/auth/refresh"
                    f"?next={encoded_next}"
                ),

        },
    )


# =========================================
# REFRESH SESSION
# =========================================
#
# TOKEN ROTATION NOW HAPPENS ONLY THROUGH
# POST AND THEREFORE PASSES THROUGH THE
# GLOBAL CSRF CHECK.
#
# =========================================

@router.post(
    "/auth/refresh"
)
def refresh_access_token(
    request: Request,

    next_url: str = Query(
        default="/home",
        alias="next",
    ),

    db: Session = Depends(
        get_db
    ),
):

    # =========================================
    # READ REFRESH TOKEN
    # =========================================

    refresh_token = (
        request.cookies.get(
            JWT_REFRESH_COOKIE_NAME
        )
    )


    if not refresh_token:

        return redirect_to_login()


    # =========================================
    # DECODE
    # =========================================

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


    # =========================================
    # DATABASE SESSION RECORD
    # =========================================

    record = get_refresh_token_record(
        db=db,
        token_id=token_id,
    )


    if not is_refresh_token_valid(
        record
    ):

        return redirect_to_login()


    # =========================================
    # IDLE TIMEOUT
    # =========================================

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


    # =========================================
    # TOKEN OWNERSHIP
    # =========================================

    if (
        record.user_id
        !=
        user_id
    ):

        return redirect_to_login()


    # =========================================
    # USER VALIDATION
    # =========================================

    user = get_user_by_id(
        db,
        user_id,
    )


    if (
        not user
        or
        not user.is_active
    ):

        revoke_refresh_token(
            db=db,
            record=record,
        )


        return redirect_to_login()


    # =========================================
    # ROTATE REFRESH TOKEN
    # =========================================

    new_refresh_data = (
        create_refresh_token(
            user_id=user.id,
        )
    )


    new_record = (
        rotate_refresh_token_record(

            db=db,

            old_record=record,

            user_id=user.id,

            new_token_id=
                new_refresh_data[
                    "token_id"
                ],

            new_expires_at=
                new_refresh_data[
                    "expires_at"
                ],

        )
    )


    # =========================================
    # NEW ACCESS TOKEN
    # =========================================

    new_access_token = (
        create_access_token(
            user_id=user.id,
            session_id=new_record.token_id,
        )
    )


    # =========================================
    # ROTATE CSRF TOKEN
    # =========================================

    new_csrf_token = (
        create_csrf_token()
    )


    # =========================================
    # SAFE REDIRECT TARGET
    # =========================================

    next_url = normalize_next_url(
        next_url
    )


    response = RedirectResponse(
        url=next_url,
        status_code=303,
    )


    # =========================================
    # SET NEW SESSION COOKIES
    # =========================================

    return set_session_cookies(

        response=response,

        access_token=
            new_access_token,

        refresh_token=
            new_refresh_data[
                "token"
            ],

        csrf_token=
            new_csrf_token,

    )


# =========================================
# LOGOUT
# =========================================

@router.post(
    "/logout"
)
def logout(
    request: Request,

    db: Session = Depends(
        get_db
    ),
):

    refresh_token = (
        request.cookies.get(
            JWT_REFRESH_COOKIE_NAME
        )
    )


    if refresh_token:

        payload = (
            decode_refresh_token(
                refresh_token
            )
        )


        if payload:

            token_id = (
                payload.get(
                    "jti"
                )
            )


            record = (
                get_refresh_token_record(
                    db=db,
                    token_id=token_id,
                )
            )


            if (
                record
                and
                record.revoked_at
                is None
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