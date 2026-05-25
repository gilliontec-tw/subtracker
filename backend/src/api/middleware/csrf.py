import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

# Paths exempt from CSRF — login and refresh create/renew the session itself
CSRF_EXEMPT_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in CSRF_SAFE_METHODS or request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Unauthenticated requests have no session to protect — let auth dependency handle 401
        if not request.cookies.get("access_token"):
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if (
            not cookie_token
            or not header_token
            or not secrets.compare_digest(cookie_token, header_token)
        ):
            return JSONResponse(
                {"success": False, "data": None, "message": "CSRF token 無效", "meta": None},
                status_code=403,
            )

        return await call_next(request)
