from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings


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
        allow_headers=["*", "X-CSRF-Token"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
