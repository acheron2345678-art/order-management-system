from types import SimpleNamespace

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from pwdlib import PasswordHash

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_admin,
)

from app.core import templates

from app.database import (
    get_db,
)

from app.users.models import (
    User,
)

from app.users.service import (
    create_user,
)

from app.utils.email_rules import (
    require_gmail_address,
)


router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
)


password_hash = (
    PasswordHash.recommended()
)


VALID_ROLES = {
    "admin",
    "client",
}


# =========================================================
# USER LIST
# =========================================================

@router.get(
    "",
    response_class=HTMLResponse,
)
def users_page(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    users = (
        db.query(User)
        .order_by(
            User.id.desc()
        )
        .all()
    )


    return templates.TemplateResponse(
        request=request,
        name="users/users.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "users":
                users,
        },
    )


# =========================================================
# ADD USER PAGE
# =========================================================

@router.get(
    "/add",
    response_class=HTMLResponse,
)
def add_user_page(
    request: Request,

    current_user: User = Depends(
        require_admin
    ),
):
    return templates.TemplateResponse(
        request=request,
        name="users/user_form.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "action":
                "add",

            "user":
                None,

            "error":
                None,

            "form_data":
                None,
        },
    )


# =========================================================
# ADD USER
# =========================================================

@router.post(
    "/add",
    response_class=HTMLResponse,
)
def add_user(
    request: Request,

    username: str = Form(
        ...
    ),

    email: str = Form(
        ...
    ),

    password: str = Form(
        ...
    ),

    role: str = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    username = (
        username.strip()
    )

    email = (
        email.strip().lower()
    )

    role = (
        role.strip().lower()
    )


    # =========================================
    # BASIC VALIDATION
    # =========================================

    if not username:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "add",

                "user":
                    None,

                "error":
                    "Username is required.",

                "form_data":
                    {
                        "username":
                            username,

                        "email":
                            email,

                        "role":
                            role,
                    },
            },
            status_code=400,
        )


    if not password:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "add",

                "user":
                    None,

                "error":
                    "Password is required.",

                "form_data":
                    {
                        "username":
                            username,

                        "email":
                            email,

                        "role":
                            role,
                    },
            },
            status_code=400,
        )


    if role not in VALID_ROLES:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "add",

                "user":
                    None,

                "error":
                    "Invalid user role.",

                "form_data":
                    {
                        "username":
                            username,

                        "email":
                            email,

                        "role":
                            role,
                    },
            },
            status_code=400,
        )


    # =========================================
    # GMAIL VALIDATION
    # =========================================

    try:

        email = require_gmail_address(
            email
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "add",

                "user":
                    None,

                "error":
                    str(error),

                "form_data":
                    {
                        "username":
                            username,

                        "email":
                            email,

                        "role":
                            role,
                    },
            },
            status_code=400,
        )


    # =========================================
    # CREATE USER DATA
    # =========================================

    user_data = SimpleNamespace(
        username=username,
        email=email,
        password=password,
        role=role,
    )


    # =========================================
    # CREATE USER
    # =========================================

    try:

        create_user(
            db,
            user_data,
        )


    except ValueError as error:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "add",

                "user":
                    None,

                "error":
                    str(error),

                "form_data":
                    {
                        "username":
                            username,

                        "email":
                            email,

                        "role":
                            role,
                    },
            },
            status_code=400,
        )


    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


# =========================================================
# EDIT USER PAGE
# =========================================================

@router.get(
    "/{user_id}/edit",
    response_class=HTMLResponse,
)
def edit_user_page(
    user_id: int,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )


    if user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )


    return templates.TemplateResponse(
        request=request,
        name="users/user_form.html",
        context={
            "request":
                request,

            "current_user":
                current_user,

            "action":
                "edit",

            "user":
                user,

            "error":
                None,

            "form_data":
                None,
        },
    )


# =========================================================
# EDIT USER
# =========================================================

@router.post(
    "/{user_id}/edit",
    response_class=HTMLResponse,
)
def edit_user(
    user_id: int,

    request: Request,

    username: str = Form(
        ...
    ),

    email: str = Form(
        ...
    ),

    role: str = Form(
        ...
    ),

    password: str = Form(
        ""
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )


    if user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )


    username = (
        username.strip()
    )

    email = (
        email.strip().lower()
    )

    role = (
        role.strip().lower()
    )

    password = (
        password.strip()
    )


    form_data = {
        "username":
            username,

        "email":
            email,

        "role":
            role,
    }


    # =========================================
    # VALIDATION
    # =========================================

    if not username:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "edit",

                "user":
                    user,

                "error":
                    "Username is required.",

                "form_data":
                    form_data,
            },
            status_code=400,
        )


    if role not in VALID_ROLES:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "edit",

                "user":
                    user,

                "error":
                    "Invalid user role.",

                "form_data":
                    form_data,
            },
            status_code=400,
        )


    # =========================================
    # GMAIL VALIDATION
    # =========================================

    try:

        email = require_gmail_address(
            email
        )

    except ValueError as error:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "edit",

                "user":
                    user,

                "error":
                    str(error),

                "form_data":
                    form_data,
            },
            status_code=400,
        )


    # =========================================
    # DUPLICATE USERNAME
    # =========================================

    duplicate_username = (
        db.query(User)
        .filter(
            User.username
            == username,

            User.id
            !=
            user.id,
        )
        .first()
    )


    if duplicate_username:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "edit",

                "user":
                    user,

                "error":
                    "Username already exists.",

                "form_data":
                    form_data,
            },
            status_code=400,
        )


    # =========================================
    # DUPLICATE EMAIL
    # =========================================

    duplicate_email = (
        db.query(User)
        .filter(
            User.email
            == email,

            User.id
            !=
            user.id,
        )
        .first()
    )


    if duplicate_email:

        return templates.TemplateResponse(
            request=request,
            name="users/user_form.html",
            context={
                "request":
                    request,

                "current_user":
                    current_user,

                "action":
                    "edit",

                "user":
                    user,

                "error":
                    "Email address already exists.",

                "form_data":
                    form_data,
            },
            status_code=400,
        )


    # =========================================
    # UPDATE
    # =========================================

    user.username = (
        username
    )

    user.email = (
        email
    )

    user.role = (
        role
    )


    if password:

        user.password_hash = (
            password_hash.hash(
                password
            )
        )


    try:

        db.commit()

        db.refresh(
            user
        )


    except Exception:

        db.rollback()

        raise


    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


# =========================================================
# ACTIVATE / DEACTIVATE USER
# =========================================================

@router.post(
    "/{user_id}/toggle"
)
def toggle_user(
    user_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_admin
    ),
):
    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )


    if user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )


    # Prevent admin from disabling
    # the account currently being used.

    if user.id == current_user.id:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot deactivate "
                "your own account."
            ),
        )


    user.is_active = (
        not user.is_active
    )


    try:

        db.commit()

        db.refresh(
            user
        )


    except Exception:

        db.rollback()

        raise


    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )