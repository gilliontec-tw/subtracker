from dataclasses import dataclass

from api.config import Settings
from cryptography.fernet import Fernet, InvalidToken
from domain.repositories.system_setting_repository import SystemSettingRepository

_ENV_FALLBACKS = {
    "smtp_host": lambda s: s.smtp_host or None,
    "smtp_port": lambda s: str(s.smtp_port),
    "smtp_user": lambda s: s.smtp_user or None,
    "smtp_password": lambda s: s.smtp_password or None,
    "smtp_from": lambda s: s.smtp_from or None,
    "smtp_sender_name": lambda s: s.smtp_sender_name or "SubTrack",
    "app_url": lambda s: s.app_url or None,
    "notification_cron_hour": lambda s: str(s.notification_cron_hour),
    "notification_cron_minute": lambda s: str(s.notification_cron_minute),
}

_SMTP_PASSWORD_KEY = "smtp_password"


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    from_addr: str
    sender_name: str


class SettingsService:
    def __init__(self, repo: SystemSettingRepository, env: Settings) -> None:
        self._repo = repo
        self._env = env
        self._fernet = (
            Fernet(env.settings_encryption_key.encode()) if env.settings_encryption_key else None
        )

    @property
    def encryption_key_configured(self) -> bool:
        return self._fernet is not None

    async def get(self, key: str) -> str | None:
        db_value = await self._repo.get(key)
        if db_value is not None and db_value != "":
            if key == _SMTP_PASSWORD_KEY:
                if self._fernet:
                    try:
                        return self._fernet.decrypt(db_value.encode()).decode()
                    except InvalidToken:
                        return None
                # No fernet — cannot decrypt; fall through to env fallback
            else:
                return db_value
        fallback_fn = _ENV_FALLBACKS.get(key)
        return fallback_fn(self._env) if fallback_fn else None

    async def set(self, key: str, value: str) -> None:
        if key == _SMTP_PASSWORD_KEY:
            if not self._fernet:
                raise ValueError("加密金鑰未設定（SETTINGS_ENCRYPTION_KEY），無法儲存密碼")
            value = self._fernet.encrypt(value.encode()).decode()
        await self._repo.set(key, value)

    async def get_smtp_config(self) -> SmtpConfig:
        return SmtpConfig(
            host=await self.get("smtp_host") or "",
            port=int(await self.get("smtp_port") or "587"),
            user=await self.get("smtp_user") or "",
            password=await self.get("smtp_password") or "",
            from_addr=await self.get("smtp_from") or "",
            sender_name=await self.get("smtp_sender_name") or "SubTrack",
        )
