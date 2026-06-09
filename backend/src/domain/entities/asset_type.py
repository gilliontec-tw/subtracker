from dataclasses import dataclass
from datetime import datetime


@dataclass
class AssetType:
    name: str
    created_by: int | None = None
    id: int | None = None
    created_at: datetime | None = None
