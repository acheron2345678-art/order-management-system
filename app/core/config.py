import os

from dotenv import load_dotenv


load_dotenv()


# =========================================
# APPLICATION
# =========================================

APP_NAME = "Order Management"

TEMPLATES_DIR = "templates"

STATIC_DIR = "static"


APP_ENV = (
    os.getenv(
        "APP_ENV",
        "development",
    )
    .strip()
    .lower()
)


IS_PRODUCTION = (
    APP_ENV
    ==
    "production"
)


# =========================================
# DATABASE
# =========================================

DATABASE_URL = (
    os.getenv(
        "DATABASE_URL",
        "",
    )
    .strip()
)


if not DATABASE_URL:

    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Add it to your environment or .env file."
    )


# =========================================
# PLATFORMS
# =========================================

VALID_PLATFORMS = {
    "swiggy": "Swiggy",
    "insights": "Insights",
}


# =========================================
# ORDER STATUSES
# =========================================

ORDER_STATUSES = (
    "pending",
    "processing",
    "completed",
    "cancelled",
)


ORDER_STATUS_TRANSITIONS = {

    "pending": {
        "processing",
        "cancelled",
    },

    "processing": {
        "completed",
        "cancelled",
    },

    "completed":
        set(),

    "cancelled":
        set(),
}


# =========================================
# JWT
# =========================================

JWT_ALGORITHM = "HS256"


JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

JWT_IDLE_TIMEOUT_MINUTES = 30


JWT_SECRET_KEY = (
    os.getenv(
        "JWT_SECRET_KEY",
        "",
    )
    .strip()
)


# =========================================
# DEVELOPMENT JWT FALLBACK
# =========================================

if not JWT_SECRET_KEY:

    if IS_PRODUCTION:

        raise RuntimeError(
            "JWT_SECRET_KEY must be configured "
            "in production."
        )

    JWT_SECRET_KEY = (
        "order-management-development-"
        "secret-key-not-for-production"
    )


# =========================================
# PRODUCTION JWT VALIDATION
# =========================================

if (
    IS_PRODUCTION
    and
    len(
        JWT_SECRET_KEY.encode(
            "utf-8"
        )
    )
    <
    32
):

    raise RuntimeError(
        "JWT_SECRET_KEY must be at least "
        "32 bytes long in production."
    )


# =========================================
# JWT COOKIES
# =========================================

JWT_ACCESS_COOKIE_NAME = (
    "order_management_access_token"
)


JWT_REFRESH_COOKIE_NAME = (
    "order_management_refresh_token"
)


JWT_COOKIE_SECURE = (
    os.getenv(
        "JWT_COOKIE_SECURE",
        (
            "true"
            if IS_PRODUCTION
            else
            "false"
        ),
    )
    .strip()
    .lower()
    ==
    "true"
)


JWT_COOKIE_SAMESITE = (
    os.getenv(
        "JWT_COOKIE_SAMESITE",
        "lax",
    )
    .strip()
    .lower()
)


if JWT_COOKIE_SAMESITE not in {
    "lax",
    "strict",
    "none",
}:

    raise RuntimeError(
        "JWT_COOKIE_SAMESITE must be "
        "'lax', 'strict', or 'none'."
    )


if (
    JWT_COOKIE_SAMESITE
    ==
    "none"
    and
    not JWT_COOKIE_SECURE
):

    raise RuntimeError(
        "SameSite=None cookies require "
        "JWT_COOKIE_SECURE=true."
    )


# =========================================
# CSRF
# =========================================

CSRF_COOKIE_NAME = (
    "order_management_csrf_token"
)


CSRF_HEADER_NAME = (
    "X-CSRF-Token"
)


# =========================================
# EMAIL
# =========================================

SMTP_HOST = (
    os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com",
    )
    .strip()
)


SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587",
    )
)


SMTP_USERNAME = (
    os.getenv(
        "SMTP_USERNAME",
        "",
    )
    .strip()
)


SMTP_PASSWORD = (
    os.getenv(
        "SMTP_PASSWORD",
        "",
    )
)


SMTP_FROM_EMAIL = (
    os.getenv(
        "SMTP_FROM_EMAIL",
        SMTP_USERNAME,
    )
    .strip()
)


SMTP_FROM_NAME = (
    os.getenv(
        "SMTP_FROM_NAME",
        "Order Management",
    )
    .strip()
)


ADMIN_NOTIFICATION_EMAIL = (
    os.getenv(
        "ADMIN_NOTIFICATION_EMAIL",
        "",
    )
    .strip()
)


SMTP_USE_TLS = (
    os.getenv(
        "SMTP_USE_TLS",
        "true",
    )
    .strip()
    .lower()
    ==
    "true"
)


EMAIL_ENABLED = (
    os.getenv(
        "EMAIL_ENABLED",
        "true",
    )
    .strip()
    .lower()
    ==
    "true"
)