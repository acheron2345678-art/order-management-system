from datetime import datetime

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

from app.database import get_db

from app.products.service import (
    create_catalog_item,
    get_admin_catalog_products,
    get_admin_product,
    set_catalog_item_active_state,
    update_catalog_item,
)

from app.users.models import User


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


# =========================================================
# ADMIN CATALOG
# =========================================================

@router.get(
    "",
    response_class=HTMLResponse,
)
def products_page(
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    products = (
        get_admin_catalog_products(
            db=db,
            include_inactive=True,
        )
    )

    swiggy_products = [
        product
        for product in products
        if (
            product.platform
            and
            product.platform.lower()
            ==
            "swiggy"
        )
    ]

    insights_services = [
        product
        for product in products
        if (
            product.platform
            and
            product.platform.lower()
            ==
            "insights"
        )
    ]

    swiggy_active_count = sum(
        1
        for product in swiggy_products
        if product.is_active
    )

    swiggy_inactive_count = (
        len(swiggy_products)
        -
        swiggy_active_count
    )

    insights_active_count = sum(
        1
        for product in insights_services
        if product.is_active
    )

    insights_inactive_count = (
        len(insights_services)
        -
        insights_active_count
    )

    return templates.TemplateResponse(
        request=request,
        name="products/products.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "products":
                products,

            "swiggy_products":
                swiggy_products,

            "insights_services":
                insights_services,

            "swiggy_active_count":
                swiggy_active_count,

            "swiggy_inactive_count":
                swiggy_inactive_count,

            "insights_active_count":
                insights_active_count,

            "insights_inactive_count":
                insights_inactive_count,
        },
    )


# =========================================================
# ADD CATALOG ITEM PAGE
# =========================================================

@router.get(
    "/add",
    response_class=HTMLResponse,
)
def add_catalog_item_page(
    request: Request,
    current_user: User = Depends(
        require_admin
    ),
):
    return templates.TemplateResponse(
        request=request,
        name="products/product_form.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "action":
                "add",

            "product":
                None,

            "product_name":
                "",

            "description":
                "",

            "price":
                "",

            "platform":
                "swiggy",

            "stock_quantity":
                0,

            "reorder_level":
                5,

            "error":
                None,
        },
    )


# =========================================================
# CREATE CATALOG ITEM
# =========================================================

@router.post(
    "/add",
    response_class=HTMLResponse,
)
def add_catalog_item(
    request: Request,

    product_name: str = Form(
        ...
    ),

    description: str = Form(
        ""
    ),

    price: str = Form(
        ...
    ),

    platform: str = Form(
        ...
    ),

    stock_quantity: int = Form(
        0
    ),

    reorder_level: int = Form(
        5
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product_name = (
        product_name.strip()
    )

    description = (
        description.strip()
    )

    platform = (
        platform
        .strip()
        .lower()
    )

    try:

        product = create_catalog_item(
            db=db,

            product_name=(
                product_name
            ),

            description=(
                description
            ),

            price=(
                price
            ),

            platform=(
                platform
            ),

            stock_quantity=(
                stock_quantity
            ),

            reorder_level=(
                reorder_level
            ),
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,
            name="products/product_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "add",

                "product":
                    None,

                "product_name":
                    product_name,

                "description":
                    description,

                "price":
                    price,

                "platform":
                    platform,

                "stock_quantity":
                    stock_quantity,

                "reorder_level":
                    reorder_level,

                "error":
                    str(error),
            },
            status_code=400,
        )

    return RedirectResponse(
        url=(
            f"/products/{product.id}"
        ),
        status_code=303,
    )


# =========================================================
# EDIT CATALOG ITEM PAGE
# =========================================================

@router.get(
    "/{product_id}/edit",
    response_class=HTMLResponse,
)
def edit_catalog_item_page(
    product_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name="products/product_form.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "action":
                "edit",

            "product":
                product,

            "product_name":
                product.product_name,

            "description":
                (
                    product.description
                    or
                    ""
                ),

            "price":
                product.price,

            "platform":
                product.platform.lower(),

            "stock_quantity":
                product.stock_quantity,

            "reorder_level":
                product.reorder_level,

            "error":
                None,
        },
    )


# =========================================================
# UPDATE CATALOG ITEM
# =========================================================

@router.post(
    "/{product_id}/edit",
    response_class=HTMLResponse,
)
def edit_catalog_item(
    product_id: int,
    request: Request,

    product_name: str = Form(
        ...
    ),

    description: str = Form(
        ""
    ),

    price: str = Form(
        ...
    ),

    stock_quantity: int = Form(
        0
    ),

    reorder_level: int = Form(
        0
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    product_name = (
        product_name.strip()
    )

    description = (
        description.strip()
    )

    try:

        product = update_catalog_item(
            db=db,

            product=product,

            product_name=(
                product_name
            ),

            description=(
                description
            ),

            price=(
                price
            ),

            stock_quantity=(
                stock_quantity
            ),

            reorder_level=(
                reorder_level
            ),
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,
            name="products/product_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "edit",

                "product":
                    product,

                "product_name":
                    product_name,

                "description":
                    description,

                "price":
                    price,

                "platform":
                    product.platform.lower(),

                "stock_quantity":
                    stock_quantity,

                "reorder_level":
                    reorder_level,

                "error":
                    str(error),
            },
            status_code=400,
        )

    return RedirectResponse(
        url=(
            f"/products/{product.id}"
        ),
        status_code=303,
    )


# =========================================================
# RESTOCK PAGE
# SWIGGY ONLY
# =========================================================

@router.get(
    "/{product_id}/restock",
    response_class=HTMLResponse,
)
def restock_product_page(
    product_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if (
        not product.platform
        or
        product.platform.lower()
        !=
        "swiggy"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Swiggy products "
                "can be restocked."
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name="products/restock.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "product":
                product,

            "error":
                None,
        },
    )


# =========================================================
# RESTOCK PRODUCT
# =========================================================

@router.post(
    "/{product_id}/restock",
    response_class=HTMLResponse,
)
def restock_product(
    product_id: int,
    request: Request,

    quantity: int = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if (
        not product.platform
        or
        product.platform.lower()
        !=
        "swiggy"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Swiggy products "
                "can be restocked."
            ),
        )

    if quantity <= 0:

        return templates.TemplateResponse(
            request=request,
            name="products/restock.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "product":
                    product,

                "error":
                    (
                        "Restock quantity must "
                        "be greater than zero."
                    ),
            },
            status_code=400,
        )

    try:

        product.stock_quantity = (
            product.stock_quantity
            +
            quantity
        )

        product.last_restocked = (
            datetime.now()
        )

        db.commit()

        db.refresh(
            product
        )

    except Exception:

        db.rollback()

        raise

    return RedirectResponse(
        url=(
            f"/products/{product.id}"
        ),
        status_code=303,
    )


# =========================================================
# DEACTIVATE
# =========================================================

@router.post(
    "/{product_id}/deactivate"
)
def deactivate_catalog_item(
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    set_catalog_item_active_state(
        db=db,
        product=product,
        is_active=False,
    )

    return RedirectResponse(
        url="/products",
        status_code=303,
    )


# =========================================================
# ACTIVATE
# =========================================================

@router.post(
    "/{product_id}/activate"
)
def activate_catalog_item(
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    set_catalog_item_active_state(
        db=db,
        product=product,
        is_active=True,
    )

    return RedirectResponse(
        url="/products",
        status_code=303,
    )


# =========================================================
# CATALOG ITEM DETAIL
# KEEP THIS AFTER THE MORE SPECIFIC ROUTES
# =========================================================

@router.get(
    "/{product_id}",
    response_class=HTMLResponse,
)
def product_detail(
    product_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name="products/product_detail.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "product":
                product,
        },
    )
from datetime import datetime

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

from app.database import get_db

from app.products.service import (
    create_catalog_item,
    get_admin_catalog_products,
    get_admin_product,
    set_catalog_item_active_state,
    update_catalog_item,
)

from app.restaurants.service import (
    get_restaurants,
)

from app.users.models import User


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


# =========================================================
# ADMIN CATALOG
# =========================================================

@router.get(
    "",
    response_class=HTMLResponse,
)
def products_page(
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    products = (
        get_admin_catalog_products(
            db=db,
            include_inactive=True,
        )
    )

    swiggy_products = [
        product
        for product in products
        if (
            product.platform
            and
            product.platform.lower()
            ==
            "swiggy"
        )
    ]

    insights_services = [
        product
        for product in products
        if (
            product.platform
            and
            product.platform.lower()
            ==
            "insights"
        )
    ]

    swiggy_active_count = sum(
        1
        for product in swiggy_products
        if product.is_active
    )

    swiggy_inactive_count = (
        len(swiggy_products)
        -
        swiggy_active_count
    )

    insights_active_count = sum(
        1
        for product in insights_services
        if product.is_active
    )

    insights_inactive_count = (
        len(insights_services)
        -
        insights_active_count
    )

    return templates.TemplateResponse(
        request=request,
        name="products/products.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "products":
                products,

            "swiggy_products":
                swiggy_products,

            "insights_services":
                insights_services,

            "swiggy_active_count":
                swiggy_active_count,

            "swiggy_inactive_count":
                swiggy_inactive_count,

            "insights_active_count":
                insights_active_count,

            "insights_inactive_count":
                insights_inactive_count,
        },
    )


# =========================================================
# ADD CATALOG ITEM PAGE
# =========================================================

@router.get(
    "/add",
    response_class=HTMLResponse,
)
def add_catalog_item_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    restaurants = get_restaurants(
        db,
        include_inactive=True,
    )

    return templates.TemplateResponse(
        request=request,
        name="products/product_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "action": "add",
            "product": None,
            "product_name": "",
            "description": "",
            "price": "",
            "platform": "swiggy",
            "stock_quantity": 0,
            "reorder_level": 5,
            "restaurants": restaurants,
            "restaurant_id": "",
            "menu_category": "Recommended",
            "is_bestseller": False,
            "error": None,
        },
    )


# =========================================================
# CREATE CATALOG ITEM
# =========================================================

@router.post(
    "/add",
    response_class=HTMLResponse,
)
def add_catalog_item(
    request: Request,

    product_name: str = Form(...),
    description: str = Form(""),
    price: str = Form(...),
    platform: str = Form(...),
    stock_quantity: int = Form(0),
    reorder_level: int = Form(5),
    restaurant_id: str = Form(""),
    menu_category: str = Form(""),
    is_bestseller: bool = Form(False),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product_name = product_name.strip()
    description = description.strip()
    platform = platform.strip().lower()
    restaurant_id = restaurant_id.strip()
    menu_category = menu_category.strip()

    restaurants = get_restaurants(
        db,
        include_inactive=True,
    )

    try:
        product = create_catalog_item(
            db=db,
            product_name=product_name,
            description=description,
            price=price,
            platform=platform,
            stock_quantity=stock_quantity,
            reorder_level=reorder_level,
            restaurant_id=(
                restaurant_id
                if restaurant_id
                else None
            ),
            menu_category=menu_category,
            is_bestseller=is_bestseller,
        )

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="products/product_form.html",
            context={
                "request": request,
                "current_user": current_user,
                "action": "add",
                "product": None,
                "product_name": product_name,
                "description": description,
                "price": price,
                "platform": platform,
                "stock_quantity": stock_quantity,
                "reorder_level": reorder_level,
                "restaurants": restaurants,
                "restaurant_id": restaurant_id,
                "menu_category": menu_category,
                "is_bestseller": is_bestseller,
                "error": str(error),
            },
            status_code=400,
        )

    return RedirectResponse(
        url=f"/products/{product.id}",
        status_code=303,
    )


# =========================================================
# EDIT CATALOG ITEM PAGE
# =========================================================

@router.get(
    "/{product_id}/edit",
    response_class=HTMLResponse,
)
def edit_catalog_item_page(
    product_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Catalog item not found",
        )

    restaurants = get_restaurants(
        db,
        include_inactive=True,
    )

    return templates.TemplateResponse(
        request=request,
        name="products/product_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "action": "edit",
            "product": product,
            "product_name": product.product_name,
            "description": product.description or "",
            "price": product.price,
            "platform": product.platform.lower(),
            "stock_quantity": product.stock_quantity,
            "reorder_level": product.reorder_level,
            "restaurants": restaurants,
            "restaurant_id": product.restaurant_id or "",
            "menu_category": product.menu_category or "",
            "is_bestseller": bool(product.is_bestseller),
            "error": None,
        },
    )


# =========================================================
# UPDATE CATALOG ITEM
# =========================================================

@router.post(
    "/{product_id}/edit",
    response_class=HTMLResponse,
)
def edit_catalog_item(
    product_id: int,
    request: Request,

    product_name: str = Form(...),
    description: str = Form(""),
    price: str = Form(...),
    stock_quantity: int = Form(0),
    reorder_level: int = Form(0),
    restaurant_id: str = Form(""),
    menu_category: str = Form(""),
    is_bestseller: bool = Form(False),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Catalog item not found",
        )

    product_name = product_name.strip()
    description = description.strip()
    restaurant_id = restaurant_id.strip()
    menu_category = menu_category.strip()

    restaurants = get_restaurants(
        db,
        include_inactive=True,
    )

    try:
        product = update_catalog_item(
            db=db,
            product=product,
            product_name=product_name,
            description=description,
            price=price,
            stock_quantity=stock_quantity,
            reorder_level=reorder_level,
            restaurant_id=(
                restaurant_id
                if restaurant_id
                else None
            ),
            menu_category=menu_category,
            is_bestseller=is_bestseller,
        )

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="products/product_form.html",
            context={
                "request": request,
                "current_user": current_user,
                "action": "edit",
                "product": product,
                "product_name": product_name,
                "description": description,
                "price": price,
                "platform": product.platform.lower(),
                "stock_quantity": stock_quantity,
                "reorder_level": reorder_level,
                "restaurants": restaurants,
                "restaurant_id": restaurant_id,
                "menu_category": menu_category,
                "is_bestseller": is_bestseller,
                "error": str(error),
            },
            status_code=400,
        )

    return RedirectResponse(
        url=f"/products/{product.id}",
        status_code=303,
    )


# =========================================================
# RESTOCK PAGE
# SWIGGY ONLY
# =========================================================

@router.get(
    "/{product_id}/restock",
    response_class=HTMLResponse,
)
def restock_product_page(
    product_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if (
        not product.platform
        or
        product.platform.lower()
        !=
        "swiggy"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Swiggy products "
                "can be restocked."
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name="products/restock.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "product":
                product,

            "error":
                None,
        },
    )


# =========================================================
# RESTOCK PRODUCT
# =========================================================

@router.post(
    "/{product_id}/restock",
    response_class=HTMLResponse,
)
def restock_product(
    product_id: int,
    request: Request,

    quantity: int = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if (
        not product.platform
        or
        product.platform.lower()
        !=
        "swiggy"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Swiggy products "
                "can be restocked."
            ),
        )

    if quantity <= 0:

        return templates.TemplateResponse(
            request=request,
            name="products/restock.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "product":
                    product,

                "error":
                    (
                        "Restock quantity must "
                        "be greater than zero."
                    ),
            },
            status_code=400,
        )

    try:

        product.stock_quantity = (
            product.stock_quantity
            +
            quantity
        )

        product.last_restocked = (
            datetime.now()
        )

        db.commit()

        db.refresh(
            product
        )

    except Exception:

        db.rollback()

        raise

    return RedirectResponse(
        url=(
            f"/products/{product.id}"
        ),
        status_code=303,
    )


# =========================================================
# DEACTIVATE
# =========================================================

@router.post(
    "/{product_id}/deactivate"
)
def deactivate_catalog_item(
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    set_catalog_item_active_state(
        db=db,
        product=product,
        is_active=False,
    )

    return RedirectResponse(
        url="/products",
        status_code=303,
    )


# =========================================================
# ACTIVATE
# =========================================================

@router.post(
    "/{product_id}/activate"
)
def activate_catalog_item(
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    set_catalog_item_active_state(
        db=db,
        product=product,
        is_active=True,
    )

    return RedirectResponse(
        url="/products",
        status_code=303,
    )


# =========================================================
# CATALOG ITEM DETAIL
# KEEP THIS AFTER THE MORE SPECIFIC ROUTES
# =========================================================

@router.get(
    "/{product_id}",
    response_class=HTMLResponse,
)
def product_detail(
    product_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    product = get_admin_product(
        db=db,
        product_id=product_id,
    )

    if product is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Catalog item not found"
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name="products/product_detail.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "product":
                product,
        },
    )