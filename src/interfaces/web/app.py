from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from src.interfaces.web.routes.subscriptions import router as sub_router
from src.interfaces.web.routes.auth import router as auth_router
from src.interfaces.web.routes.admin import router as admin_router
from src.interfaces.web.dependencies import NotAuthenticatedException, ForbiddenException

app = FastAPI(title="SaaS Subscription Tracker")

app.include_router(auth_router)
app.include_router(sub_router)
app.include_router(admin_router)


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
