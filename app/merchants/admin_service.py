
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.merchants.models import (
    MerchantRestaurant,
)

from app.orders.validation import (
    validate_positive_id,
)

from app.products.models import (
    Restaurant,
)

from app.users.models import (
    User,
)

from app.users.service import (
    set_user_active_status,
    update_user
)


MERCHANT_ROLE = "merchant"


# =========================================================
# MERCHANT ACCOUNTS
# =========================================================

def get_admin_merchant_accounts(
    db: Session,
):

    rows = (
        db.query(
            User,
            MerchantRestaurant,
            Restaurant,
        )

        .outerjoin(
            MerchantRestaurant,
            MerchantRestaurant.user_id
            ==
            User.id,
        )

        .outerjoin(
            Restaurant,
            Restaurant.id
            ==
            MerchantRestaurant.restaurant_id,
        )

        .filter(
            User.role
            ==
            MERCHANT_ROLE
        )

        .order_by(
            User.id.desc()
        )

        .all()
    )


    accounts = []


    for (
        user,
        assignment,
        restaurant,
    ) in rows:

        accounts.append(
            SimpleNamespace(
                user=user,
                assignment=assignment,
                restaurant=restaurant,
            )
        )


    return accounts


# =========================================================
# SINGLE MERCHANT ACCOUNT
# =========================================================

def get_admin_merchant_account(
    db: Session,
    merchant_id: int,
):

    merchant_id = (
        validate_positive_id(
            merchant_id,
            "Merchant ID",
        )
    )


    row = (
        db.query(
            User,
            MerchantRestaurant,
            Restaurant,
        )

        .outerjoin(
            MerchantRestaurant,
            MerchantRestaurant.user_id
            ==
            User.id,
        )

        .outerjoin(
            Restaurant,
            Restaurant.id
            ==
            MerchantRestaurant.restaurant_id,
        )

        .filter(
            User.id
            ==
            merchant_id,

            User.role
            ==
            MERCHANT_ROLE,
        )

        .first()
    )


    if row is None:

        return None


    user, assignment, restaurant = row


    return SimpleNamespace(
        user=user,
        assignment=assignment,
        restaurant=restaurant,
    )


# =========================================================
# SUMMARY
# =========================================================

def build_admin_merchant_summary(
    accounts,
):

    total = len(
        accounts
    )


    active = sum(
        1
        for account
        in accounts
        if account.user.is_active
    )


    inactive = (
        total
        -
        active
    )


    assigned = sum(
        1
        for account
        in accounts
        if account.assignment is not None
    )


    unassigned = (
        total
        -
        assigned
    )


    active_restaurants = sum(
        1
        for account
        in accounts
        if (
            account.restaurant is not None
            and
            account.restaurant.is_active
        )
    )


    return {
        "total":
            total,

        "active":
            active,

        "inactive":
            inactive,

        "assigned":
            assigned,

        "unassigned":
            unassigned,

        "active_restaurants":
            active_restaurants,
    }


# =========================================================
# AVAILABLE RESTAURANTS
# =========================================================

def get_available_restaurants_for_merchant(
    db: Session,
    merchant_id: int,
):

    merchant_id = (
        validate_positive_id(
            merchant_id,
            "Merchant ID",
        )
    )


    claimed_rows = (
        db.query(
            MerchantRestaurant.restaurant_id
        )

        .filter(
            MerchantRestaurant.user_id
            !=
            merchant_id
        )

        .all()
    )


    claimed_restaurant_ids = {
        row[0]
        for row
        in claimed_rows
    }


    query = (
        db.query(
            Restaurant
        )
    )


    if claimed_restaurant_ids:

        query = query.filter(
            Restaurant.id.notin_(
                claimed_restaurant_ids
            )
        )


    return (
        query

        .order_by(
            Restaurant.is_active.desc(),
            Restaurant.name.asc(),
        )

        .all()
    )


# =========================================================
# REASSIGN RESTAURANT
# =========================================================

def reassign_merchant_restaurant(
    db: Session,
    merchant_id: int,
    restaurant_id: int,
):

    merchant_id = (
        validate_positive_id(
            merchant_id,
            "Merchant ID",
        )
    )


    restaurant_id = (
        validate_positive_id(
            restaurant_id,
            "Restaurant ID",
        )
    )


    try:

        # =============================================
        # LOCK MERCHANT
        # =============================================

        merchant = (
            db.query(
                User
            )

            .filter(
                User.id
                ==
                merchant_id,

                User.role
                ==
                MERCHANT_ROLE,
            )

            .with_for_update()

            .first()
        )


        if merchant is None:

            raise ValueError(
                "Merchant account not found."
            )


        # =============================================
        # LOCK TARGET RESTAURANT
        # =============================================

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
                "Restaurant not found."
            )


        # =============================================
        # CHECK TARGET OWNERSHIP
        # =============================================

        existing_owner = (
            db.query(
                MerchantRestaurant
            )

            .filter(
                MerchantRestaurant.restaurant_id
                ==
                restaurant_id,

                MerchantRestaurant.user_id
                !=
                merchant_id,
            )

            .with_for_update()

            .first()
        )


        if existing_owner is not None:

            raise ValueError(
                "This restaurant is already assigned "
                "to another Merchant."
            )


        # =============================================
        # CURRENT ASSIGNMENT
        # =============================================

        assignment = (
            db.query(
                MerchantRestaurant
            )

            .filter(
                MerchantRestaurant.user_id
                ==
                merchant_id
            )

            .with_for_update()

            .first()
        )


        # =============================================
        # SAME RESTAURANT
        # =============================================

        if (
            assignment is not None
            and
            assignment.restaurant_id
            ==
            restaurant_id
        ):

            return assignment


        # =============================================
        # UPDATE EXISTING ASSIGNMENT
        # =============================================

        if assignment is not None:

            assignment.restaurant_id = (
                restaurant_id
            )


        # =============================================
        # CREATE MISSING ASSIGNMENT
        # =============================================

        else:

            assignment = MerchantRestaurant(

                user_id=(
                    merchant_id
                ),

                restaurant_id=(
                    restaurant_id
                ),
            )


            db.add(
                assignment
            )


        db.commit()


        db.refresh(
            assignment
        )


        return assignment


    except ValueError:

        db.rollback()

        raise


    except Exception:

        db.rollback()

        raise

# =========================================================
# UPDATE MERCHANT ACCOUNT
# =========================================================

def update_admin_merchant_account(
    db: Session,
    merchant_id: int,
    *,
    username: str,
    email: str,
):
    merchant_id = (
        validate_positive_id(
            merchant_id,
            "Merchant ID",
        )
    )


    merchant = (
        db.query(
            User
        )

        .filter(
            User.id
            ==
            merchant_id,

            User.role
            ==
            MERCHANT_ROLE,
        )

        .first()
    )


    if merchant is None:

        raise ValueError(
            "Merchant account not found."
        )


    return update_user(
        db=db,

        user=merchant,

        username=username,

        email=email,

        role=MERCHANT_ROLE,

        new_password=None,
    )

# =========================================================
# ENABLE / DISABLE MERCHANT
# =========================================================

def set_admin_merchant_active_state(
    db: Session,
    merchant_id: int,
    is_active: bool,
):

    merchant_id = (
        validate_positive_id(
            merchant_id,
            "Merchant ID",
        )
    )


    merchant = (
        db.query(
            User
        )

        .filter(
            User.id
            ==
            merchant_id,

            User.role
            ==
            MERCHANT_ROLE,
        )

        .first()
    )


    if merchant is None:

        return None


    return set_user_active_status(
        db=db,
        user=merchant,
        is_active=bool(
            is_active
        ),
    )