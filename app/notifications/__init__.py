from app.notifications.email_service import (
    send_email,
)

from app.notifications.order_email_service import (
    send_admin_new_order_notification,
    send_client_order_confirmation,
    send_client_status_change_notification,
)

from app.notifications.template_service import (
    render_email_template,
)