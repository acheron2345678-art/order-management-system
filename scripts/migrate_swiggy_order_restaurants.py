from pathlib import Path
import sys

from sqlalchemy import (
    inspect,
    text,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.database import engine


def run_migration():

    inspector = inspect(
        engine
    )

    tables = set(
        inspector.get_table_names()
    )

    required_tables = {
        "swiggy_orders",
        "order_items",
        "products",
        "restaurants",
    }

    missing = (
        required_tables
        -
        tables
    )

    if missing:

        raise RuntimeError(
            "Missing required tables: "
            +
            ", ".join(
                sorted(
                    missing
                )
            )
        )


    # =========================================
    # ADD RESTAURANT ID COLUMN
    # =========================================

    columns = {
        column["name"]
        for column
        in inspector.get_columns(
            "swiggy_orders"
        )
    }

    if "restaurant_id" not in columns:

        with engine.begin() as connection:

            connection.execute(
                text(
                    """
                    ALTER TABLE swiggy_orders
                    ADD COLUMN restaurant_id INT NULL
                    """
                )
            )

        print(
            "Added swiggy_orders.restaurant_id"
        )

    else:

        print(
            "swiggy_orders.restaurant_id already exists"
        )


    # =========================================
    # BACKFILL EXISTING ORDERS
    # =========================================

    with engine.begin() as connection:

        result = connection.execute(
            text(
                """
                UPDATE swiggy_orders AS sw

                JOIN (
                    SELECT
                        oi.order_id,
                        MIN(p.restaurant_id) AS restaurant_id

                    FROM order_items AS oi

                    JOIN products AS p
                        ON p.id = oi.product_id

                    WHERE
                        oi.platform = 'swiggy'
                        AND p.restaurant_id IS NOT NULL

                    GROUP BY oi.order_id

                    HAVING
                        COUNT(
                            DISTINCT p.restaurant_id
                        ) = 1
                ) AS resolved

                    ON resolved.order_id = sw.id

                SET
                    sw.restaurant_id =
                        resolved.restaurant_id

                WHERE
                    sw.restaurant_id IS NULL
                """
            )
        )

        print(
            "Legacy restaurant backfill completed."
        )

        print(
            f"Rows affected: {result.rowcount}"
        )


    # =========================================
    # INDEX
    # =========================================

    inspector = inspect(
        engine
    )

    indexes = {
        index["name"]
        for index
        in inspector.get_indexes(
            "swiggy_orders"
        )
    }

    if (
        "ix_swiggy_orders_restaurant_id"
        not in indexes
    ):

        with engine.begin() as connection:

            connection.execute(
                text(
                    """
                    CREATE INDEX
                    ix_swiggy_orders_restaurant_id

                    ON swiggy_orders (
                        restaurant_id
                    )
                    """
                )
            )

        print(
            "Added restaurant_id index."
        )


    # =========================================
    # FOREIGN KEY
    # =========================================

    inspector = inspect(
        engine
    )

    foreign_keys = (
        inspector.get_foreign_keys(
            "swiggy_orders"
        )
    )

    restaurant_fk_exists = any(

        "restaurant_id"
        in (
            foreign_key.get(
                "constrained_columns"
            )
            or
            []
        )

        for foreign_key
        in foreign_keys
    )

    if not restaurant_fk_exists:

        with engine.begin() as connection:

            connection.execute(
                text(
                    """
                    ALTER TABLE swiggy_orders

                    ADD CONSTRAINT
                    fk_swiggy_orders_restaurant_id

                    FOREIGN KEY (
                        restaurant_id
                    )

                    REFERENCES restaurants(id)

                    ON DELETE RESTRICT
                    """
                )
            )

        print(
            "Added restaurant foreign key."
        )


    print()

    print(
        "Swiggy restaurant-order migration completed."
    )


if __name__ == "__main__":

    run_migration()