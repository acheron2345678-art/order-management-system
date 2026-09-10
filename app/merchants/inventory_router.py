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

from app.merchants.dependencies import (
    require_merchant_assignment,
)

from app.merchants.inventory_service import (
    adjust_merchant_inventory_item,
    build_merchant_inventory_summary,
    bulk_restock_merchant_inventory,
    get_merchant_inventory_item,
    get_merchant_inventory_items,
    restock_merchant_inventory_item,
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
        "Merchant Inventory"
    ],
)


def merchant_inventory_context(
    *,
    request: Request,
    db: Session,
    current_user: User,
    assignment: MerchantRestaurant,
    error: str | None = None,
):
    restaurant = (
        assignment.restaurant
    )

    products = (
        get_merchant_inventory_items(
            db=db,
            restaurant_id=restaurant.id,
        )
    )

    summary = (
        build_merchant_inventory_summary(
            products
        )
    )

    return {
        "request":
            request,

        "current_user":
            current_user,

        "assignment":
            assignment,

        "restaurant":
            restaurant,

        "products":
            products,

        "summary":
            summary,

        "error":
            error,
    }


@router.get(
    "/inventory",
    response_class=HTMLResponse,
)
def merchant_inventory_page(
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
    return templates.TemplateResponse(
        request=request,

        name="merchant/inventory.html",

        context=(
            merchant_inventory_context(
                request=request,
                db=db,
                current_user=current_user,
                assignment=assignment,
            )
        ),
    )


@router.post(
    "/inventory/{product_id}/restock",
    response_class=HTMLResponse,
)
def merchant_restock_inventory_item(
    product_id: int,

    request: Request,

    quantity: int = Form(
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

        product = (
            restock_merchant_inventory_item(
                db=db,
                restaurant_id=restaurant.id,
                product_id=product_id,
                quantity=quantity,
            )
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,

            name="merchant/inventory.html",

            context=(
                merchant_inventory_context(
                    request=request,
                    db=db,
                    current_user=current_user,
                    assignment=assignment,
                    error=str(error),
                )
            ),

            status_code=400,
        )

    return RedirectResponse(
        url=(
            "/merchant/inventory"
            f"?restocked={product.id}"
        ),

        status_code=303,
    )


@router.post(
    "/inventory/{product_id}/adjust",
    response_class=HTMLResponse,
)
def merchant_adjust_inventory_item(
    product_id: int,

    request: Request,

    stock_quantity: int = Form(
        ...
    ),

    reorder_level: int = Form(
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

        product = (
            adjust_merchant_inventory_item(
                db=db,
                restaurant_id=restaurant.id,
                product_id=product_id,
                stock_quantity=stock_quantity,
                reorder_level=reorder_level,
            )
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,

            name="merchant/inventory.html",

            context=(
                merchant_inventory_context(
                    request=request,
                    db=db,
                    current_user=current_user,
                    assignment=assignment,
                    error=str(error),
                )
            ),

            status_code=400,
        )

    return RedirectResponse(
        url=(
            "/merchant/inventory"
            f"?adjusted={product.id}"
        ),

        status_code=303,
    )


@router.post(
    "/inventory/bulk-restock",
    response_class=HTMLResponse,
)
def merchant_bulk_restock(
    request: Request,

    product_ids: list[int] = Form(
        ...
    ),

    quantities: list[int] = Form(
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

        products = (
            bulk_restock_merchant_inventory(
                db=db,
                restaurant_id=restaurant.id,
                product_ids=product_ids,
                quantities=quantities,
            )
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,

            name="merchant/inventory.html",

            context=(
                merchant_inventory_context(
                    request=request,
                    db=db,
                    current_user=current_user,
                    assignment=assignment,
                    error=str(error),
                )
            ),

            status_code=400,
        )

    return RedirectResponse(
        url=(
            "/merchant/inventory"
            f"?bulk={len(products)}"
        ),

        status_code=303,
    )