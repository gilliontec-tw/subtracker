import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.interfaces.web.routes.subscriptions import router as sub_router
from src.interfaces.web.routes.auth import router as auth_router
from src.interfaces.web.routes.admin import router as admin_router
from src.interfaces.web.routes.notifications import router as notif_router
from src.interfaces.web.dependencies import NotAuthenticatedException, ForbiddenException


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


app = FastAPI(title="SubTrack", lifespan=lifespan)
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
