from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.exception_handlers import register_exception_handlers
from api.middleware.csrf import CSRFMiddleware
from api.v1.routers.admin_settings import router as admin_settings_router
from api.v1.routers.asset_types import router as asset_types_router
from api.v1.routers.audit_log import router as audit_log_router
from api.v1.routers.auth import router as auth_router
from api.v1.routers.groups import router as groups_router
from api.v1.routers.invite import router as invite_router
from api.v1.routers.payments import router as payments_router
from api.v1.routers.subscriptions import router as subscriptions_router
from api.v1.routers.users import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SubTrack API",
        version="1.0.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )
    app.add_middleware(CSRFMiddleware)

    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(subscriptions_router)
    app.include_router(users_router)
    app.include_router(invite_router)
    app.include_router(audit_log_router)
    app.include_router(payments_router)
    app.include_router(admin_settings_router)
    app.include_router(asset_types_router)
    app.include_router(groups_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
