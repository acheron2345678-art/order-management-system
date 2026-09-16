from sqlalchemy.orm import Session

from app.merchants.models import (
    MerchantRestaurant,
)

from app.restaurants.service import (
    set_restaurant_active_state,
    update_restaurant,
)

from app.users.models import (
    User,
)

from app.users.service import (
    update_user,
)

def update_merchant_account_profile(
    db: Session,
    merchant: User,
    *,
    username: str,
    email: str,
):
    """
    Allow a Merchant to update only their
    own account username and email.

    Role, active state and restaurant assignment
    cannot be changed by the Merchant.
    """

    if merchant.role != "merchant":
        raise ValueError(
            "Only Merchant accounts can be updated here."
        )

    return update_user(
        db=db,
        user=merchant,
        username=username,
        email=email,
        role="merchant",
        new_password=None,
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