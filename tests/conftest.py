from datetime import date
from unittest.mock import MagicMock
import pytest
from src.domain.entities.subscription import Subscription, NotificationDays
from src.domain.repositories.subscription_repository import SubscriptionRepository
from src.application.interfaces.email_sender import EmailSender


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock(spec=SubscriptionRepository)


@pytest.fixture
def mock_email_sender() -> MagicMock:
    return MagicMock(spec=EmailSender)


@pytest.fixture
def sample_subscription() -> Subscription:
    return Subscription(
        id=1,
        service_name="GitHub",
        login_account="it@company.com",
        expiry_date=date(2026, 12, 31),
        responsible_person_email="alice@company.com",
        notification_days=NotificationDays.SEVEN,
    )
