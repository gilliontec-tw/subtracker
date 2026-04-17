from fastapi import FastAPI
from src.interfaces.web.routes.subscriptions import router


def create_app() -> FastAPI:
    app = FastAPI(title="SaaS Subscription Tracker")
    app.include_router(router)
    return app


app = create_app()
