from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


EMAIL_TEMPLATE_DIR = (
    PROJECT_ROOT
    / "templates"
    / "emails"
)


email_environment = Environment(
    loader=FileSystemLoader(
        EMAIL_TEMPLATE_DIR
    ),
    autoescape=select_autoescape(
        [
            "html",
            "xml",
        ]
    ),
)


def render_email_template(
    template_name: str,
    **context,
):
    template = (
        email_environment
        .get_template(
            template_name
        )
    )

    return template.render(
        **context
    )