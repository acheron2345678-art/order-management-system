from pathlib import Path
import sys


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from sqlalchemy import inspect

from app.database import engine
from app.merchants.models import MerchantRestaurant


REQUIRED_TABLES = {
    "users",
    "restaurants",
}


def validate_prerequisites():
    inspector = inspect(
        engine
    )

    existing_tables = set(
        inspector.get_table_names()
    )

    missing_tables = (
        REQUIRED_TABLES
        -
        existing_tables
    )

    if missing_tables:

        missing = ", ".join(
            sorted(
                missing_tables
            )
        )

        raise RuntimeError(
            "Merchant account migration cannot run because "
            f"these required tables are missing: {missing}. "
            "Run the earlier database migrations first."
        )


def verify_constraints():
    inspector = inspect(
        engine
    )

    constraints = {
        constraint.get("name")
        for constraint
        in inspector.get_unique_constraints(
            "merchant_restaurants"
        )
        if constraint.get("name")
    }

    expected_constraints = {
        "uq_merchant_restaurants_user_id",
        "uq_merchant_restaurants_restaurant_id",
    }

    missing_constraints = (
        expected_constraints
        -
        constraints
    )

    if missing_constraints:

        missing = ", ".join(
            sorted(
                missing_constraints
            )
        )

        raise RuntimeError(
            "Merchant account table was created but required "
            f"unique constraints are missing: {missing}."
        )


def run_migration():
    validate_prerequisites()

    print(
        "Creating merchant restaurant ownership table "
        "if needed..."
    )

    MerchantRestaurant.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    verify_constraints()

    print(
        "Merchant account migration completed successfully."
    )

    print(
        "Each merchant user can own only one restaurant, "
        "and each restaurant can have only one merchant login."
    )

    print(
        "No merchant accounts were created automatically."
    )


if __name__ == "__main__":
    run_migration()