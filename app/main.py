import logging

from fastapi import (
    Depends,
    FastAPI,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth.csrf import validate_csrf
from app.auth.dependencies import (
    require_admin_or_client,
)
from app.auth.models import RefreshToken
from app.auth.router import router as auth_router
from app.core import (
    APP_NAME,
    STATIC_DIR,
    templates,
)
from app.core.config import ALLOWED_HOSTS
from app.core.redirects import RedirectTargetValidationMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.dashboard.router import router as dashboard_router
from app.database import Base, engine
from app.insights.router import router as insights_storefront_router
from app.orders.router import router as orders_router
from app.products.router import router as products_router
from app.restaurants.router import router as restaurants_router
from app.search.router import router as search_router
from app.swiggy.router import router as swiggy_storefront_router
from app.users.models import User
from app.users.profile_router import router as profile_router
from app.users.router import router as users_router


logger = logging.getLogger(
    "order_management"
)


app = FastAPI(
    title=APP_NAME,
    dependencies=[
        Depends(validate_csrf)
    ],
)


# =========================================
# SAFE ERROR RESPONSES
# =========================================

def safe_error_response(
    request: Request,
    status_code: int,
    message: str,
):
    accepts_html = (
        "text/html"
        in request.headers.get(
            "accept",
            "",
        ).lower()
    )

    if accepts_html:
        return templates.TemplateResponse(
            request=request,
            name="errors/error.html",
            context={
                "request": request,
                "status_code": status_code,
                "message": message,
            },
            status_code=status_code,
        )

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message
        },
    )


@app.exception_handler(
    RequestValidationError
)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    logger.warning(
        "Malformed request rejected: %s %s",
        request.method,
        request.url.path,
    )

    return safe_error_response(
        request=request,
        status_code=422,
        message=(
            "The request contains invalid or malformed values."
        ),
    )


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request,
    exc: ValueError,
):
    return safe_error_response(
        request=request,
        status_code=400,
        message="The request contains invalid values.",
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
):
    logger.exception(
        "Database integrity error while handling %s %s",
        request.method,
        request.url.path,
    )

    return safe_error_response(
        request=request,
        status_code=409,
        message=(
            "The request conflicts with existing data. "
            "Please review the submitted values and try again."
        ),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.exception(
        "Database operation failed while handling %s %s",
        request.method,
        request.url.path,
    )

    return safe_error_response(
        request=request,
        status_code=500,
        message=(
            "A database operation could not be completed. "
            "Please try again."
        ),
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unexpected application error while handling %s %s",
        request.method,
        request.url.path,
    )

    return safe_error_response(
        request=request,
        status_code=500,
        message=(
            "The request could not be completed. Please try again."
        ),
    )


# =========================================
# SECURITY MIDDLEWARE
# =========================================

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)

app.add_middleware(
    RedirectTargetValidationMiddleware,
)

app.add_middleware(
    SecurityHeadersMiddleware,
)


# =========================================
# STATIC FILES
# =========================================

app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static",
)


# =========================================
# DATABASE
# =========================================

Base.metadata.create_all(
    bind=engine
)


# =========================================
# ROUTERS
# =========================================

app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(dashboard_router)
app.include_router(search_router)
app.include_router(products_router)
app.include_router(restaurants_router)
app.include_router(users_router)
app.include_router(swiggy_storefront_router)
app.include_router(insights_storefront_router)
app.include_router(profile_router)


# =========================================
# ROOT
# =========================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
def root():
    return RedirectResponse(
        url="/login",
        status_code=303,
    )


# =========================================
# HOME
# =========================================

@app.get(
    "/home",
    response_class=HTMLResponse,
)
def home(
    request: Request,
    current_user: User = Depends(
        require_admin_or_client
    ),
):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "request": request,
            "current_user": current_user,
        },
    )