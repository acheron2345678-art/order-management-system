from datetime import (
    date,
    datetime,
)

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_client,
)

from app.core import templates

from app.database import (
    get_db,
)

from app.insights.service import (
    create_insights_project,
    get_client_insights_project,
    get_client_insights_projects,
    get_insights_service,
    get_insights_services,
)

from app.notifications.order_email_service import (
    send_admin_new_order_notification,
    send_client_order_confirmation,
)

from app.orders.history_service import (
    record_order_created,
)

from app.orders.order_item_service import (
    get_order_items,
)

from app.users.models import (
    User,
)

from app.users.profile_service import (
    get_client_profile,
)


router = APIRouter(
    prefix="/insights",
    tags=[
        "Insights Storefront"
    ],
)


# =========================================================
# INSIGHTS HOME
# =========================================================

@router.get(
    "",
    response_class=HTMLResponse,
)
def insights_home(
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User | None = Depends(
        get_current_user
    ),
):
    featured_services = (
        get_insights_services(
            db=db,
            limit=4,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="insights/home.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "featured_services":
                featured_services,
        },
    )


# =========================================================
# SERVICES
# =========================================================

@router.get(
    "/services",
    response_class=HTMLResponse,
)
def insights_services_page(
    request: Request,
    q: str = Query(
        default=""
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User | None = Depends(
        get_current_user
    ),
):
    search_query = (
        q.strip()
    )

    services = (
        get_insights_services(
            db=db,
            search_query=search_query,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="insights/services.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "services":
                services,

            "search_query":
                search_query,
        },
    )


# =========================================================
# SERVICE DETAIL
# =========================================================

@router.get(
    "/services/{product_id}",
    response_class=HTMLResponse,
)
def insights_service_detail(
    request: Request,
    product_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User | None = Depends(
        get_current_user
    ),
):
    service = (
        get_insights_service(
            db=db,
            product_id=product_id,
        )
    )

    if service is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Insights service not found"
            ),
        )

    return templates.TemplateResponse(
        request=request,
        name=(
            "insights/"
            "service_detail.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "service":
                service,
        },
    )


# =========================================================
# PROJECT REQUEST PAGE
# =========================================================

@router.get(
    "/checkout/{service_id}",
    response_class=HTMLResponse,
)
def insights_checkout_page(
    request: Request,
    service_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    service = (
        get_insights_service(
            db=db,
            product_id=service_id,
        )
    )


    if service is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Insights service not found"
            ),
        )


    # =====================================================
    # CLIENT PROFILE
    # =====================================================

    profile = (
        get_client_profile(
            db=db,
            user_id=current_user.id,
        )
    )


    # =====================================================
    # PREFILL CLIENT / COMPANY NAME
    # =====================================================

    if (
        profile
        and
        profile.company_name
    ):

        customer_name = (
            profile.company_name
        )


    elif (
        profile
        and
        profile.full_name
    ):

        customer_name = (
            profile.full_name
        )


    else:

        customer_name = (
            current_user.username
        )


    return templates.TemplateResponse(
        request=request,
        name="insights/checkout.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "service":
                service,

            "customer_name":
                customer_name,

            "project_brief":
                "",

            "business_goal":
                "",

            "preferred_completion_date":
                "",

            "additional_notes":
                "",

            "today":
                date.today().isoformat(),

            "error":
                None,
        },
    )


# =========================================================
# SUBMIT PROJECT REQUEST
# =========================================================

@router.post(
    "/checkout/{service_id}",
    response_class=HTMLResponse,
)
def insights_checkout_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    service_id: int,

    customer_name: str = Form(
        ...
    ),

    project_brief: str = Form(
        ...
    ),

    business_goal: str = Form(
        ...
    ),

    preferred_completion_date: str = Form(
        ""
    ),

    additional_notes: str = Form(
        ""
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    customer_name = (
        customer_name.strip()
    )

    project_brief = (
        project_brief.strip()
    )

    business_goal = (
        business_goal.strip()
    )

    preferred_completion_date = (
        preferred_completion_date.strip()
    )

    additional_notes = (
        additional_notes.strip()
    )


    service = (
        get_insights_service(
            db=db,
            product_id=service_id,
            active_only=False,
        )
    )


    if service is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Insights service not found"
            ),
        )


    # =====================================================
    # FORM ERROR HELPER
    # =====================================================

    def return_form_error(
        message: str,
    ):
        return templates.TemplateResponse(
            request=request,
            name="insights/checkout.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "service":
                    service,

                "customer_name":
                    customer_name,

                "project_brief":
                    project_brief,

                "business_goal":
                    business_goal,

                "preferred_completion_date":
                    preferred_completion_date,

                "additional_notes":
                    additional_notes,

                "today":
                    date.today().isoformat(),

                "error":
                    message,
            },
            status_code=400,
        )


    # =====================================================
    # VALIDATION
    # =====================================================

    if not customer_name:

        return return_form_error(
            "Client or company name "
            "is required."
        )

    if len(
        customer_name
    ) > 100:

        return return_form_error(
            "Client or company name "
            "cannot exceed 100 characters."
        )


    if not project_brief:

        return return_form_error(
            "Project brief is required."
        )


    if not business_goal:

        return return_form_error(
            "Business goal is required."
        )


    if len(
        project_brief
    ) < 20:

        return return_form_error(
            "Please provide a little "
            "more detail in the "
            "project brief."
        )


    if len(
        business_goal
    ) < 10:

        return return_form_error(
            "Please provide a clearer "
            "business goal."
        )


    if len(
        project_brief
    ) > 3000:

        return return_form_error(
            "Project brief cannot exceed "
            "3000 characters."
        )


    if len(
        business_goal
    ) > 2000:

        return return_form_error(
            "Business goal cannot exceed "
            "2000 characters."
        )


    if len(
        additional_notes
    ) > 2000:

        return return_form_error(
            "Additional notes cannot exceed "
            "2000 characters."
        )


    # =====================================================
    # PREFERRED COMPLETION DATE
    # =====================================================

    parsed_completion_date = None


    if preferred_completion_date:

        try:

            parsed_completion_date = (
                datetime.strptime(
                    preferred_completion_date,
                    "%Y-%m-%d",
                )
                .date()
            )


        except ValueError:

            return return_form_error(
                "Preferred completion date "
                "is invalid."
            )


        if (
            parsed_completion_date
            <
            date.today()
        ):

            return return_form_error(
                "Preferred completion date "
                "cannot be in the past."
            )


    # =====================================================
    # CREATE PROJECT
    # =====================================================

    try:

        project = (
            create_insights_project(
                db=db,

                service_id=(
                    service_id
                ),

                customer_name=(
                    customer_name
                ),

                order_date=(
                    date.today()
                ),

                client_id=(
                    current_user.id
                ),

                project_brief=(
                    project_brief
                ),

                business_goal=(
                    business_goal
                ),

                preferred_completion_date=(
                    parsed_completion_date
                ),

                additional_notes=(
                    additional_notes
                    or
                    None
                ),
            )
        )


    except ValueError as error:

        return return_form_error(
            str(error)
        )


    # =====================================================
    # ORDER / PROJECT HISTORY
    # =====================================================

    record_order_created(
        db=db,
        platform="insights",
        order_id=project.id,
        changed_by=current_user.id,
    )


    # =====================================================
    # ORDER ITEMS
    # =====================================================

    order_items = (
        get_order_items(
            db=db,
            platform="insights",
            order_id=project.id,
        )
    )


    # =====================================================
    # PREPARE EMAIL DATA
    # =====================================================

    email_items = []


    for item in order_items:

        email_items.append(
            {
                "product_name":
                    item.product_name,

                "quantity":
                    int(
                        item.quantity
                        or
                        1
                    ),

                "line_total":
                    float(
                        item.line_total
                        or
                        0
                    ),
            }
        )


    # =====================================================
    # CLIENT CONFIRMATION EMAIL
    # =====================================================

    background_tasks.add_task(
        send_client_order_confirmation,

        platform="insights",

        client_email=(
            current_user.email
        ),

        client_name=(
            current_user.username
        ),

        customer_name=(
            project.customer_name
        ),

        order_number=(
            project.order_number
        ),

        order_date=(
            project.order_date
        ),

        status=(
            project.status
        ),

        amount=(
            float(
                project.amount
            )
        ),

        items=(
            email_items
        ),
    )


    # =====================================================
    # ADMIN NEW PROJECT EMAIL
    # =====================================================

    background_tasks.add_task(
        send_admin_new_order_notification,

        platform="insights",

        client_email=(
            current_user.email
        ),

        client_name=(
            current_user.username
        ),

        customer_name=(
            project.customer_name
        ),

        order_number=(
            project.order_number
        ),

        order_date=(
            project.order_date
        ),

        status=(
            project.status
        ),

        amount=(
            float(
                project.amount
            )
        ),

        items=(
            email_items
        ),
    )


    # =====================================================
    # SUCCESS
    # =====================================================

    return RedirectResponse(
        url=(
            "/insights/"
            "order-success/"
            f"{project.id}"
        ),
        status_code=303,
    )


# =========================================================
# PROJECT SUCCESS PAGE
# =========================================================

@router.get(
    "/order-success/{order_id}",
    response_class=HTMLResponse,
)
def insights_order_success(
    request: Request,
    order_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_client
    ),
):
    project = (
        get_client_insights_project(
            db=db,
            client_id=current_user.id,
            order_id=order_id,
        )
    )


    if project is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Insights project not found"
            ),
        )


    order_items = (
        get_order_items(
            db=db,
            platform="insights",
            order_id=project.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name=(
            "insights/"
            "order_success.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "project":
                project,

            "order_items":
                order_items,
        },
    )


# =========================================================
# MY PROJECTS
# =========================================================

@router.get(
    "/my-projects",
    response_class=HTMLResponse,
)
def insights_my_projects(
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_client
    ),
):
    projects = (
        get_client_insights_projects(
            db=db,
            client_id=current_user.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name=(
            "insights/"
            "projects.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "projects":
                projects,
        },
    )


# =========================================================
# PROJECT DETAIL
# =========================================================

@router.get(
    "/my-projects/{order_id}",
    response_class=HTMLResponse,
)
def insights_project_detail(
    request: Request,
    order_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_client
    ),
):
    project = (
        get_client_insights_project(
            db=db,
            client_id=current_user.id,
            order_id=order_id,
        )
    )


    if project is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Insights project not found"
            ),
        )


    order_items = (
        get_order_items(
            db=db,
            platform="insights",
            order_id=project.id,
        )
    )


    return templates.TemplateResponse(
        request=request,
        name=(
            "insights/"
            "project_detail.html"
        ),
        context={
            "request":
                request,

            "current_user":
                current_user,

            "project":
                project,

            "order_items":
                order_items,
        },
    )