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

from app.merchants.menu_service import (
    build_merchant_menu_summary,
    create_merchant_menu_item,
    get_merchant_menu_item,
    get_merchant_menu_items,
    set_merchant_menu_item_active_state,
    update_merchant_menu_item,
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


# =========================================================
# DASHBOARD
# =========================================================

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


# =========================================================
# PROFILE RENDERER
# =========================================================

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


# =========================================================
# PROFILE PAGE
# =========================================================

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


# =========================================================
# UPDATE PROFILE
# =========================================================

@router.post(
    "/profile",
    response_class=HTMLResponse,
)
def update_merchant_profile(
    request: Request,

    name: str = Form(...),

    description: str = Form(
        ""
    ),

    cuisines: str = Form(...),

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

            error=str(
                error
            ),

            form_data=form_data,

            status_code=400,
        )

    return RedirectResponse(
        url="/merchant/profile?saved=1",

        status_code=303,
    )


# =========================================================
# RESTAURANT STATUS
# =========================================================

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

            state
            ==
            "active",
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,

            detail=str(
                error
            ),
        ) from error

    return RedirectResponse(
        url=(
            "/merchant/profile"
            f"?status={state}"
        ),

        status_code=303,
    )


# =========================================================
# MENU FORM CONTEXT
# =========================================================

def merchant_menu_form_context(
    *,
    request: Request,
    current_user: User,
    assignment: MerchantRestaurant,
    action: str,
    product=None,
    error: str | None = None,
    form_data: dict | None = None,
):
    restaurant = (
        assignment.restaurant
    )

    if form_data is None:

        if product is None:

            form_data = {
                "product_name": "",
                "description": "",
                "price": "",
                "image_url": "",
                "stock_quantity": 0,
                "reorder_level": 5,
                "menu_category": "Recommended",
                "is_bestseller": False,
            }

        else:

            form_data = {
                "product_name":
                    product.product_name,

                "description":
                    product.description or "",

                "price":
                    product.price,

                "image_url":
                    product.image_url or "",

                "stock_quantity":
                    product.stock_quantity,

                "reorder_level":
                    product.reorder_level,

                "menu_category":
                    product.menu_category
                    or
                    "Recommended",

                "is_bestseller":
                    bool(
                        product.is_bestseller
                    ),
            }

    return {
        "request":
            request,

        "current_user":
            current_user,

        "assignment":
            assignment,

        "restaurant":
            restaurant,

        "action":
            action,

        "product":
            product,

        "error":
            error,

        "form_data":
            form_data,
    }


# =========================================================
# MENU PAGE
# =========================================================

@router.get(
    "/menu",
    response_class=HTMLResponse,
)
def merchant_menu_page(
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

    products = (
        get_merchant_menu_items(
            db=db,

            restaurant_id=restaurant.id,

            include_inactive=True,
        )
    )

    summary = (
        build_merchant_menu_summary(
            products
        )
    )

    return templates.TemplateResponse(
        request=request,

        name="merchant/menu.html",

        context={
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
        },
    )


# =========================================================
# ADD DISH PAGE
# =========================================================

@router.get(
    "/menu/add",
    response_class=HTMLResponse,
)
def merchant_add_menu_item_page(
    request: Request,

    current_user: User = Depends(
        require_merchant
    ),

    assignment: MerchantRestaurant = Depends(
        require_merchant_assignment
    ),
):
    return templates.TemplateResponse(
        request=request,

        name="merchant/menu_form.html",

        context=(
            merchant_menu_form_context(
                request=request,

                current_user=current_user,

                assignment=assignment,

                action="add",
            )
        ),
    )


# =========================================================
# CREATE DISH
# =========================================================

@router.post(
    "/menu/add",
    response_class=HTMLResponse,
)
def merchant_add_menu_item(
    request: Request,

    product_name: str = Form(...),

    description: str = Form(
        ""
    ),

    price: str = Form(...),

    stock_quantity: int = Form(
        0
    ),

    reorder_level: int = Form(
        5
    ),

    menu_category: str = Form(...),

    is_bestseller: bool = Form(
        False
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
    restaurant = (
        assignment.restaurant
    )

    form_data = {
        "product_name":
            (
                product_name
                or
                ""
            ).strip(),

        "description":
            (
                description
                or
                ""
            ).strip(),

        "price":
            price,

        "stock_quantity":
            stock_quantity,

        "reorder_level":
            reorder_level,

        "menu_category":
            (
                menu_category
                or
                ""
            ).strip(),

        "is_bestseller":
            bool(
                is_bestseller
            ),
        "image_url":
            (
                image_url
                or
                ""
            ).strip(),
    }

    try:

        create_merchant_menu_item(
            db=db,

            restaurant_id=restaurant.id,

            **form_data,
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,

            name="merchant/menu_form.html",

            context=(
                merchant_menu_form_context(
                    request=request,

                    current_user=current_user,

                    assignment=assignment,

                    action="add",

                    error=str(
                        error
                    ),

                    form_data=form_data,
                )
            ),

            status_code=400,
        )

    return RedirectResponse(
        url="/merchant/menu?created=1",

        status_code=303,
    )


# =========================================================
# EDIT DISH PAGE
# =========================================================

@router.get(
    "/menu/{product_id}/edit",
    response_class=HTMLResponse,
)
def merchant_edit_menu_item_page(
    product_id: int,

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

    product = (
        get_merchant_menu_item(
            db=db,

            restaurant_id=restaurant.id,

            product_id=product_id,
        )
    )

    if product is None:

        raise HTTPException(
            status_code=404,

            detail=(
                "Menu item not found"
            ),
        )

    return templates.TemplateResponse(
        request=request,

        name="merchant/menu_form.html",

        context=(
            merchant_menu_form_context(
                request=request,

                current_user=current_user,

                assignment=assignment,

                action="edit",

                product=product,
            )
        ),
    )


# =========================================================
# UPDATE DISH
# =========================================================

@router.post(
    "/menu/{product_id}/edit",
    response_class=HTMLResponse,
)
def merchant_edit_menu_item(
    product_id: int,

    request: Request,

    product_name: str = Form(...),

    description: str = Form(
        ""
    ),

    price: str = Form(...),

    stock_quantity: int = Form(
        0
    ),

    reorder_level: int = Form(
        5
    ),

    menu_category: str = Form(...),

    is_bestseller: bool = Form(
        False
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
    restaurant = (
        assignment.restaurant
    )

    product = (
        get_merchant_menu_item(
            db=db,

            restaurant_id=restaurant.id,

            product_id=product_id,
        )
    )

    if product is None:

        raise HTTPException(
            status_code=404,

            detail=(
                "Menu item not found"
            ),
        )

    form_data = {
        "product_name":
            (
                product_name
                or
                ""
            ).strip(),

        "description":
            (
                description
                or
                ""
            ).strip(),

        "price":
            price,

        "stock_quantity":
            stock_quantity,

        "reorder_level":
            reorder_level,

        "menu_category":
            (
                menu_category
                or
                ""
            ).strip(),

        "is_bestseller":
            bool(
                is_bestseller
            ),
        "image_url":
            (
                image_url
                or
                ""
            ).strip(),
    }

    try:

        updated_product = (
            update_merchant_menu_item(
                db=db,

                restaurant_id=restaurant.id,

                product_id=product_id,

                **form_data,
            )
        )

        if updated_product is None:

            raise HTTPException(
                status_code=404,

                detail=(
                    "Menu item not found"
                ),
            )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,

            name="merchant/menu_form.html",

            context=(
                merchant_menu_form_context(
                    request=request,

                    current_user=current_user,

                    assignment=assignment,

                    action="edit",

                    product=product,

                    error=str(
                        error
                    ),

                    form_data=form_data,
                )
            ),

            status_code=400,
        )

    return RedirectResponse(
        url="/merchant/menu?saved=1",

        status_code=303,
    )


# =========================================================
# ACTIVATE / DEACTIVATE DISH
# =========================================================

@router.post(
    "/menu/{product_id}/status",
)
def merchant_menu_item_status(
    product_id: int,

    state: str = Form(...),

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
                "Menu item status must "
                "be active or inactive."
            ),
        )

    restaurant = (
        assignment.restaurant
    )

    product = (
        set_merchant_menu_item_active_state(
            db=db,

            restaurant_id=restaurant.id,

            product_id=product_id,

            is_active=(
                state == "active"
            ),
        )
    )

    if product is None:

        raise HTTPException(
            status_code=404,

            detail=(
                "Menu item not found"
            ),
        )

    return RedirectResponse(
        url=(
            "/merchant/menu"
            f"?status={state}"
        ),

        status_code=303,
    )