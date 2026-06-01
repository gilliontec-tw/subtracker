import uuid
from datetime import UTC, datetime, timedelta

from domain.repositories.user_repository import UserRepository

from application.interfaces.email_sender import EmailSender


class RequestPasswordResetUseCase:
    def __init__(
        self,
        repo: UserRepository,
        email_sender: EmailSender,
        app_url: str,
    ) -> None:
        self._repo = repo
        self._email_sender = email_sender
        self._app_url = app_url

    async def execute(self, email: str) -> None:
        user = await self._repo.get_by_email(email)
        if user is None or not user.is_active:
            return

        token = str(uuid.uuid4())
        user.invite_token = token
        user.invite_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        await self._repo.save(user)

        reset_link = f"{self._app_url}/reset-password/{token}"
        body = (
            f"您好 {user.display_name}，\n\n"
            f"請點擊以下連結重設您的密碼（1 小時內有效）：\n\n"
            f"{reset_link}\n\n"
            f"若您未申請重設密碼，請忽略此信。"
        )
        await self._email_sender.send(
            to=[user.email],
            subject="SubTrack 密碼重設",
            body=body,
        )
