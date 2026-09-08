import secrets

from fastapi import HTTPException,Request,status

from app.core.config import CSRF_COOKIE_NAME,CSRF_HEADER_NAME

SAFE_METHODS={
    "GET",
    "HEAD",
    "OPTIONS"
}

CSRF_EXEMPT_PATHS={
    "/login",
    "/api/auth/token"
}

def create_csrf_token():
    return secrets.token_urlsafe(32)

async def validate_csrf(request:Request):
    method=request.method.upper()

    if method in SAFE_METHODS:
        return

    path=request.url.path

    if path in CSRF_EXEMPT_PATHS:
        return

    if path.startswith("/api"):
        return

    cookie_token=request.cookies.get(CSRF_COOKIE_NAME)

    if not cookie_token:
        raise HTTPException(status_code=403,detail="CSRF token missing")

    submitted_token=request.headers.get(CSRF_HEADER_NAME)

    if not submitted_token:
        content_type=request.headers.get("content-type","")

    if (
        "application/x-www-form-urlencoded"
        in content_type
        or 
        "multipart/form-data"
        in content_type
    ):

        form=await request.form()

        submitted_token=form.get("csrf_token")


    if not submitted_token:
        raise HTTPException(status_code=403,detail="CSRF token missing")

    try:
        valid=secrets.compare_digest(
            str(cookie_token),
            str(submitted_token)
        )

    except TypeError:
        valid=False

    if not valid:
        raise HTTPException(status_code=403,detail="Invalid CSRF token")