from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from application.use_cases.list_audit_log import ListAuditLogUseCase
from domain.entities.audit_entry import AuditEntry


def make_entry(**kwargs) -> AuditEntry:
    defaults = dict(
        user_id=1,
        action="create",
        resource_type="subscription",
        resource_id=1,
        details={"user_email": "a@corp.com", "service_name": "GitHub"},
    )
    defaults.update(kwargs)
    return AuditEntry(**defaults)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.mark.asyncio
async def test_returns_entries_from_repo(repo):
    repo.list_by_date_range = AsyncMock(return_value=[make_entry()])
    use_case = ListAuditLogUseCase(repo)
    result = await use_case.execute(from_date=date(2026, 5, 1), to_date=date(2026, 5, 29))
    assert len(result) == 1
    repo.list_by_date_range.assert_called_once_with(date(2026, 5, 1), date(2026, 5, 29))


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_entries(repo):
    repo.list_by_date_range = AsyncMock(return_value=[])
    use_case = ListAuditLogUseCase(repo)
    result = await use_case.execute(from_date=date(2026, 5, 1), to_date=date(2026, 5, 29))
    assert result == []
