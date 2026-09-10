from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
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

from app.core.config import (
    ORDER_STATUSES,
)

from app.database import (
    get_db,
)

from app.merchants.dependencies import (
    require_merchant_assignment,
)

from app.merchants.models import (
    MerchantRestaurant,
)

from app.merchants.order_service import (
    get_allowed_merchant_statuses,
    get_merchant_order,
    get_merchant_orders,
    get_merchant_order_summary,
    update_merchant_order_status,
)

from app.users.models import (
    User,
)


router = APIRouter(

    prefix="/merchant",

    tags=[
        "Merchant Orders"
    ],
)


@router.get(
    "/orders",
    response_class=HTMLResponse,
)
def merchant_orders_page(

    request: Request,

    status: str = Query(
        default=""
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

    restaurant = (
        assignment.restaurant
    )


    status = (
        status
        or
        ""
    ).strip().lower()


    if (
        status
        and
        status not in ORDER_STATUSES
    ):

        raise HTTPException(

            status_code=400,

            detail=(
                "Invalid order status."
            ),
        )


    orders = (
        get_merchant_orders(

            db=db,

            restaurant_id=(
                restaurant.id
            ),

            status=(
                status
                or
                None
            ),
        )
    )


    summary = (
        get_merchant_order_summary(

            db=db,

            restaurant_id=(
                restaurant.id
            ),
        )
    )


    return templates.TemplateResponse(

        request=request,

        name="merchant/orders.html",

        context={

            "request":
                request,

            "current_user":
                current_user,

            "assignment":
                assignment,

            "restaurant":
                restaurant,

            "orders":
                orders,

            "summary":
                summary,

            "status_filter":
                status,

            "order_statuses":
                ORDER_STATUSES,
        },
    )


@router.get(
    "/orders/{order_id}",
    response_class=HTMLResponse,
)
def merchant_order_detail(

    order_id: int,

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


    result = (
        get_merchant_order(

            db=db,

            restaurant_id=(
                restaurant.id
            ),

            order_id=(
                order_id
            ),
        )
    )


    if result is None:

        raise HTTPException(

            status_code=404,

            detail=(
                "Restaurant order not found."
            ),
        )


    order, items = result


    return templates.TemplateResponse(

        request=request,

        name=(
            "merchant/order_detail.html"
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

            "order":
                order,

            "items":
                items,

            "allowed_statuses":
                get_allowed_merchant_statuses(
                    order.status
                ),
        },
    )


@router.post(
    "/orders/{order_id}/status",
)
def merchant_update_order_status(

    order_id: int,

    status: str = Form(
        ...
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

    restaurant = (
        assignment.restaurant
    )


    try:

        order = (
            update_merchant_order_status(

                db=db,

                restaurant_id=(
                    restaurant.id
                ),

                order_id=(
                    order_id
                ),

                new_status=(
                    status
                ),

                changed_by=(
                    current_user.id
                ),
            )
        )


    except ValueError as error:

        raise HTTPException(

            status_code=400,

            detail=str(
                error
            ),

        ) from error


    if order is None:

        raise HTTPException(

            status_code=404,

            detail=(
                "Restaurant order not found."
            ),
        )


    return RedirectResponse(

        url=(
            f"/merchant/orders/{order.id}"
            "?updated=1"
        ),

        status_code=303,
    )