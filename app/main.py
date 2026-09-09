from fastapi import (
    Depends,
    FastAPI,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from starlette.middleware.trustedhost import (
    TrustedHostMiddleware,
)

from app.auth.csrf import (
    validate_csrf,
)

from app.auth.dependencies import (
    require_authenticated_user,
)

from app.auth.models import (
    RefreshToken,
)

from app.auth.router import (
    router as auth_router,
)

from app.core import (
    APP_NAME,
    STATIC_DIR,
    templates,
)

from app.core.config import (
    ALLOWED_HOSTS,
)

from app.core.security_headers import (
    SecurityHeadersMiddleware,
)

from app.dashboard.router import (
    router as dashboard_router,
)

from app.database import (
    Base,
    engine,
)

from app.insights.router import (
    router as insights_storefront_router,
)

from app.orders.router import (
    router as orders_router,
)

from app.products.router import (
    router as products_router,
)

from app.search.router import (
    router as search_router,
)

from app.swiggy.router import (
    router as swiggy_storefront_router,
)

from app.users.models import (
    User,
)

from app.users.router import (
    router as users_router,
)

from app.users.profile_router import (
    router as profile_router,
)


app = FastAPI(
    title=APP_NAME,
    dependencies=[
        Depends(
            validate_csrf
        )
    ],
)


# =========================================
# SECURITY MIDDLEWARE
# =========================================

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
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

app.include_router(
    auth_router
)

app.include_router(
    orders_router
)

app.include_router(
    dashboard_router
)

app.include_router(
    search_router
)

app.include_router(
    products_router
)

app.include_router(
    users_router
)

app.include_router(
    swiggy_storefront_router
)

app.include_router(
    insights_storefront_router
)

app.include_router(
    profile_router
)


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
        require_authenticated_user
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
