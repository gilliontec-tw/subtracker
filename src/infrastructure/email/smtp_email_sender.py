import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from src.application.interfaces.email_sender import EmailSender

load_dotenv()


class SmtpEmailSender(EmailSender):
    def __init__(self) -> None:
        self._host = os.environ["SMTP_HOST"]
        self._port = int(os.environ["SMTP_PORT"])
        self._username = os.environ["SMTP_USERNAME"]
        self._password = os.environ["SMTP_PASSWORD"]
        self._from_address = os.environ["SMTP_FROM"]

    def send(self, to: str, subject: str, body: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = self._from_address
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL(self._host, self._port) as smtp:
            smtp.login(self._username, self._password)
            smtp.sendmail(self._from_address, to, msg.as_string())
