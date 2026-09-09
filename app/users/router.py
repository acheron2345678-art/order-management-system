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

from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_admin,
)

from app.core import templates

from app.core.config import (
    CSRF_COOKIE_NAME,
    JWT_ACCESS_COOKIE_NAME,
    JWT_REFRESH_COOKIE_NAME,
)

from app.database import get_db

from app.users.models import User

from app.users.service import (
    create_user,
    get_user_by_id,
    get_users,
    set_user_active_status,
    update_user,
)


router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
)


VALID_ROLES = {
    "admin",
    "client",
}


def render_user_form(
    *,
    request: Request,
    current_user: User,
    action: str,
    user: User | None,
    error: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="users/user_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "action": action,
            "user": user,
            "error": error,
            "form_data": form_data,
        },
        status_code=status_code,
    )


def clear_session_cookies(
    response: RedirectResponse,
):
    response.delete_cookie(
        key=JWT_ACCESS_COOKIE_NAME,
        path="/",
    )

    response.delete_cookie(
        key=JWT_REFRESH_COOKIE_NAME,
        path="/",
    )

    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
    )

    return response


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
    return templates.TemplateResponse(
        request=request,
        name="users/users.html",
        context={
            "request": request,
            "current_user": current_user,
            "users": get_users(db),
        },
    )


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
    return render_user_form(
        request=request,
        current_user=current_user,
        action="add",
        user=None,
    )


@router.post(
    "/add",
    response_class=HTMLResponse,
)
def add_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    username = username.strip()
    email = email.strip().lower()
    role = role.strip().lower()

    form_data = {
        "username": username,
        "email": email,
        "role": role,
    }

    if role not in VALID_ROLES:
        return render_user_form(
            request=request,
            current_user=current_user,
            action="add",
            user=None,
            error="Invalid user role.",
            form_data=form_data,
            status_code=400,
        )

    user_data = SimpleNamespace(
        username=username,
        email=email,
        password=password,
        role=role,
    )

    try:
        create_user(
            db,
            user_data,
        )

    except ValueError as error:
        return render_user_form(
            request=request,
            current_user=current_user,
            action="add",
            user=None,
            error=str(error),
            form_data=form_data,
            status_code=400,
        )

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


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
    user = get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return render_user_form(
        request=request,
        current_user=current_user,
        action="edit",
        user=user,
    )


@router.post(
    "/{user_id}/edit",
    response_class=HTMLResponse,
)
def edit_user(
    user_id: int,
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(""),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    user = get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    username = username.strip()
    email = email.strip().lower()
    role = role.strip().lower()

    form_data = {
        "username": username,
        "email": email,
        "role": role,
    }

    if role not in VALID_ROLES:
        return render_user_form(
            request=request,
            current_user=current_user,
            action="edit",
            user=user,
            error="Invalid user role.",
            form_data=form_data,
            status_code=400,
        )

    if (
        user.id == current_user.id
        and role != current_user.role
    ):
        return render_user_form(
            request=request,
            current_user=current_user,
            action="edit",
            user=user,
            error=(
                "You cannot change your own administrator role."
            ),
            form_data=form_data,
            status_code=400,
        )

    password_changed = bool(
        password
    )

    try:
        update_user(
            db=db,
            user=user,
            username=username,
            email=email,
            role=role,
            new_password=(
                password
                if password_changed
                else None
            ),
        )

    except ValueError as error:
        return render_user_form(
            request=request,
            current_user=current_user,
            action="edit",
            user=user,
            error=str(error),
            form_data=form_data,
            status_code=400,
        )

    if (
        user.id == current_user.id
        and password_changed
    ):
        response = RedirectResponse(
            url="/login",
            status_code=303,
        )

        return clear_session_cookies(
            response
        )

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


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
    user = get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot disable your own account."
            ),
        )

    try:
        set_user_active_status(
            db=db,
            user=user,
            is_active=(
                not user.is_active
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )
