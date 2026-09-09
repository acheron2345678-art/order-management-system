from urllib.parse import urlsplit

from starlette.middleware.base import (
    BaseHTTPMiddleware,
)

from starlette.responses import (
    PlainTextResponse,
)


REDIRECT_QUERY_PARAMETERS = {
    "next",
    "return_url",
    "redirect",
}


def is_safe_local_redirect(
    url: str | None,
) -> bool:
    if url is None:
        return True

    candidate = url.strip()

    if not candidate:
        return True

    if any(
        ord(character) < 32
        for character in candidate
    ):
        return False

    if "\\" in candidate:
        return False

    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
    ):
        return False

    parsed = urlsplit(
        candidate
    )

    if (
        parsed.scheme
        or parsed.netloc
    ):
        return False

    return True


class RedirectTargetValidationMiddleware(
    BaseHTTPMiddleware
):
    async def dispatch(
        self,
        request,
        call_next,
    ):
        for parameter in (
            REDIRECT_QUERY_PARAMETERS
        ):
            target = (
                request.query_params.get(
                    parameter
                )
            )

            if (
                target is not None
                and not is_safe_local_redirect(
                    target
                )
            ):
                return PlainTextResponse(
                    "Invalid redirect target.",
                    status_code=400,
                )

        return await call_next(
            request
        )