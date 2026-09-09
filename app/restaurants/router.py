from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core import templates
from app.database import get_db
from app.restaurants.service import (
    create_restaurant,
    get_restaurant,
    get_restaurants,
    set_restaurant_active_state,
    update_restaurant,
)
from app.users.models import User


router = APIRouter(
    prefix="/admin/restaurants",
    tags=["Admin Restaurants"],
)


def render_restaurant_form(
    *,
    request: Request,
    current_user: User,
    action: str,
    restaurant=None,
    error: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="restaurants/restaurant_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "action": action,
            "restaurant": restaurant,
            "error": error,
            "form_data": form_data,
        },
        status_code=status_code,
    )


@router.get(
    "",
    response_class=HTMLResponse,
)
def restaurants_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    restaurants = get_restaurants(
        db,
        include_inactive=True,
    )

    active_count = sum(
        1
        for restaurant in restaurants
        if restaurant.is_active
    )

    total_dishes = sum(
        len(restaurant.products)
        for restaurant in restaurants
    )

    return templates.TemplateResponse(
        request=request,
        name="restaurants/restaurants.html",
        context={
            "request": request,
            "current_user": current_user,
            "restaurants": restaurants,
            "active_count": active_count,
            "inactive_count": len(restaurants) - active_count,
            "total_dishes": total_dishes,
        },
    )


@router.get(
    "/add",
    response_class=HTMLResponse,
)
def add_restaurant_page(
    request: Request,
    current_user: User = Depends(require_admin),
):
    return render_restaurant_form(
        request=request,
        current_user=current_user,
        action="add",
        restaurant=None,
    )


@router.post(
    "/add",
    response_class=HTMLResponse,
)
def add_restaurant(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    cuisines: str = Form(...),
    rating: str = Form("4.0"),
    delivery_min_minutes: int = Form(20),
    delivery_max_minutes: int = Form(30),
    location: str = Form(""),
    offer_text: str = Form(""),
    image_url: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    form_data = {
        "name": name.strip(),
        "description": description.strip(),
        "cuisines": cuisines.strip(),
        "rating": rating.strip(),
        "delivery_min_minutes": delivery_min_minutes,
        "delivery_max_minutes": delivery_max_minutes,
        "location": location.strip(),
        "offer_text": offer_text.strip(),
        "image_url": image_url.strip(),
    }

    try:
        restaurant = create_restaurant(
            db,
            **form_data,
        )
    except ValueError as error:
        return render_restaurant_form(
            request=request,
            current_user=current_user,
            action="add",
            restaurant=None,
            error=str(error),
            form_data=form_data,
            status_code=400,
        )

    return RedirectResponse(
        url=f"/admin/restaurants/{restaurant.id}",
        status_code=303,
    )


@router.get(
    "/{restaurant_id}",
    response_class=HTMLResponse,
)
def restaurant_detail_page(
    restaurant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    swiggy_products = [
        product
        for product in restaurant.products
        if (
            product.platform
            and product.platform.lower() == "swiggy"
        )
    ]

    categories = sorted(
        {
            (product.menu_category or "Uncategorised").strip()
            or "Uncategorised"
            for product in swiggy_products
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="restaurants/restaurant_detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "restaurant": restaurant,
            "products": swiggy_products,
            "categories": categories,
        },
    )


@router.get(
    "/{restaurant_id}/edit",
    response_class=HTMLResponse,
)
def edit_restaurant_page(
    restaurant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    return render_restaurant_form(
        request=request,
        current_user=current_user,
        action="edit",
        restaurant=restaurant,
    )


@router.post(
    "/{restaurant_id}/edit",
    response_class=HTMLResponse,
)
def edit_restaurant(
    restaurant_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    cuisines: str = Form(...),
    rating: str = Form("4.0"),
    delivery_min_minutes: int = Form(20),
    delivery_max_minutes: int = Form(30),
    location: str = Form(""),
    offer_text: str = Form(""),
    image_url: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    form_data = {
        "name": name.strip(),
        "description": description.strip(),
        "cuisines": cuisines.strip(),
        "rating": rating.strip(),
        "delivery_min_minutes": delivery_min_minutes,
        "delivery_max_minutes": delivery_max_minutes,
        "location": location.strip(),
        "offer_text": offer_text.strip(),
        "image_url": image_url.strip(),
    }

    try:
        update_restaurant(
            db,
            restaurant,
            **form_data,
        )
    except ValueError as error:
        return render_restaurant_form(
            request=request,
            current_user=current_user,
            action="edit",
            restaurant=restaurant,
            error=str(error),
            form_data=form_data,
            status_code=400,
        )

    return RedirectResponse(
        url=f"/admin/restaurants/{restaurant.id}",
        status_code=303,
    )


@router.post(
    "/{restaurant_id}/toggle",
)
def toggle_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    set_restaurant_active_state(
        db,
        restaurant,
        not restaurant.is_active,
    )

    return RedirectResponse(
        url="/admin/restaurants",
        status_code=303,
    )