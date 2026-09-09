from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy.orm import Session

from app.auth.models import (
    RefreshToken,
)

from app.core.config import (
    JWT_IDLE_TIMEOUT_MINUTES,
)


IST = timezone(
    timedelta(
        hours=5,
        minutes=30,
    )
)


def ist_now():
    return (
        datetime.now(IST)
        .replace(
            tzinfo=None
        )
    )


def create_refresh_token_record(
    db: Session,
    user_id: int,
    token_id: str,
    expires_at,
):
    expires_at_ist = (
        expires_at
        .astimezone(IST)
        .replace(
            tzinfo=None
        )
    )

    record = RefreshToken(
        user_id=user_id,
        token_id=token_id,
        last_activity=ist_now(),
        expires_at=expires_at_ist,
    )

    db.add(
        record
    )

    db.commit()

    db.refresh(
        record
    )

    return record


def get_refresh_token_record(
    db: Session,
    token_id: str,
):
    return (
        db.query(
            RefreshToken
        )
        .filter(
            RefreshToken.token_id
            ==
            token_id
        )
        .first()
    )


def is_refresh_token_valid(
    record: RefreshToken | None,
):
    if not record:
        return False

    if (
        record.revoked_at
        is not None
    ):
        return False

    if (
        record.expires_at
        <=
        ist_now()
    ):
        return False

    return True


def is_refresh_token_active(
    record: RefreshToken | None,
):
    if not is_refresh_token_valid(
        record
    ):
        return False

    if not record.last_activity:
        return False

    idle_limit = (
        ist_now()
        -
        timedelta(
            minutes=(
                JWT_IDLE_TIMEOUT_MINUTES
            )
        )
    )

    if (
        record.last_activity
        <
        idle_limit
    ):
        return False

    return True


def touch_refresh_token(
    db: Session,
    record: RefreshToken,
):
    record.last_activity = (
        ist_now()
    )

    db.commit()

    db.refresh(
        record
    )

    return record


def revoke_refresh_token(
    db: Session,
    record: RefreshToken,
):
    if (
        record.revoked_at
        is None
    ):
        record.revoked_at = (
            ist_now()
        )

        db.commit()

        db.refresh(
            record
        )

    return record


def revoke_all_user_refresh_tokens(
    db: Session,
    user_id: int,
    *,
    commit: bool = True,
) -> int:
    records = (
        db.query(
            RefreshToken
        )
        .filter(
            RefreshToken.user_id
            ==
            user_id,
            RefreshToken.revoked_at
            .is_(None),
        )
        .all()
    )

    if not records:
        return 0

    revoked_at = ist_now()

    for record in records:
        record.revoked_at = (
            revoked_at
        )

    if commit:
        db.commit()

    return len(records)


def has_refresh_token_timed_out(
    record: RefreshToken | None,
):
    if not record:
        return False

    if not record.last_activity:
        return False

    idle_limit = (
        ist_now()
        -
        timedelta(
            minutes=(
                JWT_IDLE_TIMEOUT_MINUTES
            )
        )
    )

    return (
        record.last_activity
        <
        idle_limit
    )


def rotate_refresh_token_record(
    db: Session,
    old_record: RefreshToken,
    user_id: int,
    new_token_id: str,
    new_expires_at,
):
    now = ist_now()

    expires_at_ist = (
        new_expires_at
        .astimezone(IST)
        .replace(
            tzinfo=None
        )
    )

    old_record.revoked_at = now

    new_record = RefreshToken(
        user_id=user_id,
        token_id=new_token_id,
        last_activity=now,
        expires_at=expires_at_ist,
    )

    try:
        db.add(
            new_record
        )

        db.commit()

        db.refresh(
            old_record
        )

        db.refresh(
            new_record
        )

    except Exception:
        db.rollback()
        raise

    return new_record
