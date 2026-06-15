from application.use_cases.create_asset_type import CreateAssetTypeUseCase
from application.use_cases.delete_asset_type import DeleteAssetTypeUseCase
from application.use_cases.list_asset_types import ListAssetTypesUseCase
from application.use_cases.update_asset_type import UpdateAssetTypeUseCase
from domain.entities.user import User
from fastapi import APIRouter, Depends
from infrastructure.database.repositories.asset_type_repository import SqlAssetTypeRepository
from infrastructure.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, require_admin
from api.v1.schemas.asset_type import AssetTypeCreate, AssetTypeResponse, AssetTypeUpdate
from api.v1.schemas.base import ApiResponse

router = APIRouter(prefix="/api/v1/asset-types", tags=["asset-types"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> SqlAssetTypeRepository:
    return SqlAssetTypeRepository(db)


@router.get("", response_model=ApiResponse[list[AssetTypeResponse]])
async def list_asset_types(
    _: User = Depends(get_current_user),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[list[AssetTypeResponse]]:
    items = await ListAssetTypesUseCase(repo).execute()
    return ApiResponse.ok(data=[AssetTypeResponse(**vars(t)) for t in items])


@router.post("", response_model=ApiResponse[AssetTypeResponse], status_code=201)
async def create_asset_type(
    body: AssetTypeCreate,
    current_user: User = Depends(get_current_user),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[AssetTypeResponse]:
    result = await CreateAssetTypeUseCase(repo).execute(name=body.name, created_by=current_user.id)
    return ApiResponse.ok(data=AssetTypeResponse(**vars(result)))


@router.patch("/{asset_type_id}", response_model=ApiResponse[AssetTypeResponse])
async def update_asset_type(
    asset_type_id: int,
    body: AssetTypeUpdate,
    _: User = Depends(require_admin),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[AssetTypeResponse]:
    result = await UpdateAssetTypeUseCase(repo).execute(asset_type_id=asset_type_id, name=body.name)
    return ApiResponse.ok(data=AssetTypeResponse(**vars(result)))


@router.delete("/{asset_type_id}", response_model=ApiResponse[None])
async def delete_asset_type(
    asset_type_id: int,
    _: User = Depends(require_admin),
    repo: SqlAssetTypeRepository = Depends(_get_repo),
) -> ApiResponse[None]:
    await DeleteAssetTypeUseCase(repo).execute(asset_type_id=asset_type_id)
    return ApiResponse.ok(message="已刪除")
