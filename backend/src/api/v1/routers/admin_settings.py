import logging
import smtplib

from application.services.settings_service import SettingsService
from domain.entities.user import User
from domain.exceptions import BadRequestException
from fastapi import APIRouter, Depends
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender

from api.dependencies import get_settings_service, require_admin
from api.v1.schemas.admin_settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    TestEmailRequest,
)
from api.v1.schemas.base import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin-settings"])


@router.get("", response_model=ApiResponse[SettingsResponse])
async def get_settings(
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[SettingsResponse]:
    s = await svc.get_all_settings()
    return ApiResponse.ok(
        data=SettingsResponse(
            smtp_host=s.get("smtp_host") or "",
            smtp_port=int(s.get("smtp_port") or "587"),
            smtp_user=s.get("smtp_user") or "",
            smtp_password_set=bool(s.get("smtp_password")),
            smtp_from=s.get("smtp_from") or "",
            smtp_sender_name=s.get("smtp_sender_name") or "SubTrack",
            app_url=s.get("app_url") or "",
            notification_cron_hour=int(s.get("notification_cron_hour") or "8"),
            notification_cron_minute=int(s.get("notification_cron_minute") or "0"),
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


@router.post("/test-email", response_model=ApiResponse[None])
async def test_email(
    body: TestEmailRequest,
    current_user: User = Depends(require_admin),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[None]:
    password = body.smtp_password
    if not password:
        password = await svc.get("smtp_password") or ""

    sender = SmtpEmailSender(
        host=body.smtp_host,
        port=body.smtp_port,
        username=body.smtp_user,
        password=password,
        from_addr=body.smtp_from,
        sender_name=body.smtp_sender_name,
    )
    try:
        await sender.send(
            to=[current_user.email],
            subject="SubTrack 郵件設定測試",
            body=(
                "這是一封測試信，確認您的 SMTP 設定正確。\n\n"
                "如果您收到這封信，表示 SMTP 設定無誤。"
            ),
        )
    except (smtplib.SMTPException, OSError) as e:
        logger.warning("SMTP test failed: %s", e)
        raise BadRequestException("寄信失敗，請確認 SMTP 設定是否正確")

    return ApiResponse.ok(message=f"測試信已寄至 {current_user.email}")
