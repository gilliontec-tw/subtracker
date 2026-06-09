from datetime import datetime

from pydantic import BaseModel, Field


class AssetTypeResponse(BaseModel):
    id: int
    name: str
    created_at: datetime | None


class AssetTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class AssetTypeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
