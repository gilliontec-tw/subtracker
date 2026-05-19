import logging

from domain.exceptions import ForbiddenException, NotAuthenticatedException, NotFoundException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotAuthenticatedException)
    async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
        return JSONResponse(
            status_code=401,
            content={"success": False, "data": None, "message": "請先登入", "meta": None},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(
            status_code=403,
            content={"success": False, "data": None, "message": "權限不足", "meta": None},
        )

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"success": False, "data": None, "message": "資源不存在", "meta": None},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "message": "伺服器錯誤，請稍後再試",
                "meta": None,
            },
        )
