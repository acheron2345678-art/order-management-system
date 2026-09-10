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

from app.database import (
    get_db,
)

from app.merchants.service import (
    get_available_restaurants,
    register_merchant_with_existing_restaurant,
    register_merchant_with_new_restaurant,
)

from app.users.service import (
    create_user,
)


router = APIRouter(
    tags=[
        "public registration"
    ]
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
            *
            24
            *
            60
            *
            60
        ),

        httponly=False,

        secure=(
            JWT_COOKIE_SECURE
        ),

        samesite=(
            JWT_COOKIE_SAMESITE
        ),

        path="/",
    )

    return response


def _authenticated_destination(
    current_user,
) -> str:

    if (
        current_user.role
        ==
        "merchant"
    ):
        return "/merchant"

    return "/home"


# =========================================
# CLIENT REGISTRATION RENDERER
# =========================================

def _render_client_registration(
    *,
    request: Request,
    error: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    csrf_token = (
        create_csrf_token()
    )

    response = (
        templates.TemplateResponse(
            request=request,

            name=(
                "auth/client_register.html"
            ),

            context={
                "request":
                    request,

                "error":
                    error,

                "form_data":
                    form_data or {},

                "csrf_token":
                    csrf_token,
            },

            status_code=(
                status_code
            ),
        )
    )

    return _set_csrf_cookie(
        response,
        csrf_token,
    )


# =========================================
# MERCHANT REGISTRATION RENDERER
# =========================================

def _render_merchant_registration(
    *,
    request: Request,
    db: Session,
    error: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    csrf_token = (
        create_csrf_token()
    )

    response = (
        templates.TemplateResponse(
            request=request,

            name=(
                "auth/merchant_register.html"
            ),

            context={
                "request":
                    request,

                "error":
                    error,

                "form_data":
                    form_data or {},

                "csrf_token":
                    csrf_token,

                "available_restaurants":
                    get_available_restaurants(
                        db
                    ),
            },

            status_code=(
                status_code
            ),
        )
    )

    return _set_csrf_cookie(
        response,
        csrf_token,
    )


# =========================================
# CLIENT REGISTER PAGE
# =========================================

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
    current_user = (
        get_current_user(
            request=request,
            db=db,
        )
    )

    if current_user:

        return RedirectResponse(
            url=(
                _authenticated_destination(
                    current_user
                )
            ),

            status_code=303,
        )

    return _render_client_registration(
        request=request,
    )


# =========================================
# CLIENT REGISTER
# =========================================

@router.post(
    "/register/client",
    response_class=HTMLResponse,
)
def register_client(
    request: Request,

    username: str = Form(
        ...
    ),

    email: str = Form(
        ...
    ),

    password: str = Form(
        ...
    ),

    confirm_password: str = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),
):
    current_user = (
        get_current_user(
            request=request,
            db=db,
        )
    )

    if current_user:

        return RedirectResponse(
            url=(
                _authenticated_destination(
                    current_user
                )
            ),

            status_code=303,
        )

    username = (
        username or ""
    ).strip()

    email = (
        email or ""
    ).strip().lower()

    form_data = {
        "username":
            username,

        "email":
            email,
    }

    if (
        password
        !=
        confirm_password
    ):

        return _render_client_registration(
            request=request,

            error=(
                "Passwords do not match."
            ),

            form_data=(
                form_data
            ),

            status_code=400,
        )

    # IMPORTANT:
    # There is no public role parameter.
    # This endpoint always creates CLIENTS.

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

            error=str(
                error
            ),

            form_data=(
                form_data
            ),

            status_code=400,
        )

    return RedirectResponse(
        url=(
            "/login"
            "?registered=client"
        ),

        status_code=303,
    )


# =========================================
# MERCHANT REGISTER PAGE
# =========================================

@router.get(
    "/register/merchant",
    response_class=HTMLResponse,
)
def merchant_register_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),
):
    current_user = (
        get_current_user(
            request=request,
            db=db,
        )
    )

    if current_user:

        return RedirectResponse(
            url=(
                _authenticated_destination(
                    current_user
                )
            ),

            status_code=303,
        )

    return _render_merchant_registration(
        request=request,
        db=db,
    )


# =========================================
# MERCHANT REGISTER
# =========================================

@router.post(
    "/register/merchant",
    response_class=HTMLResponse,
)
def register_merchant(
    request: Request,

    username: str = Form(
        ...
    ),

    email: str = Form(
        ...
    ),

    password: str = Form(
        ...
    ),

    confirm_password: str = Form(
        ...
    ),

    setup_mode: str = Form(
        ...
    ),

    restaurant_id: str = Form(
        ""
    ),

    restaurant_name: str = Form(
        ""
    ),

    cuisines: str = Form(
        ""
    ),

    description: str = Form(
        ""
    ),

    location: str = Form(
        ""
    ),

    delivery_min_minutes: int = Form(
        20
    ),

    delivery_max_minutes: int = Form(
        30
    ),

    db: Session = Depends(
        get_db
    ),
):
    current_user = (
        get_current_user(
            request=request,
            db=db,
        )
    )

    if current_user:

        return RedirectResponse(
            url=(
                _authenticated_destination(
                    current_user
                )
            ),

            status_code=303,
        )

    username = (
        username or ""
    ).strip()

    email = (
        email or ""
    ).strip().lower()

    setup_mode = (
        setup_mode or ""
    ).strip().lower()

    form_data = {
        "username":
            username,

        "email":
            email,

        "setup_mode":
            setup_mode,

        "restaurant_id":
            restaurant_id,

        "restaurant_name":
            (
                restaurant_name
                or
                ""
            ).strip(),

        "cuisines":
            (
                cuisines
                or
                ""
            ).strip(),

        "description":
            (
                description
                or
                ""
            ).strip(),

        "location":
            (
                location
                or
                ""
            ).strip(),

        "delivery_min_minutes":
            delivery_min_minutes,

        "delivery_max_minutes":
            delivery_max_minutes,
    }

    if (
        password
        !=
        confirm_password
    ):

        return _render_merchant_registration(
            request=request,
            db=db,

            error=(
                "Passwords do not match."
            ),

            form_data=(
                form_data
            ),

            status_code=400,
        )

    if setup_mode not in {
        "existing",
        "new",
    }:

        return _render_merchant_registration(
            request=request,
            db=db,

            error=(
                "Choose whether to use an "
                "existing restaurant or "
                "create a new restaurant."
            ),

            form_data=(
                form_data
            ),

            status_code=400,
        )

    try:

        # =================================
        # CLAIM EXISTING
        # =================================

        if (
            setup_mode
            ==
            "existing"
        ):

            if not restaurant_id:

                raise ValueError(
                    "Choose an available restaurant."
                )

            register_merchant_with_existing_restaurant(
                db,

                username=username,

                email=email,

                password=password,

                restaurant_id=(
                    restaurant_id
                ),
            )

        # =================================
        # CREATE NEW
        # =================================

        else:

            register_merchant_with_new_restaurant(
                db,

                username=username,

                email=email,

                password=password,

                restaurant_name=(
                    restaurant_name
                ),

                cuisines=(
                    cuisines
                ),

                description=(
                    description
                ),

                location=(
                    location
                ),

                delivery_min_minutes=(
                    delivery_min_minutes
                ),

                delivery_max_minutes=(
                    delivery_max_minutes
                ),
            )

    except ValueError as error:

        return _render_merchant_registration(
            request=request,
            db=db,

            error=str(
                error
            ),

            form_data=(
                form_data
            ),

            status_code=400,
        )

    return RedirectResponse(
        url=(
            "/login"
            "?registered=merchant"
        ),

        status_code=303,
    )