# Testing Patterns

**Analysis Date:** 2026-05-06

## Test Framework

**Runner:**
- pytest
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)

**Configuration:**
```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```
This adds `src/` to `sys.path` so all tests import via `src.*` (e.g., `from src.domain.entities.subscription import Subscription`).

**Assertion Library:**
- pytest built-in assertions (no extra library)

**Run Commands:**
```bash
pytest                                                      # Run all tests
pytest tests/unit/test_create_subscription.py              # Run a single file
pytest tests/unit/test_create_subscription.py::test_name   # Run a single test
```
No coverage config is defined. No watch mode configured.

## Test File Organization

**Location:**
- All tests in `tests/unit/` — co-located under `tests/`, not next to source files
- Auth-specific tests in `tests/unit/auth/` subdirectory

**Directory Layout:**
```
tests/
├── __init__.py
├── conftest.py                          # Shared fixtures (mock_repo, mock_email_sender, sample_subscription)
└── unit/
    ├── __init__.py
    ├── auth/
    │   ├── __init__.py
    │   ├── test_change_password.py
    │   ├── test_login_user.py
    │   ├── test_register_user.py
    │   ├── test_update_user_permissions.py
    │   └── test_user_entity.py
    ├── test_check_and_notify.py
    ├── test_create_subscription.py
    ├── test_delete_subscription.py
    ├── test_get_subscription.py
    ├── test_list_subscriptions.py
    ├── test_subscription_entity.py
    └── test_update_subscription.py
```

**File Naming:**
- `test_<use_case_or_entity>.py` — mirrors the source file being tested
- One test file per use case or entity

## Testing Approach

**Scope:** 100% unit tests. No integration tests, no end-to-end tests, no database tests.

**Mocking Strategy:** All external dependencies (repositories, email sender) are replaced with `MagicMock(spec=Interface)`. This means:
- Tests never touch the database
- Tests never send SMTP email
- Tests run in-memory only

**What is tested:**
- All use cases (create, update, delete, list, get subscription; login, register, change password, update permissions)
- Domain entity behavior (`Subscription.should_notify_today`, status/field defaults)
- `CheckAndNotifyUseCase` email grouping/deduplication logic

**What is NOT tested:**
- `Sql*Repository` classes — no database integration tests exist
- FastAPI routes — no HTTP-level tests (no `TestClient` usage)
- Jinja2 templates — no rendering tests
- `SmtpEmailSender` — no SMTP integration tests
- `src/interfaces/web/session.py` — cookie signing untested
- `scripts/run_notifications.py` entry point — untested
- `src/interfaces/web/routes/notifications.py` — untested
- `SqlConfigOptionRepository` — untested
- `SqlAuditLogRepository` — untested

## Test Fixtures and Helpers

**Shared fixtures in `tests/conftest.py`** (available to all tests automatically):

```python
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
        notification_emails="alice@company.com",
        notification_days=NotificationDays.SEVEN,
    )
```

**Local fixtures in auth test files:** Auth test files define their own `repo` fixture locally (separate from `mock_repo` in conftest):
```python
# tests/unit/auth/test_register_user.py
@pytest.fixture
def repo():
    mock = MagicMock()
    mock.get_by_email.return_value = None
    mock.add.side_effect = lambda u: User(id=1, email=u.email, ...)
    return mock
```

**Local helper functions (`make_sub`):** Several test files define a module-level `make_sub()` factory to reduce repetition:
```python
def make_sub(expiry_date: date, notification_days: NotificationDays) -> Subscription:
    return Subscription(
        service_name="GitHub",
        login_account="it@company.com",
        expiry_date=expiry_date,
        notification_emails="alice@company.com",
        notification_days=notification_days,
    )
```
Used in `test_subscription_entity.py` and `test_check_and_notify.py`.

Private helper functions prefixed `_make_*` used in auth tests:
```python
def _make_user(hashed_pw: str, is_active: bool = True) -> User:
    ...
```

## Test Structure

**Suite Organization:** No `class`-based test grouping — all tests are top-level functions. No `describe` blocks.

**Pattern:**
```python
def test_<behavior_description>(mock_repo, sample_subscription):
    # Arrange
    mock_repo.add.return_value = sample_subscription

    # Act
    uc = CreateSubscriptionUseCase(mock_repo)
    result = uc.execute(service_name="GitHub", ...)

    # Assert
    mock_repo.add.assert_called_once()
    assert result is sample_subscription
```

**Parameterized tests:** Used selectively for exhaustive enum coverage:
```python
def test_all_threshold_values_trigger_correctly():
    thresholds = [
        (NotificationDays.THREE, 3),
        (NotificationDays.SEVEN, 7),
        ...
    ]
    for enum_val, days in thresholds:
        ...
        assert sub.should_notify_today(trigger) is True, f"Failed for {days} days"
```
Note: uses a `for` loop rather than `@pytest.mark.parametrize`.

## Mocking

**Framework:** `unittest.mock.MagicMock`

**Typical Pattern:**
```python
from unittest.mock import MagicMock
from src.domain.repositories.subscription_repository import SubscriptionRepository

mock_repo = MagicMock(spec=SubscriptionRepository)
mock_repo.get_by_id.return_value = sample_subscription
mock_repo.update.return_value = sample_subscription
```

**Exception simulation:**
```python
mock_email_sender.send.side_effect = Exception("SMTP error")
```

**Call verification:**
```python
mock_repo.add.assert_called_once()
mock_repo.deactivate.assert_called_once_with(1)
mock_email_sender.send.assert_not_called()
assert mock_email_sender.send.call_count == 1
```

**Inspecting what was passed to mock:**
```python
added_entity: Subscription = mock_repo.add.call_args[0][0]
assert added_entity.service_name == "GitHub"

call_kwargs = mock_email_sender.send.call_args[1]
assert call_kwargs["to"] == "admin@co.com"
assert "1 筆" in call_kwargs["subject"]
```

**What to mock:** Repository interfaces (`SubscriptionRepository`, `UserRepository`) and `EmailSender`. Always use `spec=` to constrain the mock to the real interface.

**What NOT to mock:** Domain entities (`Subscription`, `User`) — these are plain dataclasses and tested directly.

## Test Data Conventions

**Realistic Chinese strings used in tests** to verify multi-byte handling:
```python
owner_name="李設計", category="設計工具", department="設計"
owner_name="陳小明", category="生產力工具", department="全公司"
payment_account="公司美金卡末4碼1234"
```

**Expiry/notification dates chosen for clarity:** Comments explain the arithmetic:
```python
# expiry 2026-05-08, notify 7 days before → trigger on 2026-05-01
sub = make_sub(date(2026, 5, 8), NotificationDays.SEVEN)
assert sub.should_notify_today(date(2026, 5, 1)) is True
```

**Inline zh-TW comments** on tests that verify Chinese email content:
```python
# 單筆到期 → 彙總信主旨含「1 筆」
# 只有 1 筆到期 → 只寄 1 封彙總信
```

## Coverage Gaps

**High Priority — No tests exist for:**

| Area | Files | Risk |
|------|-------|------|
| SQL repositories | `src/infrastructure/database/sql_*.py` | Silent mapping errors when new fields added |
| FastAPI routes | `src/interfaces/web/routes/*.py` | Form parsing, redirect logic, auth guard enforcement |
| Session cookie layer | `src/interfaces/web/session.py` | Auth bypass if cookie signing breaks |
| Notification route | `src/interfaces/web/routes/notifications.py` | Entirely untested |
| Audit log repository | `src/infrastructure/database/sql_audit_log_repository.py` | Audit trail integrity |
| Config option repository | `src/infrastructure/database/sql_config_option_repository.py` | Settings management untested |
| SMTP email sender | `src/infrastructure/email/smtp_email_sender.py` | Email delivery silently fails |
| Notification script | `scripts/run_notifications.py` | Daily job logic untested |

**Medium Priority:**

| Area | Gap |
|------|-----|
| `bulk_renew` route | Billing period calculation (`_add_billing_period`) has no unit test |
| CSV export | `_csv_safe` helper and full export output untested |
| Dashboard cost calculations | `annual_cost` inner function duplicated in `dashboard` and `reports` — untested |
| `list_subscriptions` | Only one trivial delegation test; filtering/sorting logic (in routes) untested |

**Low Priority:**
- `auth/change_password` logic (the use case file has a test; edge cases minimal)
- `get_subscription` delegates trivially — single test is sufficient

---

*Testing analysis: 2026-05-06*
