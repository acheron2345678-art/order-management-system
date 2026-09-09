from datetime import date

from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from sqlalchemy import or_

from sqlalchemy.orm import Session

from app.orders.models import (
    InsightsOrders,
)

from app.orders.order_item_service import (
    create_order_item,
)

from app.orders.validation import (
    clean_optional_text,
    clean_required_text,
    validate_not_in_past,
)

from app.products.models import (
    Product,
)

from app.products.service import (
    generate_order_number,
)


PLATFORM = "insights"


MONEY_PLACES = Decimal(
    "0.01"
)


def normalize_money(
    value,
):
    return Decimal(
        str(value)
    ).quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def get_insights_services(
    db: Session,
    limit: int | None = None,
    search_query: str = "",
):
    query = (
        db.query(
            Product
        )
        .filter(
            Product.is_active == True,

            Product.platform.ilike(
                PLATFORM
            ),
        )
    )

    search_query = (
        search_query.strip()
    )

    if search_query:
        pattern = (
            f"%{search_query}%"
        )

        query = query.filter(
            or_(
                Product.product_name.ilike(
                    pattern
                ),

                Product.description.ilike(
                    pattern
                ),
            )
        )

    query = query.order_by(
        Product.id.asc()
    )

    if limit is not None:
        query = query.limit(
            limit
        )

    return query.all()


def get_insights_service(
    db: Session,
    product_id: int,
    active_only: bool = True,
):
    query = (
        db.query(
            Product
        )
        .filter(
            Product.id
            ==
            product_id,

            Product.platform.ilike(
                PLATFORM
            ),
        )
    )

    if active_only:
        query = query.filter(
            Product.is_active
            ==
            True
        )

    return query.first()


def validate_project_form_fields(
    customer_name: str,
    project_brief: str,
    business_goal: str,
    preferred_completion_date: date | None,
    additional_notes: str | None,
):
    cleaned_customer_name = (
        clean_required_text(
            customer_name,
            "Client or company name",
            max_length=100,
        )
    )

    cleaned_project_brief = (
        clean_required_text(
            project_brief,
            "Project brief",
            min_length=20,
            max_length=3000,
        )
    )

    cleaned_business_goal = (
        clean_required_text(
            business_goal,
            "Business goal",
            min_length=10,
            max_length=2000,
        )
    )

    cleaned_additional_notes = (
        clean_optional_text(
            additional_notes,
            "Additional notes",
            max_length=2000,
        )
    )

    validated_completion_date = (
        validate_not_in_past(
            preferred_completion_date,
            "Preferred completion date",
        )
    )

    return (
        cleaned_customer_name,
        cleaned_project_brief,
        cleaned_business_goal,
        validated_completion_date,
        cleaned_additional_notes,
    )


def create_insights_project(
    db: Session,

    service_id: int,

    customer_name: str,

    order_date: date,

    client_id: int,

    project_brief: str,

    business_goal: str,

    preferred_completion_date: (
        date | None
    ) = None,

    additional_notes: (
        str | None
    ) = None,
):
    (
        customer_name,
        project_brief,
        business_goal,
        preferred_completion_date,
        additional_notes,
    ) = validate_project_form_fields(
        customer_name=(
            customer_name
        ),

        project_brief=(
            project_brief
        ),

        business_goal=(
            business_goal
        ),

        preferred_completion_date=(
            preferred_completion_date
        ),

        additional_notes=(
            additional_notes
        ),
    )

    try:
        service = (
            db.query(
                Product
            )
            .filter(
                Product.id
                ==
                service_id,

                Product.platform.ilike(
                    PLATFORM
                ),
            )
            .first()
        )

        if service is None:
            raise ValueError(
                "Insights service "
                "was not found."
            )

        if not service.is_active:
            raise ValueError(
                "This Insights service "
                "is currently unavailable."
            )

        service_price = (
            normalize_money(
                service.price
            )
        )

        order_number = (
            generate_order_number(
                db=db,
                platform=PLATFORM,
            )
        )

        project = InsightsOrders(
            customer_name=(
                customer_name
            ),

            order_number=(
                order_number
            ),

            product_id=(
                service.id
            ),

            product_name=(
                service.product_name
            ),

            amount=(
                float(
                    service_price
                )
            ),

            status="pending",

            order_date=(
                order_date
            ),

            client_id=(
                client_id
            ),

            project_brief=(
                project_brief
            ),

            business_goal=(
                business_goal
            ),

            preferred_completion_date=(
                preferred_completion_date
            ),

            additional_notes=(
                additional_notes
            ),
        )

        db.add(
            project
        )

        db.flush()

        create_order_item(
            db=db,

            platform=PLATFORM,

            order_id=(
                project.id
            ),

            product_id=(
                service.id
            ),

            product_name=(
                service.product_name
            ),

            unit_price=(
                service_price
            ),

            quantity=1,
        )

        db.commit()

        db.refresh(
            project
        )

        return project

    except ValueError:
        db.rollback()

        raise

    except Exception:
        db.rollback()

        raise


def get_client_insights_projects(
    db: Session,
    client_id: int,
):
    return (
        db.query(
            InsightsOrders
        )
        .filter(
            InsightsOrders.client_id
            ==
            client_id
        )
        .order_by(
            InsightsOrders.id.desc()
        )
        .all()
    )


def get_client_insights_project(
    db: Session,
    client_id: int,
    order_id: int,
):
    return (
        db.query(
            InsightsOrders
        )
        .filter(
            InsightsOrders.id
            ==
            order_id,

            InsightsOrders.client_id
            ==
            client_id,
        )
        .first()
    )