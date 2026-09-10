from types import SimpleNamespace

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from app.auth.csrf import (
    create_csrf_token,
)

from app.auth.dependencies import (
    get_current_user,
)

from app.core import templates

from app.core.config import (
    CSRF_COOKIE_NAME,
    JWT_COOKIE_SAMESITE,
    JWT_COOKIE_SECURE,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS,
)

from app.database import get_db

from app.users.service import (
    create_user,
)


router = APIRouter(
    tags=["public registration"]
)


def _set_csrf_cookie(
    response,
    csrf_token: str,
):
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


def _render_client_registration(
    *,
    request: Request,
    error: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    csrf_token = create_csrf_token()

    response = templates.TemplateResponse(
        request=request,
        name="auth/client_register.html",
        context={
            "request": request,
            "error": error,
            "form_data": (
                form_data or {}
            ),
            "csrf_token": csrf_token,
        },
        status_code=status_code,
    )

    return _set_csrf_cookie(
        response,
        csrf_token,
    )


@router.get(
    "/register/client",
    response_class=HTMLResponse,
)
def client_register_page(
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

    return _render_client_registration(
        request=request,
    )


@router.post(
    "/register/client",
    response_class=HTMLResponse,
)
def register_client(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
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

    username = (
        username or ""
    ).strip()

    email = (
        email or ""
    ).strip().lower()

    form_data = {
        "username": username,
        "email": email,
    }

    if password != confirm_password:
        return _render_client_registration(
            request=request,
            error="Passwords do not match.",
            form_data=form_data,
            status_code=400,
        )

    # IMPORTANT:
    # The public route decides the role.
    # There is no role field submitted
    # by the browser.
    user_data = SimpleNamespace(
        username=username,
        email=email,
        password=password,
        role="client",
    )

    try:
        create_user(
            db,
            user_data,
        )

    except ValueError as error:
        return _render_client_registration(
            request=request,
            error=str(error),
            form_data=form_data,
            status_code=400,
        )

    return RedirectResponse(
        url="/login?registered=client",
        status_code=303,
    )