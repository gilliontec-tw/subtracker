from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password_set: bool
    smtp_from: str
    smtp_sender_name: str
    app_url: str
    notification_cron_hour: int
    notification_cron_minute: int
    encryption_key_configured: bool


class SettingsUpdateRequest(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_sender_name: str | None = None
    app_url: str | None = None
    notification_cron_hour: int | None = Field(default=None, ge=0, le=23)
    notification_cron_minute: int | None = Field(default=None, ge=0, le=59)


class TestEmailRequest(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str | None = None
    smtp_from: str
    smtp_sender_name: str = "SubTrack"
