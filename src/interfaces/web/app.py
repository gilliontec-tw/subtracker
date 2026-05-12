import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.interfaces.web.routes.subscriptions import router as sub_router
from src.interfaces.web.routes.auth import router as auth_router
from src.interfaces.web.routes.admin import router as admin_router
from src.interfaces.web.routes.notifications import router as notif_router
from src.interfaces.web.dependencies import NotAuthenticatedException, ForbiddenException
from src.interfaces.web.csrf import (
    generate_csrf_token, set_csrf_cookie,
    get_cookie_token, CSRF_SAFE_METHODS, verify_csrf
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
        }
        # Request-scoped fields injected via record.__dict__ by the middleware
        for field in ("method", "path", "status_code", "duration_ms"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        else:
            payload["message"] = record.getMessage()
        return json.dumps(payload, ensure_ascii=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SEC-02: configure JSON structured logging to stdout first so startup errors are JSON too
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    # SEC-01: reject insecure or missing SECRET_KEY (per D-08)
    _secret = os.getenv("SECRET_KEY", "")
    _dev_default = "dev-secret-key-change-in-production"
    if not _secret or _secret == _dev_default:
        raise RuntimeError(
            "SECRET_KEY is not set or still equals the dev default. "
            "Set a strong SECRET_KEY in your .env file before starting the app."
        )

    yield


app = FastAPI(title="SubTrack", lifespan=lifespan, dependencies=[Depends(verify_csrf)])
app.mount("/static", StaticFiles(directory="src/interfaces/web/static"), name="static")

app.include_router(auth_router)
app.include_router(sub_router)
app.include_router(admin_router)
app.include_router(notif_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000)
    logger = logging.getLogger("subtrack.http")
    logger.info(
        "",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# ── SEC-H1: CSRF 防禦 Middleware ─────────────────────────────────────────────
# 對所有狀態變更請求（POST/PUT/DELETE/PATCH）驗證 Double Submit Cookie token。
# 通過驗證後的回應以及 GET 回應都會更新/注入 CSRF token cookie。
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    # 靜態資源不需要 CSRF 處理
    if request.url.path.startswith("/static/"):
        return await call_next(request)

    # 狀態變更請求：不在此處驗證 POST body，以免 BaseHTTPMiddleware 消耗 body stream
    # 驗證交由 Depends(verify_csrf) 處理

    # 為請求產生或沿用現有 CSRF token，存入 request.state 供模板使用
    existing_token = get_cookie_token(request)
    csrf_token = existing_token or generate_csrf_token()
    request.state.csrf_token = csrf_token

    response = await call_next(request)

    # 若 token 是新生成的（或舊 token 不存在），寫入 cookie
    if not existing_token:
        set_csrf_cookie(response, csrf_token)

    return response


# ── SEC-H2: HTTP Security Headers Middleware ──────────────────────────────────
# 在每個回應注入標準安全標頭。
# CSP 說明：
#   - default-src 'self'          → 預設僅允許同源
#   - script-src  'self' 'unsafe-inline' cdn.jsdelivr.net  → Chart.js CDN + inline <script>
#   - style-src   'self' 'unsafe-inline' fonts.googleapis.com  → Google Fonts + inline style
#   - font-src    'self' fonts.gstatic.com                      → Google Fonts 字型檔
#   - img-src     'self' data:                                   → base64 inline 圖片
#   - connect-src 'self'                                         → XHR/fetch 僅限同源
#   - frame-ancestors 'none'                                     → 防止 Clickjacking
# 若未來移除 inline script，可將 'unsafe-inline' 替換為 nonce。
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
    "font-src 'self' fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"]   = _CSP
    response.headers["X-Content-Type-Options"]     = "nosniff"
    response.headers["X-Frame-Options"]            = "DENY"
    response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]         = "geolocation=(), microphone=(), camera=()"
    # HSTS 僅在 HTTPS 環境啟用（COOKIE_SECURE=true 即代表 HTTPS 環境）
    if os.getenv("COOKIE_SECURE", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse("/login", status_code=302)


@app.exception_handler(ForbiddenException)
async def forbidden_handler(request: Request, exc: ForbiddenException):
    return HTMLResponse(
        "<h3 style='color:#c62828;padding:2rem;'>403 — 您沒有執行此操作的權限。</h3>"
        "<p style='padding:0 2rem;'><a href='/'>← 返回首頁</a></p>",
        status_code=403,
    )
