from sqlalchemy.orm import Session

from app.users.profile_models import (
    ClientProfile,
)


def clean_optional_text(
    value: str | None,
):
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return value


def get_client_profile(
    db: Session,
    user_id: int,
):
    return (
        db.query(ClientProfile)
        .filter(
            ClientProfile.user_id
            ==
            user_id
        )
        .first()
    )


def save_client_profile(
    db: Session,
    user_id: int,
    full_name: str,
    company_name: str,
    phone: str,
    address_line1: str,
    address_line2: str,
    city: str,
    state: str,
    postal_code: str,
    country: str,
):
    full_name = clean_optional_text(
        full_name
    )

    company_name = clean_optional_text(
        company_name
    )

    phone = clean_optional_text(
        phone
    )

    address_line1 = clean_optional_text(
        address_line1
    )

    address_line2 = clean_optional_text(
        address_line2
    )

    city = clean_optional_text(
        city
    )

    state = clean_optional_text(
        state
    )

    postal_code = clean_optional_text(
        postal_code
    )

    country = clean_optional_text(
        country
    ) or "India"


    # =========================================
    # LENGTH VALIDATION
    # =========================================

    if (
        full_name
        and
        len(full_name) > 100
    ):
        raise ValueError(
            "Full name cannot exceed "
            "100 characters."
        )


    if (
        company_name
        and
        len(company_name) > 100
    ):
        raise ValueError(
            "Company name cannot exceed "
            "100 characters."
        )


    if (
        phone
        and
        len(phone) > 20
    ):
        raise ValueError(
            "Phone number cannot exceed "
            "20 characters."
        )


    if (
        address_line1
        and
        len(address_line1) > 255
    ):
        raise ValueError(
            "Address line 1 cannot exceed "
            "255 characters."
        )


    if (
        address_line2
        and
        len(address_line2) > 255
    ):
        raise ValueError(
            "Address line 2 cannot exceed "
            "255 characters."
        )


    if (
        city
        and
        len(city) > 100
    ):
        raise ValueError(
            "City cannot exceed "
            "100 characters."
        )


    if (
        state
        and
        len(state) > 100
    ):
        raise ValueError(
            "State cannot exceed "
            "100 characters."
        )


    if (
        postal_code
        and
        len(postal_code) > 20
    ):
        raise ValueError(
            "Postal code cannot exceed "
            "20 characters."
        )


    if len(country) > 100:
        raise ValueError(
            "Country cannot exceed "
            "100 characters."
        )


    # =========================================
    # FIND EXISTING PROFILE
    # =========================================

    profile = (
        get_client_profile(
            db=db,
            user_id=user_id,
        )
    )


    # =========================================
    # CREATE PROFILE
    # =========================================

    if profile is None:

        profile = ClientProfile(
            user_id=user_id
        )

        db.add(
            profile
        )


    # =========================================
    # UPDATE PROFILE
    # =========================================

    profile.full_name = (
        full_name
    )

    profile.company_name = (
        company_name
    )

    profile.phone = (
        phone
    )

    profile.address_line1 = (
        address_line1
    )

    profile.address_line2 = (
        address_line2
    )

    profile.city = (
        city
    )

    profile.state = (
        state
    )

    profile.postal_code = (
        postal_code
    )

    profile.country = (
        country
    )


    try:

        db.commit()

        db.refresh(
            profile
        )

        return profile


    except Exception:

        db.rollback()

        raise