from unittest.mock import MagicMock, patch

import pytest
from infrastructure.smtp.smtp_email_sender import SmtpEmailSender


@pytest.fixture
def sender():
    return SmtpEmailSender(
        host="smtp.test.com",
        port=587,
        username="user@test.com",
        password="secret",
        from_addr="user@test.com",
    )


@pytest.mark.asyncio
async def test_connects_to_configured_host_and_port(sender):
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        await sender.send(to=["dest@test.com"], subject="Test", body="Hello")

        mock_smtp_class.assert_called_once_with("smtp.test.com", 587)


@pytest.mark.asyncio
async def test_uses_starttls_and_login(sender):
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        await sender.send(to=["dest@test.com"], subject="Test", body="Hello")

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "secret")


@pytest.mark.asyncio
async def test_sends_to_all_recipients(sender):
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        await sender.send(
            to=["a@test.com", "b@test.com"],
            subject="Test",
            body="Hello",
        )

        call_args = mock_server.sendmail.call_args
        assert call_args[0][1] == ["a@test.com", "b@test.com"]
