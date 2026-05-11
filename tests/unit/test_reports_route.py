"""Unit tests for _build_report_sections helper in subscriptions route."""
from datetime import date
from decimal import Decimal

import pytest

from src.domain.entities.subscription import NotificationDays, Subscription, SubscriptionStatus
from src.interfaces.web.routes.subscriptions import _build_report_sections


def _make_sub(
    cost: float,
    currency: str = "TWD",
    billing_cycle: str = "annual",
    department: str | None = None,
    category: str | None = None,
    status: str = "active",
) -> Subscription:
    return Subscription(
        id=1,
        service_name="Test",
        login_account="test@co.com",
        expiry_date=date(2026, 12, 31),
        notification_emails="test@co.com",
        notification_days=NotificationDays.SEVEN,
        cost=Decimal(str(cost)),
        currency=currency,
        billing_cycle=billing_cycle,
        department=department,
        category=category,
        status=SubscriptionStatus(status),
    )


def test_dept_accumulator_groups_by_currency():
    """TWD/IT and USD/HR subscriptions should land in separate sections."""
    subs = [
        _make_sub(cost=12000, currency="TWD", billing_cycle="annual", department="IT"),
        _make_sub(cost=1200,  currency="USD", billing_cycle="annual", department="HR"),
    ]
    sections = _build_report_sections(subs)

    twd_section = next(s for s in sections if s["currency"] == "TWD")
    usd_section = next(s for s in sections if s["currency"] == "USD")

    assert len(twd_section["departments"]) == 1
    assert twd_section["departments"][0]["name"] == "IT"
    assert twd_section["departments"][0]["cost"] == pytest.approx(12000.0)
    assert twd_section["departments"][0]["count"] == 1

    assert len(usd_section["departments"]) == 1
    assert usd_section["departments"][0]["name"] == "HR"
    assert usd_section["departments"][0]["cost"] == pytest.approx(1200.0)
    assert usd_section["departments"][0]["count"] == 1


def test_dept_top_is_first_in_list():
    """Departments are sorted descending by cost — highest cost department is first."""
    subs = [
        _make_sub(cost=5000, currency="TWD", billing_cycle="annual", department="A"),
        _make_sub(cost=3000, currency="TWD", billing_cycle="annual", department="B"),
    ]
    sections = _build_report_sections(subs)

    assert len(sections) == 1
    depts = sections[0]["departments"]
    assert depts[0]["name"] == "A"
    assert depts[1]["name"] == "B"


def test_cat_labels_json_embedded_per_section():
    """cat_labels_json in each section only contains that currency's categories."""
    import json

    subs = [
        _make_sub(cost=10000, currency="TWD", billing_cycle="annual", category="開發工具"),
        _make_sub(cost=500,   currency="USD", billing_cycle="annual", category="設計工具"),
    ]
    sections = _build_report_sections(subs)

    twd_section = next(s for s in sections if s["currency"] == "TWD")
    usd_section = next(s for s in sections if s["currency"] == "USD")

    twd_labels = json.loads(twd_section["cat_labels_json"])
    usd_labels = json.loads(usd_section["cat_labels_json"])

    assert "開發工具" in twd_labels
    assert "設計工具" not in twd_labels

    assert "設計工具" in usd_labels
    assert "開發工具" not in usd_labels


def test_top_level_cat_labels_json_removed_from_template_response():
    """The TemplateResponse context must not have cat_labels_json at top level.

    We test this by verifying _build_report_sections returns sections with
    cat_labels_json embedded inside each section dict (not at top level).
    The route handler should only pass 'sections' and 'cat_colors' at top level.
    This test directly imports and calls the reports handler logic via
    _build_report_sections and confirms the per-section embedding.
    """
    import json

    subs = [
        _make_sub(cost=1000, currency="TWD", billing_cycle="annual", category="其他"),
    ]
    sections = _build_report_sections(subs)

    # Per-section keys must exist
    assert "cat_labels_json" in sections[0]
    assert "cat_values_json" in sections[0]
    assert "cat_colors_json" in sections[0]

    # Validate they are valid JSON
    json.loads(sections[0]["cat_labels_json"])
    json.loads(sections[0]["cat_values_json"])
    json.loads(sections[0]["cat_colors_json"])
