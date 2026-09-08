from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_client,
)

from app.core import templates

from app.database import (
    get_db,
)

from app.users.models import (
    User,
)

from app.users.profile_service import (
    get_client_profile,
    save_client_profile,
)


router = APIRouter(
    prefix="/profile",
    tags=["Client Profile"],
)


@router.get(
    "",
    response_class=HTMLResponse,
)
def profile_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    profile = get_client_profile(
        db=db,
        user_id=current_user.id,
    )

    return templates.TemplateResponse(
        request=request,
        name="users/profile.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "profile":
                profile,

            "success":
                request.query_params.get(
                    "success"
                ),

            "error":
                None,

            "form_data":
                None,
        },
    )


@router.post(
    "",
    response_class=HTMLResponse,
)
def update_profile(
    request: Request,

    full_name: str = Form(
        ""
    ),

    company_name: str = Form(
        ""
    ),

    phone: str = Form(
        ""
    ),

    address_line1: str = Form(
        ""
    ),

    address_line2: str = Form(
        ""
    ),

    city: str = Form(
        ""
    ),

    state: str = Form(
        ""
    ),

    postal_code: str = Form(
        ""
    ),

    country: str = Form(
        "India"
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_client
    ),
):
    try:

        save_client_profile(
            db=db,

            user_id=(
                current_user.id
            ),

            full_name=(
                full_name
            ),

            company_name=(
                company_name
            ),

            phone=(
                phone
            ),

            address_line1=(
                address_line1
            ),

            address_line2=(
                address_line2
            ),

            city=(
                city
            ),

            state=(
                state
            ),

            postal_code=(
                postal_code
            ),

            country=(
                country
            ),
        )

    except ValueError as error:

        profile = get_client_profile(
            db=db,
            user_id=current_user.id,
        )

        return templates.TemplateResponse(
            request=request,
            name="users/profile.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "profile":
                    profile,

                "success":
                    None,

                "error":
                    str(error),

                "form_data":
                    {
                        "full_name":
                            full_name,

                        "company_name":
                            company_name,

                        "phone":
                            phone,

                        "address_line1":
                            address_line1,

                        "address_line2":
                            address_line2,

                        "city":
                            city,

                        "state":
                            state,

                        "postal_code":
                            postal_code,

                        "country":
                            country,
                    },
            },
            status_code=400,
        )

    return RedirectResponse(
        url="/profile?success=1",
        status_code=303,
    )