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
    require_admin,
)

from app.core import templates

from app.database import (
    get_db,
)

from app.merchants.admin_service import (
    build_admin_merchant_summary,
    get_admin_merchant_account,
    get_admin_merchant_accounts,
    get_available_restaurants_for_merchant,
    reassign_merchant_restaurant,
    set_admin_merchant_active_state,
)

from app.users.models import (
    User,
)


router = APIRouter(

    prefix="/admin/merchants",

    tags=[
        "Admin Merchants"
    ],
)


# =========================================================
# EDIT PAGE RENDERER
# =========================================================

def render_admin_merchant_edit(
    *,
    request: Request,
    db: Session,
    current_user: User,
    merchant_id: int,
    error: str | None = None,
    status_code: int = 200,
):

    account = (
        get_admin_merchant_account(
            db=db,
            merchant_id=merchant_id,
        )
    )


    if account is None:

        raise HTTPException(
            status_code=404,
            detail="Merchant account not found.",
        )


    available_restaurants = (
        get_available_restaurants_for_merchant(
            db=db,
            merchant_id=merchant_id,
        )
    )


    return templates.TemplateResponse(

        request=request,

        name="merchants/admin_merchant_edit.html",

        context={

            "request":
                request,

            "current_user":
                current_user,

            "account":
                account,

            "merchant":
                account.user,

            "assignment":
                account.assignment,

            "restaurant":
                account.restaurant,

            "available_restaurants":
                available_restaurants,

            "error":
                error,
        },

        status_code=status_code,
    )


# =========================================================
# MERCHANT LIST
# =========================================================

@router.get(
    "",
    response_class=HTMLResponse,
)
def admin_merchants_page(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):

    accounts = (
        get_admin_merchant_accounts(
            db
        )
    )


    summary = (
        build_admin_merchant_summary(
            accounts
        )
    )


    return templates.TemplateResponse(

        request=request,

        name="merchants/admin_merchants.html",

        context={

            "request":
                request,

            "current_user":
                current_user,

            "accounts":
                accounts,

            "summary":
                summary,
        },
    )


# =========================================================
# MERCHANT EDIT PAGE
# =========================================================

@router.get(
    "/{merchant_id}/edit",
    response_class=HTMLResponse,
)
def admin_merchant_edit_page(

    merchant_id: int,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):

    return render_admin_merchant_edit(

        request=request,

        db=db,

        current_user=current_user,

        merchant_id=merchant_id,
    )


# =========================================================
# REASSIGN MERCHANT
# =========================================================

@router.post(
    "/{merchant_id}/reassign",
    response_class=HTMLResponse,
)
def admin_reassign_merchant(

    merchant_id: int,

    request: Request,

    restaurant_id: int = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):

    try:

        reassign_merchant_restaurant(

            db=db,

            merchant_id=merchant_id,

            restaurant_id=restaurant_id,
        )


    except ValueError as error:

        return render_admin_merchant_edit(

            request=request,

            db=db,

            current_user=current_user,

            merchant_id=merchant_id,

            error=str(
                error
            ),

            status_code=400,
        )


    return RedirectResponse(

        url=(
            f"/admin/merchants/{merchant_id}/edit"
            "?reassigned=1"
        ),

        status_code=303,
    )


# =========================================================
# ENABLE / DISABLE
# =========================================================

@router.post(
    "/{merchant_id}/status",
)
def admin_merchant_status(

    merchant_id: int,

    state: str = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
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
                "Merchant status must be "
                "active or inactive."
            ),
        )


    merchant = (
        set_admin_merchant_active_state(

            db=db,

            merchant_id=merchant_id,

            is_active=(
                state == "active"
            ),
        )
    )


    if merchant is None:

        raise HTTPException(
            status_code=404,
            detail="Merchant account not found.",
        )


    return RedirectResponse(

        url=(
            f"/admin/merchants/{merchant_id}/edit"
            f"?status={state}"
        ),

        status_code=303,
    )