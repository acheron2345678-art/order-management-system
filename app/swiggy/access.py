from fastapi import (
    Depends,
    HTTPException,
    Request,
)

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
)

from app.database import (
    get_db,
)

from app.merchants.models import (
    MerchantRestaurant,
)

from app.users.models import (
    User,
)


def enforce_merchant_swiggy_scope(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User | None = Depends(
        get_current_user
    ),
):
    # =====================================================
    # PUBLIC / CLIENT / ADMIN
    # =====================================================
    #
    # This restriction applies only to Merchant accounts.
    #
    # Normal Swiggy behaviour remains unchanged for:
    #
    # - unauthenticated visitors
    # - clients
    # - admins
    #
    # =====================================================

    if (
        current_user is None
        or
        current_user.role != "merchant"
    ):
        return current_user


    # =====================================================
    # FIND MERCHANT RESTAURANT
    # =====================================================

    assignment = (
        db.query(
            MerchantRestaurant
        )
        .filter(
            MerchantRestaurant.user_id
            ==
            current_user.id
        )
        .first()
    )


    if assignment is None:

        raise HTTPException(
            status_code=403,
            detail=(
                "Merchant account is not linked "
                "to a restaurant."
            ),
        )


    if assignment.restaurant_id is None:

        raise HTTPException(
            status_code=403,
            detail=(
                "Merchant account does not have "
                "a valid restaurant assignment."
            ),
        )


    # =====================================================
    # NORMALIZE REQUEST PATH
    # =====================================================

    request_path = (
        request.url.path.rstrip("/")
    )


    allowed_path = (
        "/swiggy/restaurants/"
        f"{assignment.restaurant_id}"
    )


    # =====================================================
    # ONLY ALLOW OWN RESTAURANT PAGE
    # =====================================================

    if request_path == allowed_path:

        return current_user


    # =====================================================
    # ANOTHER RESTAURANT
    # =====================================================
    #
    # Use 404 rather than exposing whether another
    # restaurant exists.
    #
    # =====================================================

    if request_path.startswith(
        "/swiggy/restaurants/"
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Restaurant preview not found."
            ),
        )


    # =====================================================
    # BLOCK EVERYTHING ELSE IN SWIGGY
    # =====================================================

    raise HTTPException(
        status_code=403,
        detail=(
            "Merchant accounts can access only "
            "their assigned restaurant preview."
        ),
    )