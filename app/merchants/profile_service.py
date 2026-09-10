from sqlalchemy.orm import Session

from app.merchants.models import (
    MerchantRestaurant,
)

from app.restaurants.service import (
    set_restaurant_active_state,
    update_restaurant,
)


def update_merchant_restaurant_profile(
    db: Session,
    assignment: MerchantRestaurant,
    *,
    name,
    description,
    cuisines,
    delivery_min_minutes,
    delivery_max_minutes,
    location,
    offer_text,
    image_url,
):
    restaurant = assignment.restaurant

    if restaurant is None:
        raise ValueError(
            "The merchant account is not linked "
            "to a valid restaurant."
        )

    # Rating deliberately remains unchanged.
    # Merchant accounts cannot modify their
    # own marketplace rating.
    return update_restaurant(
        db,
        restaurant,
        name=name,
        description=description,
        cuisines=cuisines,
        rating=restaurant.rating,
        delivery_min_minutes=delivery_min_minutes,
        delivery_max_minutes=delivery_max_minutes,
        location=location,
        offer_text=offer_text,
        image_url=image_url,
    )


def set_merchant_restaurant_status(
    db: Session,
    assignment: MerchantRestaurant,
    is_active: bool,
):
    restaurant = assignment.restaurant

    if restaurant is None:
        raise ValueError(
            "The merchant account is not linked "
            "to a valid restaurant."
        )

    return set_restaurant_active_state(
        db,
        restaurant,
        is_active,
    )