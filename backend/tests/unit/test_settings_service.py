from unittest.mock import AsyncMock

import pytest
from api.config import Settings
from application.services.settings_service import SettingsService
from cryptography.fernet import Fernet


def make_env(settings_encryption_key: str = "", **kwargs) -> Settings:
    defaults = dict(
        smtp_host="env-host",
        smtp_port=587,
        smtp_user="env-user",
        smtp_password="env-pass",
        smtp_from="noreply@corp.com",
        smtp_sender_name="SubTrack",
        app_url="http://localhost",
        notification_cron_hour=8,
        notification_cron_minute=0,
        settings_encryption_key=settings_encryption_key,
        database_url="",
        redis_url="",
        jwt_access_secret_key="",
        jwt_refresh_secret_key="",
        jwt_access_expire_minutes=30,
        jwt_refresh_expire_days=7,
        cors_origins=[],
        app_env="development",
    )
    defaults.update(kwargs)
    return Settings.model_construct(**defaults)


@pytest.mark.asyncio
async def test_get_returns_db_value_when_present():
    repo = AsyncMock()
    repo.get.return_value = "smtp.gmail.com"
    svc = SettingsService(repo, make_env())
    assert await svc.get("smtp_host") == "smtp.gmail.com"


@pytest.mark.asyncio
async def test_get_falls_back_to_env_when_db_empty():
    repo = AsyncMock()
    repo.get.return_value = None
    svc = SettingsService(repo, make_env(smtp_host="env.smtp.com"))
    assert await svc.get("smtp_host") == "env.smtp.com"


@pytest.mark.asyncio
async def test_get_smtp_password_decrypts_db_value():
    key = Fernet.generate_key()
    encrypted = Fernet(key).encrypt(b"secret123").decode()
    repo = AsyncMock()
    repo.get.return_value = encrypted
    svc = SettingsService(repo, make_env(settings_encryption_key=key.decode()))
    assert await svc.get("smtp_password") == "secret123"


@pytest.mark.asyncio
async def test_get_smtp_password_falls_back_to_env_when_no_key():
    repo = AsyncMock()
    repo.get.return_value = None
    svc = SettingsService(repo, make_env(smtp_password="env-pass", settings_encryption_key=""))
    assert await svc.get("smtp_password") == "env-pass"


@pytest.mark.asyncio
async def test_set_smtp_password_raises_when_no_encryption_key():
    repo = AsyncMock()
    svc = SettingsService(repo, make_env(settings_encryption_key=""))
    with pytest.raises(ValueError, match="加密金鑰"):
        await svc.set("smtp_password", "secret")


@pytest.mark.asyncio
async def test_set_smtp_password_encrypts_before_saving():
    key = Fernet.generate_key()
    repo = AsyncMock()
    svc = SettingsService(repo, make_env(settings_encryption_key=key.decode()))
    await svc.set("smtp_password", "secret123")
    saved_value = repo.set.call_args[0][1]
    decrypted = Fernet(key).decrypt(saved_value.encode()).decode()
    assert decrypted == "secret123"


@pytest.mark.asyncio
async def test_set_non_password_key_saves_directly():
    repo = AsyncMock()
    svc = SettingsService(repo, make_env())
    await svc.set("smtp_host", "smtp.example.com")
    repo.set.assert_called_once_with("smtp_host", "smtp.example.com")


@pytest.mark.asyncio
async def test_encryption_key_configured_true_when_key_set():
    repo = AsyncMock()
    key = Fernet.generate_key().decode()
    svc = SettingsService(repo, make_env(settings_encryption_key=key))
    assert svc.encryption_key_configured is True


@pytest.mark.asyncio
async def test_encryption_key_configured_false_when_key_empty():
    repo = AsyncMock()
    svc = SettingsService(repo, make_env(settings_encryption_key=""))
    assert svc.encryption_key_configured is False


@pytest.mark.asyncio
async def test_get_smtp_config_returns_resolved_values():
    repo = AsyncMock()
    repo.get.return_value = None  # all keys fall back to env
    svc = SettingsService(
        repo,
        make_env(
            smtp_host="host",
            smtp_port=465,
            smtp_user="user",
            smtp_password="pass",
            smtp_from="from@x.com",
            smtp_sender_name="MyApp",
        ),
    )
    cfg = await svc.get_smtp_config()
    assert cfg.host == "host"
    assert cfg.port == 465
    assert cfg.sender_name == "MyApp"
