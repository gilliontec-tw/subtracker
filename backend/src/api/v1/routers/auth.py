import secrets
from datetime import UTC, datetime

import redis.asyncio as aioredis
from application.services.settings_service import SettingsService
from application.use_cases.change_password import ChangePasswordUseCase
from application.use_cases.direct_password_reset import DirectPasswordResetUseCase
from application.use_cases.request_password_reset import RequestPasswordResetUseCase
from domain.entities.user import User
from domain.exceptions import NotAuthenticatedException
from fastapi import APIRouter, Cookie, Depends, Request, Response
from infrastructure.auth.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from infrastructure.auth.password import verify_password
from infrastructure.cache.redis_client import get_redis
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.session import get_db
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.dependencies import get_current_user, get_settings_service
from api.v1.schemas.auth import (
    ChangePasswordRequest,
    DirectPasswordResetRequest,
    ForgotPasswordRequest,
    LoginRequest,
    UserResponse,
)
from api.v1.schemas.base import ApiResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_FAIL_TTL = 60  # seconds window for login failure rate limit
_MAX_FAILS = 5


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str, csrf_token: str
) -> None:
    is_prod = settings.app_env == "production"
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_access_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[UserResponse]:
    ip = request.client.host if request.client else "unknown"
    fail_key = f"login_fail:{ip}"

    fail_count = await redis.get(fail_key)
    if fail_count and int(fail_count) >= _MAX_FAILS:
        return ApiResponse.fail("登入嘗試次數過多，請一分鐘後再試")  # type: ignore[return-value]

    repo = SqlUserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        await redis.incr(fail_key)
        await redis.expire(fail_key, _FAIL_TTL)
        raise NotAuthenticatedException()

    await redis.delete(fail_key)

    access_token = create_access_token(user.id, user.role)
    refresh_token, _ = create_refresh_token(user.id)
    csrf_token = secrets.token_urlsafe(32)

    _set_auth_cookies(response, access_token, refresh_token, csrf_token)

    return ApiResponse.ok(
        data=UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            can_create=user.can_create,
            can_update=user.can_update,
            can_delete=user.can_delete,
        )
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[None]:
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = exp - int(datetime.now(UTC).timestamp())
                if ttl > 0:
                    await redis.set(f"blacklist:{jti}", "1", ex=ttl)
        except Exception:
            pass  # invalid token — still clear cookies

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")
    return ApiResponse.ok(message="已登出")


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[None]:
    if not refresh_token:
        raise NotAuthenticatedException()
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise NotAuthenticatedException()

    jti = payload.get("jti")
    if jti and await redis.get(f"blacklist:{jti}"):
        raise NotAuthenticatedException()

    user_id = int(payload["sub"])
    repo = SqlUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise NotAuthenticatedException()

    new_access = create_access_token(user.id, user.role)
    is_prod = settings.app_env == "production"
    response.set_cookie(
        "access_token",
        new_access,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.jwt_access_expire_minutes * 60,
    )
    return ApiResponse.ok(message="Token 已更新")


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    svc: SettingsService = Depends(get_settings_service),
) -> ApiResponse[None]:
    repo = SqlUserRepository(db)
    smtp_config = await svc.get_smtp_config()
    email_sender = SmtpEmailSender(
        host=smtp_config.host,
        port=smtp_config.port,
        username=smtp_config.user,
        password=smtp_config.password,
        from_addr=smtp_config.from_addr,
        sender_name=smtp_config.sender_name,
    )
    app_url = await svc.get("app_url") or settings.app_url
    use_case = RequestPasswordResetUseCase(repo, email_sender, app_url)
    await use_case.execute(email=str(body.email))
    return ApiResponse.ok(message="若此 Email 已註冊，重設連結已寄出，請查收信箱")


@router.post("/reset-password-direct")
async def reset_password_direct(
    body: DirectPasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> ApiResponse[None]:
    ip = request.client.host if request.client else "unknown"
    reset_key = f"reset_fail:{ip}"
    fail_count = await redis.get(reset_key)
    if fail_count and int(fail_count) >= _MAX_FAILS:
        return ApiResponse.fail("嘗試次數過多，請一分鐘後再試")  # type: ignore[return-value]

    repo = SqlUserRepository(db)
    use_case = DirectPasswordResetUseCase(repo)
    try:
        await use_case.execute(email=body.email, new_password=body.new_password)
    except Exception:
        await redis.incr(reset_key)
        await redis.expire(reset_key, _FAIL_TTL)
        raise

    await redis.delete(reset_key)
    return ApiResponse.ok(message="密碼已重設")


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    repo = SqlUserRepository(db)
    use_case = ChangePasswordUseCase(repo)
    await use_case.execute(current_user, body.current_password, body.new_password)
    return ApiResponse.ok(message="密碼已更新")


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ApiResponse.ok(
        data=UserResponse(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            role=current_user.role,
            can_create=current_user.can_create,
            can_update=current_user.can_update,
            can_delete=current_user.can_delete,
        )
    )
