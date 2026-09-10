from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
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

from app.merchants.profile_service import (
    set_merchant_restaurant_status,
    update_merchant_restaurant_profile,
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


# =========================================
# DASHBOARD
# =========================================

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
        name="merchant/dashboard.html",
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


# =========================================
# PROFILE RENDERER
# =========================================

def render_merchant_profile(
    *,
    request: Request,
    current_user: User,
    assignment: MerchantRestaurant,
    error: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,

        name="merchant/profile.html",

        context={
            "request":
                request,

            "current_user":
                current_user,

            "assignment":
                assignment,

            "restaurant":
                assignment.restaurant,

            "error":
                error,

            "form_data":
                form_data,
        },

        status_code=status_code,
    )


# =========================================
# RESTAURANT PROFILE PAGE
# =========================================

@router.get(
    "/profile",
    response_class=HTMLResponse,
)
def merchant_profile_page(
    request: Request,

    current_user: User = Depends(
        require_merchant
    ),

    assignment: MerchantRestaurant = Depends(
        require_merchant_assignment
    ),
):
    return render_merchant_profile(
        request=request,
        current_user=current_user,
        assignment=assignment,
    )


# =========================================
# UPDATE RESTAURANT PROFILE
# =========================================

@router.post(
    "/profile",
    response_class=HTMLResponse,
)
def update_merchant_profile(
    request: Request,

    name: str = Form(
        ...
    ),

    description: str = Form(
        ""
    ),

    cuisines: str = Form(
        ...
    ),

    delivery_min_minutes: int = Form(
        ...
    ),

    delivery_max_minutes: int = Form(
        ...
    ),

    location: str = Form(
        ""
    ),

    offer_text: str = Form(
        ""
    ),

    image_url: str = Form(
        ""
    ),

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
    form_data = {
        "name":
            (
                name
                or
                ""
            ).strip(),

        "description":
            (
                description
                or
                ""
            ).strip(),

        "cuisines":
            (
                cuisines
                or
                ""
            ).strip(),

        "delivery_min_minutes":
            delivery_min_minutes,

        "delivery_max_minutes":
            delivery_max_minutes,

        "location":
            (
                location
                or
                ""
            ).strip(),

        "offer_text":
            (
                offer_text
                or
                ""
            ).strip(),

        "image_url":
            (
                image_url
                or
                ""
            ).strip(),
    }

    try:

        update_merchant_restaurant_profile(
            db,
            assignment,

            **form_data,
        )

    except ValueError as error:

        return render_merchant_profile(
            request=request,
            current_user=current_user,
            assignment=assignment,
            error=str(error),
            form_data=form_data,
            status_code=400,
        )

    return RedirectResponse(
        url="/merchant/profile?saved=1",
        status_code=303,
    )


# =========================================
# RESTAURANT ACTIVE STATE
# =========================================

@router.post(
    "/profile/status",
)
def update_merchant_restaurant_status(
    state: str = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    assignment: MerchantRestaurant = Depends(
        require_merchant_assignment
    ),
):
    state = (
        state
        or
        ""
    ).strip().lower()

    if state not in {
        "active",
        "inactive",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Restaurant status must be "
                "active or inactive."
            ),
        )

    try:

        set_merchant_restaurant_status(
            db,
            assignment,
            state == "active",
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return RedirectResponse(
        url=(
            "/merchant/profile"
            f"?status={state}"
        ),
        status_code=303,
    )