from fastapi import (
    APIRouter,
    Depends,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
)

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_merchant,
)

from app.core import templates

from app.database import (
    get_db,
)

from app.merchants.dashboard_service import (
    get_merchant_dashboard_summary,
)

from app.merchants.dependencies import (
    require_merchant_assignment,
)

from app.merchants.models import (
    MerchantRestaurant,
)

from app.users.models import (
    User,
)


router = APIRouter(
    prefix="/merchant",
    tags=[
        "Merchant"
    ],
)


@router.get(
    "",
    response_class=HTMLResponse,
)
def merchant_dashboard(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_merchant
    ),

    assignment: MerchantRestaurant = Depends(
        require_merchant_assignment
    ),
):

    restaurant = (
        assignment.restaurant
    )

    summary = (
        get_merchant_dashboard_summary(
            db=db,
            restaurant_id=restaurant.id,
        )
    )

    return templates.TemplateResponse(
        request=request,

        name=(
            "merchant/dashboard.html"
        ),

        context={
            "request":
                request,

            "current_user":
                current_user,

            "assignment":
                assignment,

            "restaurant":
                restaurant,

            "summary":
                summary,
        },
    )