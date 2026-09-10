from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from fastapi.responses import HTMLResponse

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_admin_or_client,
)

from app.core import templates

from app.dashboard.schemas import (
    DashboardDrilldownResponse,
    DashboardSummary,
)

from app.dashboard.service import (
    build_dashboard_context,
    get_dashboard_drilldown,
)

from app.database import get_db

from app.orders.models import (
    InsightsOrders,
    SwiggyOrders,
)

from app.users.models import User


router = APIRouter(
    tags=["dashboard"]
)


def get_client_scope(
    current_user: User,
):
    if current_user.role == "client":
        return current_user.id

    return None


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_admin_or_client
    ),
):
    context = build_dashboard_context(
        db,
        SwiggyOrders,
        InsightsOrders,
        client_id=get_client_scope(
            current_user
        ),
    )

    context["request"] = request
    context["current_user"] = current_user

    return templates.TemplateResponse(
        request=request,
        name="dashboard/dashboard.html",
        context=context,
    )


@router.get(
    "/api/dashboard/summary",
    response_model=DashboardSummary,
)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_admin_or_client
    ),
):
    return build_dashboard_context(
        db,
        SwiggyOrders,
        InsightsOrders,
        client_id=get_client_scope(
            current_user
        ),
    )


@router.get(
    "/api/dashboard/orders",
    response_model=DashboardDrilldownResponse,
)
def dashboard_orders(
    platform: str,
    metric: str,
    date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_admin_or_client
    ),
):
    try:

        return get_dashboard_drilldown(
            db,
            SwiggyOrders,
            InsightsOrders,
            platform,
            metric,
            date,
            client_id=get_client_scope(
                current_user
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc