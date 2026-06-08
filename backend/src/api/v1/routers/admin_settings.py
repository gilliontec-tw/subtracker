from application.services.settings_service import SettingsService
from domain.entities.user import User
from domain.exceptions import BadRequestException
from fastapi import APIRouter, Depends

from api.dependencies import get_settings_service, require_admin
from api.v1.schemas.admin_settings import SettingsResponse, SettingsUpdateRequest
from api.v1.schemas.base import ApiResponse

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin-settings"])


@router.get("", response_model=ApiResponse[SettingsResponse])
async def get_settings(
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[SettingsResponse]:
    password = await svc.get("smtp_password")
    return ApiResponse.ok(
        data=SettingsResponse(
            smtp_host=await svc.get("smtp_host") or "",
            smtp_port=int(await svc.get("smtp_port") or "587"),
            smtp_user=await svc.get("smtp_user") or "",
            smtp_password_set=bool(password),
            smtp_from=await svc.get("smtp_from") or "",
            smtp_sender_name=await svc.get("smtp_sender_name") or "SubTrack",
            app_url=await svc.get("app_url") or "",
            notification_cron_hour=int(await svc.get("notification_cron_hour") or "8"),
            notification_cron_minute=int(await svc.get("notification_cron_minute") or "0"),
            encryption_key_configured=svc.encryption_key_configured,
        )
    )


@router.put("", response_model=ApiResponse[None])
async def update_settings(
    body: SettingsUpdateRequest,
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[None]:
    if body.smtp_password:
        if not svc.encryption_key_configured:
            raise BadRequestException("加密金鑰未設定（SETTINGS_ENCRYPTION_KEY），無法儲存密碼")
        await svc.set("smtp_password", body.smtp_password)

    field_map: dict[str, str | None] = {
        "smtp_host": body.smtp_host,
        "smtp_port": str(body.smtp_port) if body.smtp_port is not None else None,
        "smtp_user": body.smtp_user,
        "smtp_from": body.smtp_from,
        "smtp_sender_name": body.smtp_sender_name,
        "app_url": body.app_url,
        "notification_cron_hour": str(body.notification_cron_hour)
        if body.notification_cron_hour is not None
        else None,
        "notification_cron_minute": str(body.notification_cron_minute)
        if body.notification_cron_minute is not None
        else None,
    }
    for key, value in field_map.items():
        if value is not None:
            await svc.set(key, value)

    return ApiResponse.ok(message="設定已儲存")
