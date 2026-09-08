import os

from dotenv import load_dotenv

load_dotenv()


APP_NAME = "Order Management"

TEMPLATES_DIR = "templates"

STATIC_DIR = "static"


VALID_PLATFORMS = {
    "swiggy": "Swiggy",
    "insights": "Insights",
}


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

    "completed": set(),

    "cancelled": set(),
}


JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "order-management-development-secret-key-change-in-production",
)

JWT_ALGORITHM = "HS256"


JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

JWT_IDLE_TIMEOUT_MINUTES=30

JWT_ACCESS_COOKIE_NAME = (
    "order_management_access_token"
)

JWT_REFRESH_COOKIE_NAME = (
    "order_management_refresh_token"
)

JWT_COOKIE_SECURE = False

JWT_COOKIE_SAMESITE = "lax"

CSRF_COOKIE_NAME="order_management_csrf_token"
CSRF_HEADER_NAME="X-CSRF-Token"


SMTP_HOST=os.getenv("SMTP_HOST","smtp.gmail.com")

SMTP_PORT=int(os.getenv("SMTP_PORT","587"))

SMTP_USERNAME=os.getenv("SMTP_USERNAME","")

SMTP_PASSWORD=os.getenv("SMTP_PASSWORD","")

SMTP_FROM_EMAIL=os.getenv("SMTP_FROM_EMAIL",SMTP_USERNAME)

SMTP_FROM_NAME=os.getenv("STMP_FROM_NAME","Order Management")

ADMIN_NOTIFICATION_EMAIL=os.getenv("ADMIN_NOTIFICATION_EMAIL","")

SMTP_USE_TLS=os.getenv("SMTP_USE_TLS","true").strip().lower()=="true"

EMAIL_ENABLED=os.getenv("EMAIL_ENABLED","true").strip().lower()=="true"

