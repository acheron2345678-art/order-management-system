from starlette.datastructures import MutableHeaders

from app.core.config import (
    HSTS_MAX_AGE_SECONDS,
    IS_PRODUCTION,
)


AUTH_NOSTORE_PATHS = {
    "/login",
    "/auth/session",
    "/auth/refresh",
    "/api/auth/token",
}


class SecurityHeadersMiddleware:
    def __init__(
        self,
        app,
    ):
        self.app = app


    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        if scope["type"] != "http":
            await self.app(
                scope,
                receive,
                send,
            )
            return


        async def send_with_security_headers(
            message,
        ):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(
                    scope=message
                )

                headers.setdefault(
                    "X-Content-Type-Options",
                    "nosniff",
                )

                headers.setdefault(
                    "X-Frame-Options",
                    "DENY",
                )

                headers.setdefault(
                    "Referrer-Policy",
                    "strict-origin-when-cross-origin",
                )

                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), microphone=(), geolocation=()",
                )

                headers.setdefault(
                    "Content-Security-Policy",
                    (
                        "base-uri 'self'; "
                        "object-src 'none'; "
                        "frame-ancestors 'none'; "
                        "form-action 'self'"
                    ),
                )

                path = scope.get(
                    "path",
                    "",
                )

                if path in AUTH_NOSTORE_PATHS:
                    headers.setdefault(
                        "Cache-Control",
                        "no-store",
                    )

                    headers.setdefault(
                        "Pragma",
                        "no-cache",
                    )

                if (
                    IS_PRODUCTION
                    and
                    scope.get("scheme") == "https"
                    and
                    HSTS_MAX_AGE_SECONDS > 0
                ):
                    headers.setdefault(
                        "Strict-Transport-Security",
                        (
                            "max-age="
                            f"{HSTS_MAX_AGE_SECONDS}"
                        ),
                    )

            await send(
                message
            )


        await self.app(
            scope,
            receive,
            send_with_security_headers,
        )
