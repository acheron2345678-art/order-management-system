import logging
import smtplib

from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import (
    EMAIL_ENABLED,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_TLS,
)

from app.utils.email_rules import (
    is_gmail_address,
    normalize_email,
)


logger = logging.getLogger(
    __name__
)


def send_email(
    recipient_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:

    # =========================================
    # EMAIL ENABLED
    # =========================================

    if not EMAIL_ENABLED:

        logger.info(
            "Email sending is disabled."
        )

        return False


    # =========================================
    # NORMALIZE RECIPIENT
    # =========================================

    recipient_email = normalize_email(
        recipient_email
    )


    if not recipient_email:

        logger.warning(
            "Email skipped because "
            "no recipient was supplied."
        )

        return False


    # =========================================
    # GMAIL ONLY
    # =========================================

    if not is_gmail_address(
        recipient_email
    ):

        logger.warning(
            "Email skipped because "
            "recipient is not a Gmail "
            "account: %s",
            recipient_email,
        )

        return False


    # =========================================
    # SMTP CONFIG VALIDATION
    # =========================================

    if not SMTP_HOST:

        logger.error(
            "Email could not be sent "
            "because SMTP_HOST is missing."
        )

        return False


    if not SMTP_USERNAME:

        logger.error(
            "Email could not be sent "
            "because SMTP_USERNAME "
            "is missing."
        )

        return False


    if not SMTP_PASSWORD:

        logger.error(
            "Email could not be sent "
            "because SMTP_PASSWORD "
            "is missing."
        )

        return False


    if not SMTP_FROM_EMAIL:

        logger.error(
            "Email could not be sent "
            "because SMTP_FROM_EMAIL "
            "is missing."
        )

        return False


    if not subject:

        logger.error(
            "Email could not be sent "
            "because subject is missing."
        )

        return False


    if not html_body:

        logger.error(
            "Email could not be sent "
            "because HTML body is missing."
        )

        return False


    # =========================================
    # BUILD MESSAGE
    # =========================================

    message = EmailMessage()


    message["Subject"] = (
        subject
    )


    message["From"] = formataddr(
        (
            SMTP_FROM_NAME,
            SMTP_FROM_EMAIL,
        )
    )


    message["To"] = (
        recipient_email
    )


    # =========================================
    # TEXT VERSION
    # =========================================

    if text_body:

        message.set_content(
            text_body
        )

    else:

        message.set_content(
            "This is an automated "
            "notification from "
            "Order Management."
        )


    # =========================================
    # HTML VERSION
    # =========================================

    message.add_alternative(
        html_body,
        subtype="html",
    )


    # =========================================
    # SEND EMAIL
    # =========================================

    try:

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
        ) as server:

            server.ehlo()


            if SMTP_USE_TLS:

                server.starttls()

                server.ehlo()


            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD,
            )


            server.send_message(
                message
            )


        logger.info(
            "Email sent successfully "
            "to %s",
            recipient_email,
        )

        return True


    # =========================================
    # AUTHENTICATION ERROR
    # =========================================

    except smtplib.SMTPAuthenticationError:

        logger.exception(
            "SMTP authentication failed."
        )

        return False


    # =========================================
    # SMTP ERROR
    # =========================================

    except smtplib.SMTPException:

        logger.exception(
            "SMTP error while sending "
            "email to %s",
            recipient_email,
        )

        return False


    # =========================================
    # UNKNOWN ERROR
    # =========================================

    except Exception:

        logger.exception(
            "Unexpected error while "
            "sending email to %s",
            recipient_email,
        )

        return False