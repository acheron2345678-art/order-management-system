from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    BackgroundTasks
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
from app.notifications.order_email_service import (
    send_client_status_change_notification,
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

    background_tasks: BackgroundTasks,

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


    # =========================================
    # CAPTURE CURRENT STATE
    # =========================================

    current_result = (
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


    if current_result is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Restaurant order not found."
            ),
        )


    current_order, _ = (
        current_result
    )


    old_status = (

        current_order.status
        or
        ""

    ).strip().lower()


    client_email = (

        current_order.client.email

        if current_order.client

        else ""
    )


    client_name = (

        current_order.client.username

        if current_order.client

        else current_order.customer_name
    )


    # =========================================
    # UPDATE STATUS
    # =========================================

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


    # =========================================
    # CLIENT STATUS EMAIL
    # =========================================

    new_status = (

        order.status
        or
        ""

    ).strip().lower()


    if (
        old_status != new_status
        and
        client_email
    ):

        background_tasks.add_task(
            send_client_status_change_notification,

            platform="swiggy",

            client_email=(
                client_email
            ),

            client_name=(
                client_name
            ),

            order_number=(
                order.order_number
            ),

            old_status=(
                old_status
            ),

            new_status=(
                new_status
            ),
        )


    # =========================================
    # REDIRECT
    # =========================================

    return RedirectResponse(

        url=(
            f"/merchant/orders/{order.id}"
            "?updated=1"
        ),

        status_code=303,
    )