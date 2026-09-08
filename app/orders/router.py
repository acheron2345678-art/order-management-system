from fastapi import (
    APIRouter,
    Depends,
    Form,
    BackgroundTasks,
    HTTPException,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from app.core import (
    ORDER_STATUSES,
    templates,
)

from app.core.config import (
    ORDER_STATUS_TRANSITIONS,
)

from app.database import get_db

from app.orders.dependencies import (
    get_platform_context,
)

from app.orders.service import (
    delete_order,
    get_order,
    get_orders,
    update_order,
)

from app.orders.purchase_service import (
    get_client_purchases,
)

from app.orders.history_service import (
    record_order_change,
    record_order_deleted,
    get_order_history,
)

from app.orders.order_item_service import (
    get_order_items,
)

from app.auth.dependencies import (
    require_authenticated_user,
    require_admin,
    require_client,
)

from app.users.models import User

from app.users.service import (
    get_clients,
    get_user_by_id,
)

from app.notifications.order_email_service import send_client_status_change_notification

from app.products.service import get_products_from_platform

from datetime import date

 
router = APIRouter(
    tags=["orders"]
)


def get_client_scope(
    current_user: User,
):
    if current_user.role == "client":
        return current_user.id

    return None


def validate_client(
    db: Session,
    client_id: int,
):
    client = get_user_by_id(
        db,
        client_id,
    )

    if (
        not client
        or not client.is_active
        or client.role != "client"
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid client account",
        )

    return client


def render_order_list(
    request,
    platform_context,
    status,
    order_date,
    db,
    current_user,
):
    try:

        orders, total = get_orders(
            db,
            platform_context["model"],
            status=status,
            order_date=order_date,
            client_id=get_client_scope(
                current_user
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail="Invalid order date",
        ) from exc

    return templates.TemplateResponse(
        request=request,
        name="orders/orders.html",
        context={
            "request": request,
            "orders": orders,
            "platform": platform_context["name"],
            "platform_url": platform_context["key"],
            "status": status,
            "order_date": order_date,
            "total_orders": total,
            "statuses": ORDER_STATUSES,
            "current_user": current_user,
        },
    )


@router.get(
    "/{platform}/orders",
    response_class=HTMLResponse,
)
def get_orders_page(
    platform: str,
    request: Request,
    status: str | None = None,
    order_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    context = get_platform_context(
        platform
    )

    if (
        status
        and status not in ORDER_STATUSES
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid order status",
        )

    return render_order_list(
        request,
        context,
        status,
        order_date,
        db,
        current_user,
    )


@router.get(
    "/{platform}/orders/view/{id}",
    response_class=HTMLResponse,
)
def view_order(
    platform: str,
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    context = get_platform_context(
        platform
    )

    order = get_order(
        db,
        context["model"],
        id,
        client_id=get_client_scope(
            current_user
        ),
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    order_items = get_order_items(
        db=db,
        platform=context["key"],
        order_id=order.id,
    )

    history = get_order_history(
        db=db,
        platform=context["key"],
        order_id=order.id,
    )

    client = None

    if order.client_id is not None:
        client = get_user_by_id(
            db,
            order.client_id,
        )

    template_name = (
        "orders/insights_project_detail.html"
        if (
            context["key"] == "insights"
            and current_user.role == "admin"
        )
        else
        "orders/order_detail.html"
    )

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "request":
                request,

            "order":
                order,

            "order_items":
                order_items,

            "history":
                history,

            "client":
                client,

            "platform":
                context["name"],

            "platform_url":
                context["key"],

            "current_user":
                current_user,
        },
    ) 

@router.get(
    "/{platform}/orders/edit/{id}",
    response_class=HTMLResponse,
)
def edit_order_page(
    platform: str,
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_admin
    ),
):
    context = get_platform_context(
        platform
    )

    order = get_order(
        db,
        context["model"],
        id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    products = (
        get_products_from_platform(
            db,
            context["name"],
        )
    )

    clients = get_clients(
        db
    )

    allowed_next_statuses = (
        ORDER_STATUS_TRANSITIONS.get(
            order.status,
            set(),
        )
    )

    available_statuses = [
        status
        for status in ORDER_STATUSES
        if (
            status == order.status
            or
            status in allowed_next_statuses
        )
    ]

    template_name = (
        "orders/insights_project_form.html"
        if context["key"] == "insights"
        else
        "orders/order_form.html"
    )

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "request":
                request,

            "platform":
                context["name"],

            "platform_url":
                context["key"],

            "action":
                "edit",

            "order":
                order,

            "products":
                products,

            "clients":
                clients,

            "statuses":
                available_statuses,

            "current_user":
                current_user,
        },
    )


@router.post(
    "/{platform}/orders/edit/{id}"
)
def edit_order(
    platform: str,
    id: int,
    background_tasks: BackgroundTasks,

    customer_name: str = Form(...),

    order_number: str = Form(...),

    client_id: int = Form(...),

    status: str = Form(...),

    order_date: str = Form(...),

    preferred_completion_date: str = Form(
        ""
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    context = get_platform_context(
        platform
    )

    order = get_order(
        db,
        context["model"],
        id,
    )

    if not order:

        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )


    # =========================================
    # STATUS VALIDATION
    # =========================================

    if status not in ORDER_STATUSES:

        raise HTTPException(
            status_code=400,
            detail="Invalid order status",
        )


    allowed_next_statuses = (
        ORDER_STATUS_TRANSITIONS.get(
            order.status,
            set(),
        )
    )


    if (
        status != order.status
        and
        status not in allowed_next_statuses
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"Status cannot change from "
                f"{order.status} to {status}"
            ),
        )


    # =========================================
    # CLIENT
    # =========================================

    client = validate_client(
        db,
        client_id,
    )


    # =========================================
    # CLEAN VALUES
    # =========================================

    customer_name = (
        customer_name.strip()
    )

    order_number = (
        order_number.strip()
    )

    preferred_completion_date = (
        preferred_completion_date.strip()
    )


    if not customer_name:

        raise HTTPException(
            status_code=400,
            detail=(
                "Customer name is required"
            ),
        )


    if not order_number:

        raise HTTPException(
            status_code=400,
            detail=(
                "Order number is required"
            ),
        )


    # =========================================
    # INSIGHTS COMPLETION DATE
    # =========================================

    parsed_completion_date = None


    if (
        context["key"] == "insights"
        and
        preferred_completion_date
    ):

        try:

            parsed_completion_date = (
                date.fromisoformat(
                    preferred_completion_date
                )
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Preferred completion "
                    "date is invalid."
                ),
            ) from exc


    # =========================================
    # SAVE OLD VALUES
    # =========================================

    old_customer_name = (
        order.customer_name
    )

    old_order_number = (
        order.order_number
    )

    old_product_name = (
        order.product_name
    )

    old_amount = (
        order.amount
    )

    old_status = (
        order.status
    )

    old_order_date = (
        order.order_date
    )

    old_client_id = (
        order.client_id
    )


    old_preferred_completion_date = (
        getattr(
            order,
            "preferred_completion_date",
            None,
        )
        if context["key"] == "insights"
        else None
    )


    # =========================================
    # OLD CLIENT
    # =========================================

    old_client = None


    if old_client_id is not None:

        old_client = get_user_by_id(
            db,
            old_client_id,
        )


    old_client_name = (
        old_client.username
        if old_client
        else "Unassigned"
    )


    new_client_name = (
        client.username
    )


    # =========================================
    # UPDATE NORMAL ORDER FIELDS
    # =========================================

    try:

        update_order(
            db=db,

            order=order,

            customer_name=(
                customer_name
            ),

            order_number=(
                order_number
            ),

            amount=(
                order.amount
            ),

            status=(
                status
            ),

            order_date=(
                order_date
            ),

            client_id=(
                client.id
            ),
        )


    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


    order.client_id = (
        client.id
    )


    # =========================================
    # INSIGHTS-SPECIFIC FIELD
    # =========================================

    if context["key"] == "insights":

        order.preferred_completion_date = (
            parsed_completion_date
        )


    db.commit()

    db.refresh(
        order
    )


    # =========================================
    # HISTORY - CUSTOMER
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name="customer_name",

        old_value=old_customer_name,

        new_value=order.customer_name,

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - ORDER NUMBER
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name="order_number",

        old_value=old_order_number,

        new_value=order.order_number,

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - PRODUCT / SERVICE
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name=(
            "service"
            if context["key"] == "insights"
            else "product"
        ),

        old_value=(
            old_product_name
            or
            "Unassigned"
        ),

        new_value=(
            order.product_name
            or
            "Unassigned"
        ),

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - AMOUNT
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name="amount",

        old_value=old_amount,

        new_value=order.amount,

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - STATUS
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name="status",

        old_value=old_status,

        new_value=order.status,

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - REQUEST / ORDER DATE
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name="order_date",

        old_value=old_order_date,

        new_value=order.order_date,

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - CLIENT
    # =========================================

    record_order_change(
        db=db,

        platform=context["key"],

        order_id=order.id,

        field_name="client",

        old_value=old_client_name,

        new_value=new_client_name,

        changed_by=current_user.id,
    )


    # =========================================
    # HISTORY - INSIGHTS PREFERRED DATE
    # =========================================

    if context["key"] == "insights":

        record_order_change(
            db=db,

            platform=context["key"],

            order_id=order.id,

            field_name=(
                "preferred_completion_date"
            ),

            old_value=(
                old_preferred_completion_date
            ),

            new_value=(
                order.preferred_completion_date
            ),

            changed_by=current_user.id,
        )


    # =========================================
    # STATUS EMAIL
    #
    # Email only when the status itself changed.
    # =========================================

    if old_status != order.status:

        background_tasks.add_task(
            send_client_status_change_notification,

            platform=context["key"],

            client_email=(
                client.email
            ),

            client_name=(
                client.username
            ),

            order_number=(
                order.order_number
            ),

            old_status=(
                old_status
            ),

            new_status=(
                order.status
            ),
        )


    # =========================================
    # REDIRECT
    # =========================================

    return RedirectResponse(
        url=(
            f"/{context['key']}"
            f"/orders/view/{order.id}"
        ),
        status_code=303,
    )

@router.post(
    "/{platform}/orders/delete/{id}"
)
def delete_order_route(
    platform: str,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_admin
    ),
):
    context = get_platform_context(
        platform
    )

    order = get_order(
        db,
        context["model"],
        id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    record_order_deleted(
        db=db,
        platform=context["key"],
        order_id=order.id,
        changed_by=current_user.id,
    )

    delete_order(
        db,
        order,
    )

    return RedirectResponse(
        url=(
            f"/{context['key']}"
            "/orders"
        ),
        status_code=303,
    )


@router.get(
    "/my-purchases",
    response_class=HTMLResponse,
)
def my_purchases(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_client
    ),
):
    purchases = (
        get_client_purchases(
            db=db,
            client_id=current_user.id,
        )
    )

    swiggy_purchases = [
        purchase
        for purchase in purchases
        if purchase["platform"] == "swiggy"
    ]

    insights_purchases = [
        purchase
        for purchase in purchases
        if purchase["platform"] == "insights"
    ]

    total_units = sum(
        purchase["quantity"]
        for purchase in purchases
    )

    total_spent = sum(
        purchase["line_total"]
        for purchase in purchases
        if purchase["status"] == "completed"
    )

    swiggy_units = sum(
        purchase["quantity"]
        for purchase in swiggy_purchases
    )

    insights_units = sum(
        purchase["quantity"]
        for purchase in insights_purchases
    )

    return templates.TemplateResponse(
        request=request,
        name="orders/my_purchases.html",
        context={
            "current_user":
                current_user,

            "swiggy_purchases":
                swiggy_purchases,

            "insights_purchases":
                insights_purchases,

            "total_units":
                total_units,

            "total_spent":
                total_spent,

            "swiggy_units":
                swiggy_units,

            "insights_units":
                insights_units,
        },
    )