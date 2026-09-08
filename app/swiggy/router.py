from datetime import date

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
    get_current_user,
    require_client,
)

from app.core import templates

from app.database import (
    get_db,
)

from app.notifications.order_email_service import (
    send_admin_new_order_notification,
    send_client_order_confirmation,
)

from app.orders.history_service import (
    record_order_created,
)

from app.orders.order_item_service import (
    get_order_items,
)

from app.products.cart_checkout_service import (
    create_cart_orders,
)

from app.products.cart_service import (
    add_to_cart,
    remove_from_cart,
    set_cart_quantity,
)

from app.swiggy.service import (
    clear_swiggy_cart,
    get_client_swiggy_order,
    get_client_swiggy_orders,
    get_swiggy_cart,
    get_swiggy_cart_count,
    get_swiggy_cart_details,
    get_swiggy_product,
    get_swiggy_products,
)

from app.users.models import (
    User,
)

from app.users.profile_service import (
    get_client_profile,
)


router = APIRouter(
    prefix="/swiggy",
    tags=[
        "Swiggy Storefront"
    ],
)


# =========================================================
# CART COUNT HELPER
# =========================================================

def get_cart_count_for_user(
    db: Session,
    current_user: User | None,
):
    if (
        not current_user
        or
        current_user.role
        !=
        "client"
    ):
        return 0


    return get_swiggy_cart_count(
        db=db,
        user_id=current_user.id,
    )


# =========================================================
# HOME
# =========================================================

@router.get(
    "",
    response_class=HTMLResponse,
)
def swiggy_home(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User | None = Depends(
        get_current_user
    ),
):
    featured_products = (
        get_swiggy_products(
            db=db,
            limit=4,
        )
    )


    cart_count = (
        get_cart_count_for_user(
            db=db,
            current_user=current_user,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name="swiggy/home.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "featured_products":
                featured_products,

            "cart_count":
                cart_count,
        },
    )


# =========================================================
# PRODUCTS
# =========================================================

@router.get(
    "/products",
    response_class=HTMLResponse,
)
def swiggy_products_page(
    request: Request,

    q: str = Query(
        default=""
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User | None = Depends(
        get_current_user
    ),
):
    search_query = (
        q.strip()
    )


    products = (
        get_swiggy_products(
            db=db,
            search_query=search_query,
        )
    )


    cart_count = (
        get_cart_count_for_user(
            db=db,
            current_user=current_user,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name="swiggy/products.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "products":
                products,

            "search_query":
                search_query,

            "cart_count":
                cart_count,
        },
    )


# =========================================================
# PRODUCT DETAIL
# =========================================================

@router.get(
    "/products/{product_id}",
    response_class=HTMLResponse,
)
def swiggy_product_detail(
    request: Request,
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User | None = Depends(
        get_current_user
    ),
):
    product = (
        get_swiggy_product(
            db=db,
            product_id=product_id,
        )
    )


    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Swiggy product not found"
            ),
        )


    cart_count = (
        get_cart_count_for_user(
            db=db,
            current_user=current_user,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name=(
            "swiggy/"
            "product_detail.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "product":
                product,

            "cart_count":
                cart_count,
        },
    )


# =========================================================
# CART PAGE
# =========================================================

@router.get(
    "/cart",
    response_class=HTMLResponse,
)
def swiggy_cart_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    cart = (
        get_swiggy_cart_details(
            db=db,
            user_id=current_user.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name="swiggy/cart.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "cart":
                cart,

            "cart_count":
                cart[
                    "item_count"
                ],

            "error":
                None,
        },
    )


# =========================================================
# ADD TO CART
# =========================================================

@router.post(
    "/cart/add/{product_id}"
)
def swiggy_add_to_cart(
    product_id: int,

    quantity: int = Form(
        1
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    product = (
        get_swiggy_product(
            db=db,
            product_id=product_id,
        )
    )


    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Swiggy product not found"
            ),
        )


    if quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Quantity must be "
                "greater than 0"
            ),
        )


    cart = (
        get_swiggy_cart(
            db=db,
            user_id=current_user.id,
        )
    )


    current_quantity = int(
        cart.get(
            product_id,
            cart.get(
                str(product_id),
                0,
            ),
        )
        or
        0
    )


    requested_quantity = (
        current_quantity
        +
        quantity
    )


    if (
        requested_quantity
        >
        product.stock_quantity
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"Only "
                f"{product.stock_quantity} "
                "units are currently "
                "available"
            ),
        )


    add_to_cart(
        db=db,
        user_id=current_user.id,
        product_id=product_id,
        quantity=quantity,
    )


    return RedirectResponse(
        url="/swiggy/cart",
        status_code=303,
    )


# =========================================================
# UPDATE CART ITEM
# =========================================================

@router.post(
    "/cart/update/{product_id}",
    response_class=HTMLResponse,
)
def swiggy_update_cart_item(
    request: Request,
    product_id: int,

    quantity: int = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    product = (
        get_swiggy_product(
            db=db,
            product_id=product_id,
        )
    )


    if product is None:

        remove_from_cart(
            db=db,
            user_id=current_user.id,
            product_id=product_id,
        )


        return RedirectResponse(
            url="/swiggy/cart",
            status_code=303,
        )


    if quantity <= 0:

        remove_from_cart(
            db=db,
            user_id=current_user.id,
            product_id=product_id,
        )


        return RedirectResponse(
            url="/swiggy/cart",
            status_code=303,
        )


    if (
        quantity
        >
        product.stock_quantity
    ):

        cart = (
            get_swiggy_cart_details(
                db=db,
                user_id=current_user.id,
            )
        )


        return templates.TemplateResponse(
            request=request,
            name="swiggy/cart.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "cart":
                    cart,

                "cart_count":
                    cart[
                        "item_count"
                    ],

                "error":
                    (
                        f"Only "
                        f"{product.stock_quantity} "
                        f"units of "
                        f"{product.product_name} "
                        "are available."
                    ),
            },
            status_code=400,
        )


    set_cart_quantity(
        db=db,
        user_id=current_user.id,
        product_id=product_id,
        quantity=quantity,
    )


    return RedirectResponse(
        url="/swiggy/cart",
        status_code=303,
    )


# =========================================================
# REMOVE CART ITEM
# =========================================================

@router.post(
    "/cart/remove/{product_id}"
)
def swiggy_remove_cart_item(
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    remove_from_cart(
        db=db,
        user_id=current_user.id,
        product_id=product_id,
    )


    return RedirectResponse(
        url="/swiggy/cart",
        status_code=303,
    )


# =========================================================
# CLEAR CART
# =========================================================

@router.post(
    "/cart/clear"
)
def swiggy_clear_cart(
    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    clear_swiggy_cart(
        db=db,
        user_id=current_user.id,
    )


    return RedirectResponse(
        url="/swiggy/cart",
        status_code=303,
    )


# =========================================================
# CHECKOUT PAGE
# =========================================================

@router.get(
    "/checkout",
    response_class=HTMLResponse,
)
def swiggy_checkout_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    cart = (
        get_swiggy_cart_details(
            db=db,
            user_id=current_user.id,
        )
    )


    if not cart["items"]:

        return RedirectResponse(
            url="/swiggy/cart",
            status_code=303,
        )


    if cart["has_stock_errors"]:

        return RedirectResponse(
            url="/swiggy/cart",
            status_code=303,
        )


    # =========================================
    # CLIENT PROFILE
    # =========================================

    profile = (
        get_client_profile(
            db=db,
            user_id=current_user.id,
        )
    )


    delivery_name = (
        profile.full_name
        if (
            profile
            and
            profile.full_name
        )
        else
        current_user.username
    )


    delivery_phone = (
        profile.phone
        if profile
        else ""
    ) or ""


    delivery_address_line1 = (
        profile.address_line1
        if profile
        else ""
    ) or ""


    delivery_address_line2 = (
        profile.address_line2
        if profile
        else ""
    ) or ""


    delivery_city = (
        profile.city
        if profile
        else ""
    ) or ""


    delivery_state = (
        profile.state
        if profile
        else ""
    ) or ""


    delivery_postal_code = (
        profile.postal_code
        if profile
        else ""
    ) or ""


    delivery_country = (
        profile.country
        if (
            profile
            and
            profile.country
        )
        else
        "India"
    )


    return templates.TemplateResponse(
        request=request,
        name="swiggy/checkout.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "cart":
                cart,

            "cart_count":
                cart[
                    "item_count"
                ],

            "delivery_name":
                delivery_name,

            "delivery_phone":
                delivery_phone,

            "delivery_address_line1":
                delivery_address_line1,

            "delivery_address_line2":
                delivery_address_line2,

            "delivery_city":
                delivery_city,

            "delivery_state":
                delivery_state,

            "delivery_postal_code":
                delivery_postal_code,

            "delivery_country":
                delivery_country,

            "error":
                None,
        },
    )


# =========================================================
# CHECKOUT SUBMIT
# =========================================================

@router.post(
    "/checkout",
    response_class=HTMLResponse,
)
def swiggy_checkout_submit(
    request: Request,
    background_tasks: BackgroundTasks,

    delivery_name: str = Form(
        ...
    ),

    delivery_phone: str = Form(
        ...
    ),

    delivery_address_line1: str = Form(
        ...
    ),

    delivery_address_line2: str = Form(
        ""
    ),

    delivery_city: str = Form(
        ...
    ),

    delivery_state: str = Form(
        ...
    ),

    delivery_postal_code: str = Form(
        ...
    ),

    delivery_country: str = Form(
        "India"
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    # =========================================
    # CLEAN INPUT
    # =========================================

    delivery_name = (
        delivery_name.strip()
    )


    delivery_phone = (
        delivery_phone.strip()
    )


    delivery_address_line1 = (
        delivery_address_line1.strip()
    )


    delivery_address_line2 = (
        delivery_address_line2.strip()
    )


    delivery_city = (
        delivery_city.strip()
    )


    delivery_state = (
        delivery_state.strip()
    )


    delivery_postal_code = (
        delivery_postal_code.strip()
    )


    delivery_country = (
        delivery_country.strip()
    )


    # =========================================
    # CART
    # =========================================

    cart_data = (
        get_swiggy_cart(
            db=db,
            user_id=current_user.id,
        )
    )


    cart = (
        get_swiggy_cart_details(
            db=db,
            user_id=current_user.id,
        )
    )


    # =========================================
    # ERROR RESPONSE
    # =========================================

    def return_checkout_error(
        message: str,
    ):
        return templates.TemplateResponse(
            request=request,
            name="swiggy/checkout.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "cart":
                    cart,

                "cart_count":
                    cart[
                        "item_count"
                    ],

                "delivery_name":
                    delivery_name,

                "delivery_phone":
                    delivery_phone,

                "delivery_address_line1":
                    delivery_address_line1,

                "delivery_address_line2":
                    delivery_address_line2,

                "delivery_city":
                    delivery_city,

                "delivery_state":
                    delivery_state,

                "delivery_postal_code":
                    delivery_postal_code,

                "delivery_country":
                    delivery_country,

                "error":
                    message,
            },
            status_code=400,
        )


    # =========================================
    # CART VALIDATION
    # =========================================

    if not cart["items"]:

        return RedirectResponse(
            url="/swiggy/cart",
            status_code=303,
        )


    if cart["has_stock_errors"]:

        return return_checkout_error(
            "One or more products are "
            "no longer available."
        )


    # =========================================
    # REQUIRED DELIVERY FIELDS
    # =========================================

    if not delivery_name:

        return return_checkout_error(
            "Delivery name is required."
        )


    if not delivery_phone:

        return return_checkout_error(
            "Phone number is required."
        )


    if not delivery_address_line1:

        return return_checkout_error(
            "Delivery address is required."
        )


    if not delivery_city:

        return return_checkout_error(
            "City is required."
        )


    if not delivery_state:

        return return_checkout_error(
            "State is required."
        )


    if not delivery_postal_code:

        return return_checkout_error(
            "Postal code is required."
        )


    if not delivery_country:

        return return_checkout_error(
            "Country is required."
        )


    # =========================================
    # LENGTH VALIDATION
    # =========================================

    if len(
        delivery_name
    ) > 100:

        return return_checkout_error(
            "Delivery name cannot exceed "
            "100 characters."
        )


    if len(
        delivery_phone
    ) > 20:

        return return_checkout_error(
            "Phone number cannot exceed "
            "20 characters."
        )


    if len(
        delivery_address_line1
    ) > 255:

        return return_checkout_error(
            "Address line 1 cannot exceed "
            "255 characters."
        )


    if len(
        delivery_address_line2
    ) > 255:

        return return_checkout_error(
            "Address line 2 cannot exceed "
            "255 characters."
        )


    if len(
        delivery_city
    ) > 100:

        return return_checkout_error(
            "City cannot exceed "
            "100 characters."
        )


    if len(
        delivery_state
    ) > 100:

        return return_checkout_error(
            "State cannot exceed "
            "100 characters."
        )


    if len(
        delivery_postal_code
    ) > 20:

        return return_checkout_error(
            "Postal code cannot exceed "
            "20 characters."
        )


    if len(
        delivery_country
    ) > 100:

        return return_checkout_error(
            "Country cannot exceed "
            "100 characters."
        )


    # =========================================
    # CREATE ORDER
    # =========================================

    try:

        created_orders = (
            create_cart_orders(
                db=db,

                cart=cart_data,

                customer_name=(
                    delivery_name
                ),

                order_date=(
                    date.today()
                ),

                client_id=(
                    current_user.id
                ),

                delivery_name=(
                    delivery_name
                ),

                delivery_phone=(
                    delivery_phone
                ),

                delivery_address_line1=(
                    delivery_address_line1
                ),

                delivery_address_line2=(
                    delivery_address_line2
                    or
                    None
                ),

                delivery_city=(
                    delivery_city
                ),

                delivery_state=(
                    delivery_state
                ),

                delivery_postal_code=(
                    delivery_postal_code
                ),

                delivery_country=(
                    delivery_country
                ),
            )
        )


    except ValueError as error:

        cart = (
            get_swiggy_cart_details(
                db=db,
                user_id=current_user.id,
            )
        )


        return return_checkout_error(
            str(error)
        )


    # =========================================
    # FIND CREATED ORDER
    # =========================================

    swiggy_result = None


    for result in created_orders:

        if (
            result[
                "platform"
            ]
            ==
            "swiggy"
        ):

            swiggy_result = (
                result
            )

            break


    if swiggy_result is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Swiggy order was "
                "not created"
            ),
        )


    order = (
        swiggy_result[
            "order"
        ]
    )


    # =========================================
    # ORDER HISTORY
    # =========================================

    record_order_created(
        db=db,
        platform="swiggy",
        order_id=order.id,
        changed_by=current_user.id,
    )


    # =========================================
    # EMAIL DATA
    # =========================================

    email_items = []


    for item in (
        swiggy_result[
            "items"
        ]
    ):

        email_items.append(
            {
                "product_name":
                    item[
                        "product_name"
                    ],

                "quantity":
                    int(
                        item[
                            "quantity"
                        ]
                    ),

                "line_total":
                    float(
                        item[
                            "line_total"
                        ]
                    ),
            }
        )


    # =========================================
    # CLIENT CONFIRMATION EMAIL
    # =========================================

    background_tasks.add_task(
        send_client_order_confirmation,

        platform="swiggy",

        client_email=(
            current_user.email
        ),

        client_name=(
            current_user.username
        ),

        customer_name=(
            order.customer_name
        ),

        order_number=(
            order.order_number
        ),

        order_date=(
            order.order_date
        ),

        status=(
            order.status
        ),

        amount=(
            float(
                order.amount
            )
        ),

        items=(
            email_items
        ),
    )


    # =========================================
    # ADMIN EMAIL
    # =========================================

    background_tasks.add_task(
        send_admin_new_order_notification,

        platform="swiggy",

        client_email=(
            current_user.email
        ),

        client_name=(
            current_user.username
        ),

        customer_name=(
            order.customer_name
        ),

        order_number=(
            order.order_number
        ),

        order_date=(
            order.order_date
        ),

        status=(
            order.status
        ),

        amount=(
            float(
                order.amount
            )
        ),

        items=(
            email_items
        ),
    )


    # =========================================
    # CLEAR CART
    # =========================================

    clear_swiggy_cart(
        db=db,
        user_id=current_user.id,
    )


    # =========================================
    # SUCCESS
    # =========================================

    return RedirectResponse(
        url=(
            "/swiggy/order-success/"
            f"{order.id}"
        ),
        status_code=303,
    )


# =========================================================
# ORDER SUCCESS
# =========================================================

@router.get(
    "/order-success/{order_id}",
    response_class=HTMLResponse,
)
def swiggy_order_success(
    request: Request,
    order_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    order = (
        get_client_swiggy_order(
            db=db,
            client_id=current_user.id,
            order_id=order_id,
        )
    )


    if order is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Swiggy order not found"
            ),
        )


    order_items = (
        get_order_items(
            db=db,
            platform="swiggy",
            order_id=order.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name=(
            "swiggy/"
            "order_success.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "order":
                order,

            "order_items":
                order_items,

            "cart_count":
                get_swiggy_cart_count(
                    db=db,
                    user_id=current_user.id,
                ),
        },
    )


# =========================================================
# MY ORDERS
# =========================================================

@router.get(
    "/my-orders",
    response_class=HTMLResponse,
)
def swiggy_my_orders(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    orders = (
        get_client_swiggy_orders(
            db=db,
            client_id=current_user.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name="swiggy/orders.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "orders":
                orders,

            "cart_count":
                get_swiggy_cart_count(
                    db=db,
                    user_id=current_user.id,
                ),
        },
    )


# =========================================================
# MY ORDER DETAIL
# =========================================================

@router.get(
    "/my-orders/{order_id}",
    response_class=HTMLResponse,
)
def swiggy_my_order_detail(
    request: Request,
    order_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    order = (
        get_client_swiggy_order(
            db=db,
            client_id=current_user.id,
            order_id=order_id,
        )
    )


    if order is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Swiggy order not found"
            ),
        )


    order_items = (
        get_order_items(
            db=db,
            platform="swiggy",
            order_id=order.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name=(
            "swiggy/"
            "order_detail.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "order":
                order,

            "order_items":
                order_items,

            "cart_count":
                get_swiggy_cart_count(
                    db=db,
                    user_id=current_user.id,
                ),
        },
    )