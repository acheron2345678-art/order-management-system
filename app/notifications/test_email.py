import sys

from app.notifications.email_service import (
    send_email,
)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage:"
        )

        print(
            "python -m app.notifications.test_email "
            "recipient@example.com"
        )

        return

    recipient = (
        sys.argv[1]
        .strip()
    )

    subject = (
        "Order Management - Email Test"
    )

    text_body = """
Order Management Email Test

Your SMTP email configuration is working successfully.

This is only a test message.
""".strip()

    html_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>

<body
    style="
        margin: 0;
        padding: 0;
        background: #f4f6f8;
        font-family: Arial, Helvetica, sans-serif;
        color: #212529;
    "
>

    <div
        style="
            max-width: 620px;
            margin: 40px auto;
            padding: 0 20px;
        "
    >

        <div
            style="
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                overflow: hidden;
            "
        >

            <div
                style="
                    padding: 24px 30px;
                    background: #0d6efd;
                    color: #ffffff;
                "
            >

                <div
                    style="
                        font-size: 13px;
                        font-weight: 700;
                        letter-spacing: 1px;
                    "
                >
                    ORDER MANAGEMENT
                </div>

                <h1
                    style="
                        margin: 8px 0 0;
                        font-size: 24px;
                    "
                >
                    Email Test Successful
                </h1>

            </div>


            <div
                style="
                    padding: 30px;
                "
            >

                <p
                    style="
                        margin-top: 0;
                        font-size: 16px;
                        line-height: 1.6;
                    "
                >
                    Your Order Management application
                    successfully connected to the configured
                    SMTP server.
                </p>


                <div
                    style="
                        padding: 16px;
                        margin: 24px 0;
                        background: #f8f9fa;
                        border-radius: 10px;
                    "
                >

                    <strong>
                        SMTP configuration status:
                    </strong>

                    <div
                        style="
                            margin-top: 6px;
                            color: #198754;
                            font-weight: 700;
                        "
                    >
                        ✓ Working
                    </div>

                </div>


                <p
                    style="
                        margin-bottom: 0;
                        color: #6c757d;
                        font-size: 14px;
                    "
                >
                    This is a test email.
                    No order was created.
                </p>

            </div>

        </div>

    </div>

</body>
</html>
""".strip()

    success = send_email(
        recipient_email=recipient,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    if success:

        print(
            f"Email sent successfully to {recipient}"
        )

    else:

        print(
            "Email could not be sent."
        )

        print(
            "Check the terminal logs "
            "for the SMTP error."
        )


if __name__ == "__main__":
    main()