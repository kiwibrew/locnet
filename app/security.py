import hmac
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response, status

from app.config import settings


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_token(request: Request, submitted_token: str | None) -> None:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if (
        not cookie_token
        or not submitted_token
        or not hmac.compare_digest(cookie_token, submitted_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )


def require_api_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if request.headers.get("authorization") is not None:
        return
    verify_csrf_token(request, request.headers.get("x-csrf-token"))


def require_same_origin(request: Request) -> None:
    """Require an unsafe proxy-forwarded request to originate on this site."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    expected_origin = f"{scheme}://{host}"
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid origin"
        )

    parsed = urlsplit(source)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or f"{parsed.scheme}://{parsed.netloc}" != expected_origin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid origin"
        )


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        max_age=settings.session_max_age_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_authentication_cookies(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )
