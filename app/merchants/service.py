from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    validate_password,
)

from app.merchants.models import (
    MerchantRestaurant,
)

from app.orders.validation import (
    validate_positive_id,
)

from app.products.models import (
    Restaurant,
)

from app.restaurants.service import (
    clean_restaurant_form,
)

from app.users.models import (
    User,
)

from app.users.service import (
    ensure_email_available,
    ensure_username_available,
    normalize_email,
    normalize_username,
)


MERCHANT_ROLE = "merchant"


def get_merchant_assignment(
    db: Session,
    user_id: int,
):
    user_id = validate_positive_id(
        user_id,
        "User ID",
    )

    return (
        db.query(
            MerchantRestaurant
        )
        .filter(
            MerchantRestaurant.user_id
            ==
            user_id
        )
        .first()
    )


def get_available_restaurants(
    db: Session,
):
    """
    Return restaurants that do not currently
    belong to any merchant account.
    """

    return (
        db.query(
            Restaurant
        )
        .outerjoin(
            MerchantRestaurant,
            MerchantRestaurant.restaurant_id
            ==
            Restaurant.id,
        )
        .filter(
            MerchantRestaurant.id.is_(
                None
            )
        )
        .order_by(
            Restaurant.is_active.desc(),
            Restaurant.name.asc(),
        )
        .all()
    )


def _prepare_merchant_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
) -> User:

    username = normalize_username(
        username
    )

    email = normalize_email(
        email
    )

    password = validate_password(
        password,
        username=username,
        email=email,
    )

    ensure_username_available(
        db,
        username,
    )

    ensure_email_available(
        db,
        email,
    )

    return User(
        username=username,
        email=email,
        password_hash=hash_password(
            password
        ),
        role=MERCHANT_ROLE,
        is_active=True,
    )


def _get_restaurant_by_name(
    db: Session,
    name: str,
):
    return (
        db.query(
            Restaurant
        )
        .filter(
            func.lower(
                Restaurant.name
            )
            ==
            name.lower()
        )
        .first()
    )


def _restaurant_is_claimed(
    db: Session,
    restaurant_id: int,
) -> bool:

    return (
        db.query(
            MerchantRestaurant
        )
        .filter(
            MerchantRestaurant.restaurant_id
            ==
            restaurant_id
        )
        .first()
        is not None
    )


def register_merchant_with_existing_restaurant(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    restaurant_id: int,
):
    restaurant_id = validate_positive_id(
        restaurant_id,
        "Restaurant ID",
    )

    try:

        restaurant = (
            db.query(
                Restaurant
            )
            .filter(
                Restaurant.id
                ==
                restaurant_id
            )
            .with_for_update()
            .first()
        )

        if restaurant is None:

            raise ValueError(
                "The selected restaurant does not exist."
            )

        if _restaurant_is_claimed(
            db,
            restaurant.id,
        ):

            raise ValueError(
                "This restaurant already has a merchant account."
            )

        merchant = _prepare_merchant_user(
            db,
            username=username,
            email=email,
            password=password,
        )

        db.add(
            merchant
        )

        # Obtain merchant.id without committing.
        db.flush()

        assignment = MerchantRestaurant(
            user_id=merchant.id,
            restaurant_id=restaurant.id,
        )

        db.add(
            assignment
        )

        # User + ownership commit together.
        db.commit()

        db.refresh(
            merchant
        )

        db.refresh(
            assignment
        )

        return (
            merchant,
            restaurant,
            assignment,
        )

    except ValueError:

        db.rollback()
        raise

    except IntegrityError as exc:

        db.rollback()

        raise ValueError(
            "The merchant account or restaurant "
            "is already registered."
        ) from exc

    except Exception:

        db.rollback()
        raise


def register_merchant_with_new_restaurant(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    restaurant_name: str,
    cuisines: str,
    description: str = "",
    location: str = "",
    delivery_min_minutes: int = 20,
    delivery_max_minutes: int = 30,
):

    restaurant_data = clean_restaurant_form(
        name=restaurant_name,
        description=description,
        cuisines=cuisines,

        # We start new restaurants at the
        # current project's default rating.
        rating="4.0",

        delivery_min_minutes=(
            delivery_min_minutes
        ),

        delivery_max_minutes=(
            delivery_max_minutes
        ),

        location=location,

        offer_text="",

        image_url="",
    )

    try:

        existing_restaurant = (
            _get_restaurant_by_name(
                db,
                restaurant_data[
                    "name"
                ],
            )
        )

        if existing_restaurant is not None:

            if _restaurant_is_claimed(
                db,
                existing_restaurant.id,
            ):

                raise ValueError(
                    "A restaurant with this name "
                    "already exists and already has "
                    "a merchant account."
                )

            raise ValueError(
                "A restaurant with this name already exists. "
                "Choose it from Existing Restaurants instead."
            )

        merchant = _prepare_merchant_user(
            db,
            username=username,
            email=email,
            password=password,
        )

        restaurant = Restaurant(
            **restaurant_data,
            is_active=True,
        )

        db.add(
            merchant
        )

        db.add(
            restaurant
        )

        # Gives both objects their IDs
        # without committing.
        db.flush()

        assignment = MerchantRestaurant(
            user_id=merchant.id,
            restaurant_id=restaurant.id,
        )

        db.add(
            assignment
        )

        # All three records commit together:
        #
        # User
        # Restaurant
        # MerchantRestaurant

        db.commit()

        db.refresh(
            merchant
        )

        db.refresh(
            restaurant
        )

        db.refresh(
            assignment
        )

        return (
            merchant,
            restaurant,
            assignment,
        )

    except ValueError:

        db.rollback()
        raise

    except IntegrityError as exc:

        db.rollback()

        raise ValueError(
            "The merchant account or restaurant "
            "could not be registered because one "
            "of those values is already in use."
        ) from exc

    except Exception:

        db.rollback()
        raise