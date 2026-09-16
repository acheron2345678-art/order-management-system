import logging

from app.core.config import (
    ADMIN_NOTIFICATION_EMAIL,
)

from app.notifications.email_service import (
    send_email,
)

from app.notifications.template_service import (
    render_email_template,
)


logger = logging.getLogger(
    __name__
)


PLATFORM_NAMES = {
    "swiggy": "Swiggy",
    "insights": "Insights",
}


def normalize_platform(
    platform: str,
):
    platform = (
        platform
        .strip()
        .lower()
    )

    if platform not in PLATFORM_NAMES:
        raise ValueError(
            "Unsupported notification platform"
        )

    return platform


def format_order_date(
    order_date,
):
    if hasattr(
        order_date,
        "strftime",
    ):
        return order_date.strftime(
            "%d %b %Y"
        )

    return str(
        order_date
    )


def normalize_items(
    items,
):
    normalized = []

    for item in items:

        if isinstance(
            item,
            dict,
        ):
            product_name = (
                item.get(
                    "product_name"
                )
                or
                "Item"
            )

            quantity = int(
                item.get(
                    "quantity",
                    1,
                )
            )

            line_total = float(
                item.get(
                    "line_total",
                    0,
                )
            )

        else:
            product_name = (
                getattr(
                    item,
                    "product_name",
                    "Item",
                )
            )

            quantity = int(
                getattr(
                    item,
                    "quantity",
                    1,
                )
            )

            line_total = float(
                getattr(
                    item,
                    "line_total",
                    0,
                )
            )

        normalized.append(
            {
                "product_name":
                    product_name,

                "quantity":
                    quantity,

                "line_total":
                    line_total,
            }
        )

    return normalized


def build_items_text(
    items,
    platform: str,
):
    lines = []

    for item in items:

        if platform == "swiggy":

            lines.append(
                (
                    f"- {item['product_name']} "
                    f"x {item['quantity']} "
                    f"- ₹{item['line_total']:,.2f}"
                )
            )

        else:

            lines.append(
                (
                    f"- {item['product_name']} "
                    f"- ₹{item['line_total']:,.2f}"
                )
            )

    return "\n".join(
        lines
    )


def send_client_order_confirmation(
    platform: str,
    client_email: str,
    client_name: str,
    customer_name: str,
    order_number: str,
    order_date,
    status: str,
    amount,
    items,
):
    try:

        platform = normalize_platform(
            platform
        )

        platform_name = (
            PLATFORM_NAMES[
                platform
            ]
        )

        normalized_items = (
            normalize_items(
                items
            )
        )

        formatted_date = (
            format_order_date(
                order_date
            )
        )

        amount = float(
            amount
        )

        if platform == "swiggy":

            title = (
                f"Order Confirmed - "
                f"{order_number}"
            )

            subject = (
                f"Swiggy Order Confirmed - "
                f"{order_number}"
            )

            description = (
                "Your Swiggy order has been "
                "received successfully."
            )

        else:

            title = (
                f"Project Request Received - "
                f"{order_number}"
            )

            subject = (
                f"Insights Project Received - "
                f"{order_number}"
            )

            description = (
                "Your Insights project request "
                "has been received successfully."
            )

        html_body = (
            render_email_template(
                "client_order_confirmation.html",

                title=title,

                platform=platform,

                platform_name=platform_name,

                client_name=client_name,

                customer_name=customer_name,

                order_number=order_number,

                order_date=formatted_date,

                status=status,

                amount=amount,

                items=normalized_items,
            )
        )

        items_text = (
            build_items_text(
                normalized_items,
                platform,
            )
        )

        text_body = f"""
{platform_name}

{description}

Hi {client_name},

Order / Project Number:
{order_number}

Customer:
{customer_name}

Date:
{formatted_date}

Status:
{status.capitalize()}

Items:
{items_text}

Total:
₹{amount:,.2f}

You will receive another email whenever the status changes.

Order Management
""".strip()

        return send_email(
            recipient_email=client_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    except Exception:

        logger.exception(
            "Failed to build or send "
            "client order email for %s.",
            order_number,
        )

        return False


def send_admin_new_order_notification(
    platform: str,
    client_email: str,
    client_name: str,
    customer_name: str,
    order_number: str,
    order_date,
    status: str,
    amount,
    items,
):
    try:

        if not ADMIN_NOTIFICATION_EMAIL:

            logger.warning(
                "Admin notification email "
                "is not configured. "
                "Skipped admin notification "
                "for %s.",
                order_number,
            )

            return False

        platform = normalize_platform(
            platform
        )

        platform_name = (
            PLATFORM_NAMES[
                platform
            ]
        )

        normalized_items = (
            normalize_items(
                items
            )
        )

        formatted_date = (
            format_order_date(
                order_date
            )
        )

        amount = float(
            amount
        )

        if platform == "swiggy":

            title = (
                f"New Swiggy Order - "
                f"{order_number}"
            )

            subject = (
                f"New Swiggy Order - "
                f"{order_number}"
            )

        else:

            title = (
                f"New Insights Project - "
                f"{order_number}"
            )

            subject = (
                f"New Insights Project - "
                f"{order_number}"
            )

        html_body = (
            render_email_template(
                "admin_new_order.html",

                title=title,

                platform=platform,

                platform_name=platform_name,

                client_name=client_name,

                client_email=client_email,

                customer_name=customer_name,

                order_number=order_number,

                order_date=formatted_date,

                status=status,

                amount=amount,

                items=normalized_items,
            )
        )

        items_text = (
            build_items_text(
                normalized_items,
                platform,
            )
        )

        text_body = f"""
ORDER MANAGEMENT

New {platform_name} activity received.

Platform:
{platform_name}

Order / Project Number:
{order_number}

Client Account:
{client_name}

Client Email:
{client_email}

Customer:
{customer_name}

Date:
{formatted_date}

Status:
{status.capitalize()}

Items:
{items_text}

Total:
₹{amount:,.2f}

Review this item from Order Management.
""".strip()

        return send_email(
            recipient_email=(
                ADMIN_NOTIFICATION_EMAIL
            ),
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    except Exception:

        logger.exception(
            "Failed to build or send "
            "admin notification for %s.",
            order_number,
        )

        return False

def send_merchant_new_order_notification(
    merchant_email: str,
    merchant_name: str,
    restaurant_name: str,
    client_email: str,
    client_name: str,
    customer_name: str,
    order_number: str,
    order_date,
    status: str,
    amount,
    items,
):
    """
    Send the assigned restaurant merchant
    a new Swiggy order notification.
    """

    try:

        normalized_items = (
            normalize_items(
                items
            )
        )


        formatted_date = (
            format_order_date(
                order_date
            )
        )


        amount = float(
            amount
        )


        title = (
            f"New Order - "
            f"{order_number}"
        )


        subject = (
            f"New Swiggy Order for "
            f"{restaurant_name} - "
            f"{order_number}"
        )


        html_body = (
            render_email_template(
                "merchant_new_order.html",

                title=title,

                merchant_name=(
                    merchant_name
                ),

                restaurant_name=(
                    restaurant_name
                ),

                client_name=(
                    client_name
                ),

                client_email=(
                    client_email
                ),

                customer_name=(
                    customer_name
                ),

                order_number=(
                    order_number
                ),

                order_date=(
                    formatted_date
                ),

                status=(
                    status
                ),

                amount=(
                    amount
                ),

                items=(
                    normalized_items
                ),
            )
        )


        items_text = (
            build_items_text(
                normalized_items,
                "swiggy",
            )
        )


        text_body = f"""
SWIGGY MERCHANT

A new order has been placed for {restaurant_name}.

Hi {merchant_name},

Order Number:
{order_number}

Customer:
{customer_name}

Client Account:
{client_name}

Client Email:
{client_email}

Date:
{formatted_date}

Status:
{status.capitalize()}

Items:
{items_text}

Order Total:
₹{amount:,.2f}

Open the Merchant Console to review and process this order.

Order Management
""".strip()


        return send_email(
            recipient_email=(
                merchant_email
            ),

            subject=(
                subject
            ),

            html_body=(
                html_body
            ),

            text_body=(
                text_body
            ),
        )


    except Exception:

        logger.exception(
            "Failed to build or send "
            "merchant notification "
            "for %s.",
            order_number,
        )

        return False

def send_client_status_change_notification(
    platform: str,
    client_email: str,
    client_name: str,
    order_number: str,
    old_status: str,
    new_status: str,
):
    try:

        platform = normalize_platform(
            platform
        )

        platform_name = (
            PLATFORM_NAMES[
                platform
            ]
        )


        if platform == "swiggy":

            title = (
                f"Order Status Updated - "
                f"{order_number}"
            )

            subject = (
                f"Swiggy Order Status Updated - "
                f"{order_number}"
            )

            item_name = "order"

        else:

            title = (
                f"Project Status Updated - "
                f"{order_number}"
            )

            subject = (
                f"Insights Project Status Updated - "
                f"{order_number}"
            )

            item_name = "project"


        html_body = (
            render_email_template(
                "client_status_changed.html",

                title=title,

                platform=platform,

                platform_name=platform_name,

                client_name=client_name,

                order_number=order_number,

                old_status=old_status,

                new_status=new_status,
            )
        )


        text_body = f"""
{platform_name}

Status Update

Hi {client_name},

The status of your {item_name}
{order_number}
has changed.

Previous Status:
{old_status.capitalize()}

Current Status:
{new_status.capitalize()}

You can sign in to Order Management to view the latest details.

Order Management
""".strip()


        return send_email(
            recipient_email=client_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )


    except Exception:

        logger.exception(
            "Failed to build or send "
            "status notification for %s.",
            order_number,
        )

        return False