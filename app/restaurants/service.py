from decimal import Decimal, InvalidOperation

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.orders.validation import (
    clean_optional_text,
    clean_required_text,
    validate_positive_id,
    validate_positive_quantity,
)
from app.products.models import Restaurant


MIN_RATING = Decimal("1.0")
MAX_RATING = Decimal("5.0")
MAX_DELIVERY_MINUTES = 240


def validate_rating(value) -> Decimal:
    try:
        rating = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Rating must be a valid number.") from exc

    if not rating.is_finite():
        raise ValueError("Rating must be a finite number.")

    if rating < MIN_RATING or rating > MAX_RATING:
        raise ValueError("Rating must be between 1.0 and 5.0.")

    return rating.quantize(Decimal("0.1"))


def validate_delivery_window(
    minimum_minutes,
    maximum_minutes,
) -> tuple[int, int]:
    minimum = validate_positive_quantity(
        minimum_minutes,
        "Minimum delivery time",
    )
    maximum = validate_positive_quantity(
        maximum_minutes,
        "Maximum delivery time",
    )

    if minimum > MAX_DELIVERY_MINUTES or maximum > MAX_DELIVERY_MINUTES:
        raise ValueError(
            f"Delivery times cannot exceed {MAX_DELIVERY_MINUTES} minutes."
        )

    if maximum < minimum:
        raise ValueError(
            "Maximum delivery time cannot be less than minimum delivery time."
        )

    return minimum, maximum


def clean_restaurant_form(
    *,
    name,
    description,
    cuisines,
    rating,
    delivery_min_minutes,
    delivery_max_minutes,
    location,
    offer_text,
    image_url,
):
    cleaned_name = clean_required_text(
        name,
        "Restaurant name",
        max_length=120,
    )

    cleaned_description = clean_optional_text(
        description,
        "Description",
        max_length=500,
    )

    cleaned_cuisines = clean_required_text(
        cuisines,
        "Cuisines",
        max_length=255,
    )

    cleaned_location = clean_optional_text(
        location,
        "Location",
        max_length=150,
    )

    cleaned_offer_text = clean_optional_text(
        offer_text,
        "Offer text",
        max_length=150,
    )

    cleaned_image_url = clean_optional_text(
        image_url,
        "Image URL",
        max_length=500,
    )

    cleaned_rating = validate_rating(rating)

    minimum, maximum = validate_delivery_window(
        delivery_min_minutes,
        delivery_max_minutes,
    )

    return {
        "name": cleaned_name,
        "description": cleaned_description,
        "cuisines": cleaned_cuisines,
        "rating": cleaned_rating,
        "delivery_min_minutes": minimum,
        "delivery_max_minutes": maximum,
        "location": cleaned_location,
        "offer_text": cleaned_offer_text,
        "image_url": cleaned_image_url,
    }


def restaurant_name_exists(
    db: Session,
    name: str,
    *,
    exclude_restaurant_id: int | None = None,
) -> bool:
    query = db.query(Restaurant).filter(
        func.lower(Restaurant.name) == name.lower()
    )

    if exclude_restaurant_id is not None:
        query = query.filter(
            Restaurant.id != exclude_restaurant_id
        )

    return query.first() is not None


def get_restaurants(
    db: Session,
    *,
    include_inactive: bool = True,
):
    query = db.query(Restaurant).options(
        selectinload(Restaurant.products)
    )

    if not include_inactive:
        query = query.filter(
            Restaurant.is_active.is_(True)
        )

    return query.order_by(
        Restaurant.is_active.desc(),
        Restaurant.name.asc(),
    ).all()


def get_restaurant(
    db: Session,
    restaurant_id: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    return (
        db.query(Restaurant)
        .options(selectinload(Restaurant.products))
        .filter(Restaurant.id == restaurant_id)
        .first()
    )


def create_restaurant(
    db: Session,
    *,
    name,
    description,
    cuisines,
    rating,
    delivery_min_minutes,
    delivery_max_minutes,
    location,
    offer_text,
    image_url,
):
    data = clean_restaurant_form(
        name=name,
        description=description,
        cuisines=cuisines,
        rating=rating,
        delivery_min_minutes=delivery_min_minutes,
        delivery_max_minutes=delivery_max_minutes,
        location=location,
        offer_text=offer_text,
        image_url=image_url,
    )

    if restaurant_name_exists(db, data["name"]):
        raise ValueError(
            "A restaurant with this name already exists."
        )

    restaurant = Restaurant(
        **data,
        is_active=True,
    )

    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)

    return restaurant


def update_restaurant(
    db: Session,
    restaurant: Restaurant,
    *,
    name,
    description,
    cuisines,
    rating,
    delivery_min_minutes,
    delivery_max_minutes,
    location,
    offer_text,
    image_url,
):
    data = clean_restaurant_form(
        name=name,
        description=description,
        cuisines=cuisines,
        rating=rating,
        delivery_min_minutes=delivery_min_minutes,
        delivery_max_minutes=delivery_max_minutes,
        location=location,
        offer_text=offer_text,
        image_url=image_url,
    )

    if restaurant_name_exists(
        db,
        data["name"],
        exclude_restaurant_id=restaurant.id,
    ):
        raise ValueError(
            "Another restaurant with this name already exists."
        )

    for field, value in data.items():
        setattr(restaurant, field, value)

    db.commit()
    db.refresh(restaurant)

    return restaurant


def set_restaurant_active_state(
    db: Session,
    restaurant: Restaurant,
    is_active: bool,
):
    restaurant.is_active = bool(is_active)

    db.commit()
    db.refresh(restaurant)

    return restaurant