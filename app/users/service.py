from sqlalchemy.orm import Session

from app.auth.refresh_service import (
    revoke_all_user_refresh_tokens,
)

from app.core.security import (
    hash_password,
    validate_password,
)

from app.users.models import User

from app.utils.email_rules import (
    require_gmail_address,
)


ALLOWED_ROLES = {
    "admin",
    "client",
    "merchant"
}


MAX_USERNAME_LENGTH = 100
MAX_EMAIL_LENGTH = 255


def get_user_by_id(
    db: Session,
    user_id: int,
):
    return (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )


def get_user_by_username(
    db: Session,
    username: str,
):
    return (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )


def get_user_by_email(
    db: Session,
    email: str,
):
    return (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )


def get_users(
    db: Session,
):
    return (
        db.query(User)
        .order_by(
            User.id.desc()
        )
        .all()
    )


def get_clients(
    db: Session,
):
    return (
        db.query(User)
        .filter(
            User.role == "client",
            User.is_active.is_(True),
        )
        .order_by(
            User.username.asc()
        )
        .all()
    )


def count_active_admins(
    db: Session,
) -> int:
    return (
        db.query(User)
        .filter(
            User.role == "admin",
            User.is_active.is_(True),
        )
        .count()
    )


def normalize_username(
    username: str,
) -> str:
    username = (
        username or ""
    ).strip()

    if not username:
        raise ValueError(
            "Username is required."
        )

    if len(username) > MAX_USERNAME_LENGTH:
        raise ValueError(
            "Username must be 100 characters or fewer."
        )

    return username


def normalize_role(
    role: str,
) -> str:
    role = (
        role or ""
    ).strip().lower()

    if role not in ALLOWED_ROLES:
        raise ValueError(
            "Invalid user role."
        )

    return role


def normalize_email(
    email: str,
) -> str:
    email = require_gmail_address(
        email
    )

    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(
            "Email address must be 255 characters or fewer."
        )

    return email


def ensure_username_available(
    db: Session,
    username: str,
    *,
    exclude_user_id: int | None = None,
):
    query = (
        db.query(User)
        .filter(
            User.username == username
        )
    )

    if exclude_user_id is not None:
        query = query.filter(
            User.id != exclude_user_id
        )

    if query.first():
        raise ValueError(
            "Username already exists."
        )


def ensure_email_available(
    db: Session,
    email: str,
    *,
    exclude_user_id: int | None = None,
):
    query = (
        db.query(User)
        .filter(
            User.email.ilike(email)
        )
    )

    if exclude_user_id is not None:
        query = query.filter(
            User.id != exclude_user_id
        )

    if query.first():
        raise ValueError(
            "Email address already exists."
        )


def create_user(
    db: Session,
    user_data,
):
    username = normalize_username(
        user_data.username
    )

    email = normalize_email(
        user_data.email
    )

    role = normalize_role(
        user_data.role
    )

    password = validate_password(
        user_data.password,
        username=username,
        email=email,
    )

    ensure_username_available(
        db,
        username,
    )

    ensure_email_available(
        db,
        email,
    )

    new_user = User(
        username=username,
        email=email,
        password_hash=hash_password(
            password
        ),
        role=role,
        is_active=True,
    )

    try:
        db.add(
            new_user
        )

        db.commit()

        db.refresh(
            new_user
        )

        return new_user

    except Exception:
        db.rollback()
        raise


def update_user(
    db: Session,
    user: User,
    username: str,
    email: str,
    role: str,
    new_password: str | None = None,
):
    username = normalize_username(
        username
    )

    email = normalize_email(
        email
    )

    role = normalize_role(
        role
    )

    ensure_username_available(
        db,
        username,
        exclude_user_id=user.id,
    )

    ensure_email_available(
        db,
        email,
        exclude_user_id=user.id,
    )

    role_changed = (
        user.role != role
    )

    password_changed = bool(
        new_password
    )

    if (
        role_changed
        and user.role == "admin"
        and user.is_active
        and count_active_admins(db) <= 1
    ):
        raise ValueError(
            "The last active administrator cannot be changed to another role."
        )

    if password_changed:
        validate_password(
            new_password,
            username=username,
            email=email,
        )

    user.username = username
    user.email = email
    user.role = role

    if password_changed:
        user.password_hash = hash_password(
            new_password
        )

    if (
        role_changed
        or password_changed
    ):
        revoke_all_user_refresh_tokens(
            db,
            user.id,
            commit=False,
        )

    try:
        db.commit()
        db.refresh(
            user
        )

        return user

    except Exception:
        db.rollback()
        raise


def set_user_active_status(
    db: Session,
    user: User,
    is_active: bool,
):
    if (
        not is_active
        and user.role == "admin"
        and user.is_active
        and count_active_admins(db) <= 1
    ):
        raise ValueError(
            "The last active administrator cannot be disabled."
        )

    user.is_active = is_active

    if not is_active:
        revoke_all_user_refresh_tokens(
            db,
            user.id,
            commit=False,
        )

    try:
        db.commit()
        db.refresh(
            user
        )

        return user

    except Exception:
        db.rollback()
        raise
