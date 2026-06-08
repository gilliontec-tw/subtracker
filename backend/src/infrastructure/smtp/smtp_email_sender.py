import asyncio
import smtplib
from email.mime.text import MIMEText

from application.interfaces.email_sender import EmailSender


class SmtpEmailSender(EmailSender):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        sender_name: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = f"{sender_name} <{from_addr}>" if sender_name else from_addr

    async def send(self, to: list[str], subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_sync, to, subject, body)

    def _send_sync(self, to: list[str], subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = ", ".join(to)
        with smtplib.SMTP(self._host, self._port) as server:
            server.starttls()
            server.login(self._username, self._password)
            server.sendmail(self._from, to, msg.as_string())
