from collections import Counter
from pathlib import Path
import ast
import sys

from sqlalchemy import inspect as sqlalchemy_inspect


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


project_root_string = str(
    PROJECT_ROOT
)


if project_root_string in sys.path:

    sys.path.remove(
        project_root_string
    )


sys.path.insert(
    0,
    project_root_string,
)


# =========================================================
# APPLICATION IMPORTS
# =========================================================

import app.main as main_module

from app.main import app

from app.database import (
    engine,
    get_db,
)

from app.merchants.models import (
    MerchantRestaurant,
)

from app.orders.models import (
    OrderItem,
    SwiggyOrders,
)

from app.products.models import (
    Product,
    Restaurant,
)

from app.users.models import (
    User,
)


# =========================================================
# AUDIT TRACKER
# =========================================================

class Audit:

    def __init__(self):

        self.passes = []
        self.warnings = []
        self.failures = []


    def pass_check(
        self,
        message: str,
    ):

        self.passes.append(
            message
        )

        print(
            f"[PASS] {message}"
        )


    def warn_check(
        self,
        message: str,
    ):

        self.warnings.append(
            message
        )

        print(
            f"[WARN] {message}"
        )


    def fail_check(
        self,
        message: str,
    ):

        self.failures.append(
            message
        )

        print(
            f"[FAIL] {message}"
        )


# =========================================================
# APPLICATION IMPORT AUDIT
# =========================================================

def audit_import_location(
    audit: Audit,
):

    print()

    print(
        "=== APPLICATION IMPORT AUDIT ==="
    )


    imported_main = (
        Path(
            main_module.__file__
        )
        .resolve()
    )


    expected_main = (
        PROJECT_ROOT
        /
        "app"
        /
        "main.py"
    ).resolve()


    print(
        "Imported app.main:"
    )

    print(
        f"  {imported_main}"
    )


    if imported_main == expected_main:

        audit.pass_check(
            "Audit imported app.main "
            "from the current project."
        )

    else:

        audit.fail_check(
            "Audit imported app.main "
            "from the wrong project."
        )


# =========================================================
# OPENAPI ROUTE CHECK
# =========================================================

def check_route(
    audit: Audit,
    paths: dict,
    route_path: str,
    methods: set[str],
):

    operation = paths.get(
        route_path
    )


    if operation is None:

        audit.fail_check(
            f"Missing route: {route_path}"
        )

        return


    available_methods = {

        method.lower()

        for method
        in operation.keys()

        if method.lower()
        in {
            "get",
            "post",
            "put",
            "patch",
            "delete",
        }
    }


    expected_methods = {

        method.lower()

        for method
        in methods
    }


    missing_methods = (
        expected_methods
        -
        available_methods
    )


    if missing_methods:

        audit.fail_check(
            f"{route_path} missing method(s): "
            +
            ", ".join(
                sorted(
                    missing_methods
                )
            )
        )

        return


    audit.pass_check(
        "Route registered: "
        +
        ", ".join(
            sorted(
                method.upper()
                for method
                in methods
            )
        )
        +
        f" {route_path}"
    )


# =========================================================
# MAIN.PY ROUTER REGISTRATION AUDIT
# =========================================================

def get_name_identifiers(
    node,
):

    return {

        child.id

        for child
        in ast.walk(
            node
        )

        if isinstance(
            child,
            ast.Name,
        )
    }


def audit_router_registration_source(
    audit: Audit,
):

    print()

    print(
        "=== ROUTER REGISTRATION AUDIT ==="
    )


    main_path = (
        PROJECT_ROOT
        /
        "app"
        /
        "main.py"
    )


    try:

        source = main_path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

    except Exception as error:

        audit.fail_check(
            "Could not parse app/main.py: "
            f"{error}"
        )

        return


    registrations = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call,
        ):

            continue


        function = node.func


        if not (
            isinstance(
                function,
                ast.Attribute,
            )
            and
            function.attr
            ==
            "include_router"
        ):

            continue


        if not node.args:

            continue


        router_argument = (
            node.args[0]
        )


        if isinstance(
            router_argument,
            ast.Name,
        ):

            router_name = (
                router_argument.id
            )

        else:

            router_name = (
                ast.unparse(
                    router_argument
                )
            )


        dependency_names = set()


        for keyword in node.keywords:

            if (
                keyword.arg
                ==
                "dependencies"
            ):

                dependency_names.update(
                    get_name_identifiers(
                        keyword.value
                    )
                )


        registrations.append(
            {
                "router":
                    router_name,

                "line":
                    node.lineno,

                "dependencies":
                    dependency_names,
            }
        )


    registrations.sort(
        key=lambda item:
            item[
                "line"
            ]
    )


    registration_map = {

        item[
            "router"
        ]:
            item

        for item
        in registrations
    }


    # =====================================================
    # MERCHANT ORDER ROUTE ORDER
    # =====================================================

    merchant_registration = (
        registration_map.get(
            "merchant_order_router"
        )
    )


    generic_order_registration = (
        registration_map.get(
            "orders_router"
        )
    )


    if merchant_registration is None:

        audit.fail_check(
            "merchant_order_router is not "
            "included in app/main.py."
        )


    elif generic_order_registration is None:

        audit.fail_check(
            "orders_router is not "
            "included in app/main.py."
        )


    elif (
        merchant_registration[
            "line"
        ]
        <
        generic_order_registration[
            "line"
        ]
    ):

        audit.pass_check(
            "merchant_order_router is registered "
            "before orders_router."
        )


        print(
            "  merchant_order_router:"
            f" line {merchant_registration['line']}"
        )


        print(
            "  orders_router:"
            f" line {generic_order_registration['line']}"
        )


    else:

        audit.fail_check(
            "merchant_order_router is registered "
            "after orders_router. "
            "/merchant/orders may be shadowed."
        )


    # =====================================================
    # SWIGGY ROUTER REGISTRATION
    # =====================================================

    swiggy_registration = (
        registration_map.get(
            "swiggy_storefront_router"
        )
    )


    if swiggy_registration is None:

        audit.fail_check(
            "swiggy_storefront_router is not "
            "included in app/main.py."
        )


    else:

        audit.pass_check(
            "swiggy_storefront_router is "
            "registered in app/main.py."
        )


        print(
            "  swiggy_storefront_router:"
            f" line {swiggy_registration['line']}"
        )


        if (
            "enforce_merchant_swiggy_scope"
            in
            swiggy_registration[
                "dependencies"
            ]
        ):

            audit.pass_check(
                "Swiggy router is protected by "
                "enforce_merchant_swiggy_scope."
            )

        else:

            audit.fail_check(
                "Swiggy router is missing "
                "enforce_merchant_swiggy_scope."
            )


# =========================================================
# OPENAPI ROUTE AUDIT
# =========================================================

def audit_routes(
    audit: Audit,
):

    print()

    print(
        "=== ROUTE AUDIT ==="
    )


    schema = app.openapi()


    paths = schema.get(
        "paths",
        {},
    )


    print(
        f"FastAPI routes discovered: "
        f"{len(paths)}"
    )


    required_routes = {

        "/register/client": {
            "get",
            "post",
        },

        "/register/merchant": {
            "get",
            "post",
        },

        "/merchant": {
            "get",
        },

        "/merchant/profile": {
            "get",
            "post",
        },

        "/merchant/profile/status": {
            "post",
        },

        "/merchant/menu": {
            "get",
        },

        "/merchant/menu/add": {
            "get",
            "post",
        },

        "/merchant/menu/{product_id}/edit": {
            "get",
            "post",
        },

        "/merchant/menu/{product_id}/status": {
            "post",
        },

        "/merchant/inventory": {
            "get",
        },

        "/merchant/inventory/bulk-restock": {
            "post",
        },

        "/merchant/inventory/{product_id}/restock": {
            "post",
        },

        "/merchant/inventory/{product_id}/adjust": {
            "post",
        },

        "/merchant/orders": {
            "get",
        },

        "/merchant/orders/{order_id}": {
            "get",
        },

        "/merchant/orders/{order_id}/status": {
            "post",
        },

        "/admin/merchants": {
            "get",
        },

        "/admin/merchants/{merchant_id}/edit": {
            "get",
        },

        "/admin/merchants/{merchant_id}/reassign": {
            "post",
        },

        "/admin/merchants/{merchant_id}/status": {
            "post",
        },

        "/swiggy/restaurants/{restaurant_id}": {
            "get",
        },
    }


    for (
        route_path,
        methods,
    ) in required_routes.items():

        check_route(
            audit=(
                audit
            ),

            paths=(
                paths
            ),

            route_path=(
                route_path
            ),

            methods=(
                methods
            ),
        )


    swiggy_paths = [

        path

        for path
        in paths

        if path.startswith(
            "/swiggy"
        )
    ]


    if swiggy_paths:

        audit.pass_check(
            f"OpenAPI contains "
            f"{len(swiggy_paths)} "
            "Swiggy route(s)."
        )

    else:

        audit.fail_check(
            "OpenAPI contains no "
            "Swiggy routes."
        )


# =========================================================
# DATABASE SCHEMA AUDIT
# =========================================================

def audit_database_schema(
    audit: Audit,
):

    print()

    print(
        "=== DATABASE SCHEMA AUDIT ==="
    )


    inspector = (
        sqlalchemy_inspect(
            engine
        )
    )


    tables = set(
        inspector.get_table_names()
    )


    required_tables = {

        "users",

        "restaurants",

        "merchant_restaurants",

        "products",

        "swiggy_orders",

        "order_items",
    }


    missing_tables = (
        required_tables
        -
        tables
    )


    if missing_tables:

        audit.fail_check(
            "Missing required table(s): "
            +
            ", ".join(
                sorted(
                    missing_tables
                )
            )
        )

        return


    audit.pass_check(
        "All Phase 11 database "
        "tables exist."
    )


    # =====================================================
    # ASSIGNMENT COLUMNS
    # =====================================================

    assignment_columns = {

        column[
            "name"
        ]

        for column
        in inspector.get_columns(
            "merchant_restaurants"
        )
    }


    for column_name in (
        "user_id",
        "restaurant_id",
    ):

        if (
            column_name
            in
            assignment_columns
        ):

            audit.pass_check(
                "merchant_restaurants."
                f"{column_name} exists."
            )

        else:

            audit.fail_check(
                "merchant_restaurants."
                f"{column_name} is missing."
            )


    # =====================================================
    # UNIQUE CONSTRAINTS
    # =====================================================

    unique_sets = set()


    for constraint in (
        inspector.get_unique_constraints(
            "merchant_restaurants"
        )
    ):

        columns = (
            constraint.get(
                "column_names"
            )
            or
            []
        )


        if columns:

            unique_sets.add(
                frozenset(
                    columns
                )
            )


    for index in (
        inspector.get_indexes(
            "merchant_restaurants"
        )
    ):

        if not index.get(
            "unique"
        ):

            continue


        columns = (
            index.get(
                "column_names"
            )
            or
            []
        )


        if columns:

            unique_sets.add(
                frozenset(
                    columns
                )
            )


    if (
        frozenset(
            {
                "user_id"
            }
        )
        in
        unique_sets
    ):

        audit.pass_check(
            "Database enforces one restaurant "
            "assignment per Merchant."
        )

    else:

        audit.fail_check(
            "Missing UNIQUE constraint on "
            "merchant_restaurants.user_id."
        )


    if (
        frozenset(
            {
                "restaurant_id"
            }
        )
        in
        unique_sets
    ):

        audit.pass_check(
            "Database enforces one Merchant "
            "per restaurant."
        )

    else:

        audit.fail_check(
            "Missing UNIQUE constraint on "
            "merchant_restaurants.restaurant_id."
        )


    # =====================================================
    # SWIGGY ORDER COLUMN
    # =====================================================

    swiggy_columns = {

        column[
            "name"
        ]

        for column
        in inspector.get_columns(
            "swiggy_orders"
        )
    }


    if (
        "restaurant_id"
        in
        swiggy_columns
    ):

        audit.pass_check(
            "swiggy_orders.restaurant_id exists."
        )

    else:

        audit.fail_check(
            "swiggy_orders.restaurant_id "
            "is missing."
        )


    # =====================================================
    # RESTAURANT FOREIGN KEY
    # =====================================================

    restaurant_fk_found = False


    for foreign_key in (
        inspector.get_foreign_keys(
            "swiggy_orders"
        )
    ):

        constrained_columns = (
            foreign_key.get(
                "constrained_columns"
            )
            or
            []
        )


        referred_table = (
            foreign_key.get(
                "referred_table"
            )
        )


        referred_columns = (
            foreign_key.get(
                "referred_columns"
            )
            or
            []
        )


        if (
            "restaurant_id"
            in
            constrained_columns
            and
            referred_table
            ==
            "restaurants"
            and
            "id"
            in
            referred_columns
        ):

            restaurant_fk_found = True

            break


    if restaurant_fk_found:

        audit.pass_check(
            "swiggy_orders.restaurant_id "
            "references restaurants.id."
        )

    else:

        audit.fail_check(
            "Missing restaurant foreign key "
            "on swiggy_orders."
        )


# =========================================================
# DATABASE OWNERSHIP AUDIT
# =========================================================

def audit_database_ownership(
    audit: Audit,
):

    print()

    print(
        "=== DATABASE OWNERSHIP AUDIT ==="
    )


    db_generator = (
        get_db()
    )


    db = next(
        db_generator
    )


    try:

        merchants = (

            db.query(
                User
            )

            .filter(
                User.role
                ==
                "merchant"
            )

            .order_by(
                User.id.asc()
            )

            .all()
        )


        assignments = (

            db.query(
                MerchantRestaurant
            )

            .order_by(
                MerchantRestaurant.id.asc()
            )

            .all()
        )


        restaurants = {

            restaurant.id:
                restaurant

            for restaurant
            in (
                db.query(
                    Restaurant
                )
                .all()
            )
        }


        merchant_ids = {

            merchant.id

            for merchant
            in merchants
        }


        assignments_by_user = Counter(

            assignment.user_id

            for assignment
            in assignments
        )


        assignments_by_restaurant = Counter(

            assignment.restaurant_id

            for assignment
            in assignments
        )


        # =================================================
        # ONE RESTAURANT PER MERCHANT
        # =================================================

        duplicate_users = [

            user_id

            for (
                user_id,
                count,
            )
            in assignments_by_user.items()

            if count > 1
        ]


        if duplicate_users:

            audit.fail_check(
                "Merchants with multiple "
                "assignments: "
                +
                ", ".join(
                    map(
                        str,
                        duplicate_users,
                    )
                )
            )

        else:

            audit.pass_check(
                "No Merchant has more than one "
                "restaurant assignment."
            )


        # =================================================
        # ONE MERCHANT PER RESTAURANT
        # =================================================

        duplicate_restaurants = [

            restaurant_id

            for (
                restaurant_id,
                count,
            )
            in assignments_by_restaurant.items()

            if count > 1
        ]


        if duplicate_restaurants:

            audit.fail_check(
                "Restaurants assigned to "
                "multiple Merchants: "
                +
                ", ".join(
                    map(
                        str,
                        duplicate_restaurants,
                    )
                )
            )

        else:

            audit.pass_check(
                "No restaurant is assigned to "
                "more than one Merchant."
            )


        # =================================================
        # EVERY MERCHANT ASSIGNED
        # =================================================

        unassigned_merchants = [

            merchant.id

            for merchant
            in merchants

            if (
                assignments_by_user[
                    merchant.id
                ]
                !=
                1
            )
        ]


        if unassigned_merchants:

            audit.fail_check(
                "Merchant accounts without "
                "exactly one assignment: "
                +
                ", ".join(
                    map(
                        str,
                        unassigned_merchants,
                    )
                )
            )

        else:

            audit.pass_check(
                "Every Merchant account has exactly "
                "one restaurant assignment."
            )


        # =================================================
        # ASSIGNMENTS BELONG TO MERCHANT USERS
        # =================================================

        invalid_assignment_users = [

            assignment.user_id

            for assignment
            in assignments

            if (
                assignment.user_id
                not in
                merchant_ids
            )
        ]


        if invalid_assignment_users:

            audit.fail_check(
                "MerchantRestaurant rows linked "
                "to non-Merchant users: "
                +
                ", ".join(
                    map(
                        str,
                        sorted(
                            set(
                                invalid_assignment_users
                            )
                        ),
                    )
                )
            )

        else:

            audit.pass_check(
                "Every MerchantRestaurant row "
                "belongs to a Merchant user."
            )


        # =================================================
        # ASSIGNED RESTAURANTS EXIST
        # =================================================

        invalid_assignments = [

            assignment.id

            for assignment
            in assignments

            if (
                assignment.restaurant_id
                not in
                restaurants
            )
        ]


        if invalid_assignments:

            audit.fail_check(
                "Assignments reference missing "
                "restaurants: "
                +
                ", ".join(
                    map(
                        str,
                        invalid_assignments,
                    )
                )
            )

        else:

            audit.pass_check(
                "Every Merchant assignment references "
                "an existing restaurant."
            )


        # =================================================
        # SWIGGY ORDERS
        # =================================================

        swiggy_orders = (

            db.query(
                SwiggyOrders
            )

            .order_by(
                SwiggyOrders.id.asc()
            )

            .all()
        )


        non_null_orders = [

            order

            for order
            in swiggy_orders

            if order.restaurant_id
            is not None
        ]


        null_orders = [

            order

            for order
            in swiggy_orders

            if order.restaurant_id
            is None
        ]


        invalid_order_restaurants = [

            order.id

            for order
            in non_null_orders

            if (
                order.restaurant_id
                not in
                restaurants
            )
        ]


        if invalid_order_restaurants:

            audit.fail_check(
                "Swiggy orders reference missing "
                "restaurants. Order IDs: "
                +
                ", ".join(
                    map(
                        str,
                        invalid_order_restaurants,
                    )
                )
            )

        else:

            audit.pass_check(
                "Every non-null Swiggy order "
                "restaurant_id references an "
                "existing restaurant."
            )


        # =================================================
        # LEGACY NULL ORDERS
        # =================================================

        unresolved_null_orders = []


        for order in null_orders:

            restaurant_rows = (

                db.query(
                    Product.restaurant_id
                )

                .join(
                    OrderItem,
                    OrderItem.product_id
                    ==
                    Product.id,
                )

                .filter(
                    OrderItem.platform
                    ==
                    "swiggy",

                    OrderItem.order_id
                    ==
                    order.id,

                    Product.restaurant_id.isnot(
                        None
                    ),
                )

                .distinct()

                .all()
            )


            restaurant_ids = {

                row[0]

                for row
                in restaurant_rows

                if row[0]
                is not None
            }


            if len(
                restaurant_ids
            ) != 1:

                unresolved_null_orders.append(
                    order.id
                )


        if unresolved_null_orders:

            audit.warn_check(
                f"{len(unresolved_null_orders)} "
                "legacy Swiggy order(s) still have "
                "restaurant_id=NULL and cannot be "
                "reliably reconstructed. "
                "This is acceptable for pre-11I orders."
            )


        # =================================================
        # LATEST ORDERS
        # =================================================

        latest_orders = (

            db.query(
                SwiggyOrders
            )

            .order_by(
                SwiggyOrders.id.desc()
            )

            .limit(
                5
            )

            .all()
        )


        print()

        print(
            "Latest Swiggy orders:"
        )


        latest_missing_restaurant = False


        for order in latest_orders:

            print(
                "  "
                f"ID={order.id}, "
                f"number={order.order_number}, "
                f"restaurant_id={order.restaurant_id}, "
                f"status={order.status}"
            )


            if (
                order.restaurant_id
                is None
            ):

                latest_missing_restaurant = True


        if (
            latest_orders
            and
            not latest_missing_restaurant
        ):

            audit.pass_check(
                "Latest five Swiggy orders all "
                "have restaurant ownership."
            )

        elif latest_missing_restaurant:

            audit.fail_check(
                "At least one of the latest five "
                "Swiggy orders has restaurant_id=NULL."
            )


        print()

        print(
            "Merchant accounts:",
            len(
                merchants
            ),
        )


        print(
            "Restaurant assignments:",
            len(
                assignments
            ),
        )


        print(
            "Owned restaurants:",
            len(
                assignments_by_restaurant
            ),
        )


        print(
            "Swiggy orders:",
            len(
                swiggy_orders
            ),
        )


        print(
            "Legacy unresolved orders:",
            len(
                unresolved_null_orders
            ),
        )


    finally:

        db.close()


        try:

            next(
                db_generator
            )

        except StopIteration:

            pass


# =========================================================
# RESULT
# =========================================================

def print_result(
    audit: Audit,
):

    print()

    print(
        "=== RESULT ==="
    )


    print(
        f"PASS: {len(audit.passes)}"
    )


    print(
        f"WARN: {len(audit.warnings)}"
    )


    print(
        f"FAIL: {len(audit.failures)}"
    )


    if audit.failures:

        print()

        print(
            "Phase 11 automated audit FAILED."
        )

        return 1


    print()

    print(
        "Phase 11 automated audit PASSED."
    )


    if audit.warnings:

        print()

        print(
            "Warnings are legacy-data or "
            "informational findings."
        )


    return 0


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "Phase 11 Merchant Security Audit"
    )


    print(
        "================================"
    )


    print(
        f"Project: {PROJECT_ROOT}"
    )


    audit = Audit()


    audit_import_location(
        audit
    )


    audit_routes(
        audit
    )


    audit_router_registration_source(
        audit
    )


    audit_database_schema(
        audit
    )


    audit_database_ownership(
        audit
    )


    sys.exit(
        print_result(
            audit
        )
    )


if __name__ == "__main__":

    main()