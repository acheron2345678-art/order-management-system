from fastapi import (
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_merchant,
)

from app.database import get_db

from app.merchants.models import (
    MerchantRestaurant,
)

from app.users.models import User


def require_merchant_assignment(
    current_user: User = Depends(
        require_merchant
    ),
    db: Session = Depends(
        get_db
    ),
) -> MerchantRestaurant:

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

    if assignment.restaurant is None:

        raise HTTPException(
            status_code=403,
            detail=(
                "The restaurant linked to this "
                "merchant account is unavailable."
            ),
        )

    return assignment