from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    message: str = ""
    meta: dict[str, Any] | None = None

    @classmethod
    def ok(cls, data: T | None = None, message: str = "", meta: dict | None = None) -> "ApiResponse[T]":
        return cls(success=True, data=data, message=message, meta=meta)

    @classmethod
    def fail(cls, message: str, data: T | None = None) -> "ApiResponse[T]":
        return cls(success=False, data=data, message=message)


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
