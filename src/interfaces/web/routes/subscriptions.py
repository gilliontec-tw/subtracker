import calendar
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import csv
import io
import json
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from src.domain.entities.audit_entry import AuditEntry
from src.domain.entities.subscription import NotificationDays, SubscriptionStatus
from src.interfaces.web.constants import NOTIFICATION_OPTIONS
from src.interfaces.web.dependencies import (
    get_create_uc, get_delete_uc, get_list_uc, get_single_uc, get_update_uc,
    get_current_user, require_create, require_update, require_delete,
    get_audit_log_repo, get_config_repo, templates,
)

router = APIRouter()

STATUS_OPTIONS = [
    ("active",    "使用中"),
    ("renewed",   "已續約"),
    ("cancelled", "已取消"),
    ("suspended", "暫停"),
]

CURRENCY_OPTIONS = ["TWD", "USD", "EUR", "JPY"]


BILLING_CYCLE_OPTIONS = [
    ("monthly",     "月付"),
    ("quarterly",   "季付"),
    ("semi_annual", "半年付"),
    ("annual",      "年付"),
    ("biennial",    "兩年付"),
]


@router.get("/dashboard")
def dashboard(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    today = date.today()

    active_subs = [s for s in subscriptions if s.status.value in ("active", "renewed")]

    # Per-currency annual cost breakdown
    cost_by_currency: dict[str, float] = defaultdict(float)
    for s in active_subs:
        cur = s.currency or "TWD"
        cost_by_currency[cur] += s.annual_cost()
    cost_summary = sorted(
        [{"currency": c, "annual": v, "monthly": v / 12} for c, v in cost_by_currency.items()],
        key=lambda x: -x["annual"],
    )

    total_annual_cost = sum(s.annual_cost() for s in active_subs)
    total_monthly_cost = total_annual_cost / 12

    upcoming_30 = [s for s in active_subs if 0 <= (s.expiry_date - today).days <= 30]
    upcoming_90 = sorted(
        [s for s in active_subs if 0 <= (s.expiry_date - today).days <= 90],
        key=lambda s: s.expiry_date,
    )
    no_owner = [s for s in active_subs if not s.owner_name]

    trial_expiring = [
        s for s in active_subs
        if s.trial_end_date and 0 <= (s.trial_end_date - today).days <= 14
    ]

    # ── Donut chart: cost by category ────────────────────────────────────
    cat_costs: dict[str, float] = defaultdict(float)
    for s in active_subs:
        cat = s.category or "未分類"
        cat_costs[cat] += s.annual_cost()
    chart_cat_labels = json.dumps(list(cat_costs.keys()), ensure_ascii=False)
    chart_cat_values = json.dumps([round(v, 2) for v in cat_costs.values()])

    # ── Bar chart: annual-sub renewals by month (next 12 months) ─────────
    month_labels_raw = []
    month_data: dict[str, float] = defaultdict(float)
    for i in range(12):
        m = (today.month - 1 + i) % 12 + 1
        y = today.year + (today.month - 1 + i) // 12
        key = f"{y}-{m:02d}"
        month_labels_raw.append(key)
        month_data[key] = 0.0

    for s in active_subs:
        if (s.billing_cycle or "").lower() == "monthly":
            continue  # skip monthly; they renew every month
        exp = s.expiry_date
        key = f"{exp.year}-{exp.month:02d}"
        if key in month_data:
            month_data[key] += s.annual_cost()

    chart_month_labels = json.dumps([f"{k[:4]}/{int(k[5:7])}月" for k in month_labels_raw], ensure_ascii=False)
    chart_month_values = json.dumps([round(month_data[k], 2) for k in month_labels_raw])

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "today": today,
        "total_subscriptions": len(subscriptions),
        "active_count": len(active_subs),
        "cost_summary": cost_summary,
        "total_annual_cost": total_annual_cost,
        "total_monthly_cost": total_monthly_cost,
        "upcoming_30_count": len(upcoming_30),
        "no_owner_count": len(no_owner),
        "trial_expiring_count": len(trial_expiring),
        "upcoming_90": upcoming_90,
        "chart_cat_labels": chart_cat_labels,
        "chart_cat_values": chart_cat_values,
        "chart_month_labels": chart_month_labels,
        "chart_month_values": chart_month_values,
    })


def _csv_safe(v) -> str:
    if v is None:
        return ""
    s = str(v)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


@router.get("/subscriptions/export")
def export_csv(uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM for Excel
    writer = csv.writer(buf)
    writer.writerow(["服務名稱", "登入帳號", "到期日", "狀態", "費用", "幣別",
                     "計費週期", "負責人", "分類", "部門", "備註"])
    for s in subscriptions:
        writer.writerow([
            _csv_safe(s.service_name), _csv_safe(s.login_account), s.expiry_date.strftime('%Y/%m/%d'), s.status.value,
            s.cost or "", s.currency, s.billing_cycle or "",
            _csv_safe(s.owner_name), _csv_safe(s.category), _csv_safe(s.department), _csv_safe(s.notes),
        ])
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''subscriptions.csv"},
    )


@router.get("/")
def index(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    today = date.today()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "subscriptions": subscriptions,
        "today": today,
        "current_user": current_user,
    })


def _add_billing_period(d: date, billing_cycle: str | None) -> date:
    bc = (billing_cycle or "annual").lower()
    if bc == "monthly":
        m, y = d.month + 1, d.year
        if m > 12:
            m, y = 1, y + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    if bc == "quarterly":
        months = d.month - 1 + 3
        y = d.year + months // 12
        m = months % 12 + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    if bc == "semi_annual":
        months = d.month - 1 + 6
        y = d.year + months // 12
        m = months % 12 + 1
        return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    if bc == "biennial":
        try:
            return d.replace(year=d.year + 2)
        except ValueError:
            return date(d.year + 2, 2, 28)
    # annual (default)
    try:
        return d.replace(year=d.year + 1)
    except ValueError:
        return date(d.year + 1, 2, 28)


def _dept_options(config_repo) -> list[tuple[str, str]]:
    """Returns (value, label) pairs with visual indent for sub-departments."""
    result = []
    for parent in config_repo.get_tree("department"):
        result.append((parent.value, parent.value))
        for child in parent.children:
            result.append((child.value, f"　{child.value}"))
    return result


@router.get("/subscriptions/create")
def create_form(request: Request, current_user=Depends(require_create), config_repo=Depends(get_config_repo)):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "category_options": [o.value for o in config_repo.get_by_type("category")],
        "department_options": _dept_options(config_repo),
        "billing_cycle_options": BILLING_CYCLE_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/create")
def create_submit(
    request: Request,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    status: str = Form("active"),
    cost: str | None = Form(None),
    currency: str = Form("TWD"),
    notes: str | None = Form(None),
    owner_name: str | None = Form(None),
    category: str | None = Form(None),
    department: str | None = Form(None),
    billing_cycle: str | None = Form(None),
    payment_account: str | None = Form(None),
    auto_renew: bool = Form(False),
    trial_end_date: str | None = Form(None),
    next_billing_date: str | None = Form(None),
    uc=Depends(get_create_uc),
    current_user=Depends(require_create),
    audit_repo=Depends(get_audit_log_repo),
    config_repo=Depends(get_config_repo),
):
    def _create_error(msg: str):
        return templates.TemplateResponse("create.html", {
            "request": request,
            "error": msg,
            "notification_options": NOTIFICATION_OPTIONS,
            "status_options": STATUS_OPTIONS,
            "currency_options": CURRENCY_OPTIONS,
            "category_options": [o.value for o in config_repo.get_by_type("category")],
            "department_options": _dept_options(config_repo),
            "billing_cycle_options": BILLING_CYCLE_OPTIONS,
            "current_user": current_user,
        }, status_code=422)

    try:
        parsed_expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        parsed_trial = datetime.strptime(trial_end_date, "%Y-%m-%d").date() if trial_end_date else None
        parsed_next_billing = datetime.strptime(next_billing_date, "%Y-%m-%d").date() if next_billing_date else None
    except ValueError:
        return _create_error("日期格式不正確，請使用 YYYY-MM-DD 格式")

    sub = uc.execute(
        service_name=service_name,
        login_account=login_account,
        expiry_date=parsed_expiry,
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        status=SubscriptionStatus(status),
        cost=Decimal(cost) if cost and cost.strip() else None,
        currency=currency,
        notes=notes or None,
        owner_name=owner_name or None,
        category=category or None,
        department=department or None,
        billing_cycle=billing_cycle or None,
        payment_account=payment_account or None,
        auto_renew=bool(auto_renew),
        trial_end_date=parsed_trial,
        next_billing_date=parsed_next_billing,
    )
    audit_repo.add(AuditEntry(
        user_id=current_user.id,
        user_email=current_user.email,
        action="create",
        target_type="subscription",
        target_id=sub.id,
        target_name=sub.service_name,
    ))
    return RedirectResponse("/", status_code=303)


@router.get("/subscriptions/{subscription_id}/edit")
def edit_form(
    request: Request,
    subscription_id: int,
    uc=Depends(get_single_uc),
    current_user=Depends(require_update),
    config_repo=Depends(get_config_repo),
):
    sub = uc.execute(subscription_id)
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "sub": sub,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "category_options": [o.value for o in config_repo.get_by_type("category")],
        "department_options": _dept_options(config_repo),
        "billing_cycle_options": BILLING_CYCLE_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/{subscription_id}/edit")
def edit_submit(
    request: Request,
    subscription_id: int,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    notification_emails: str = Form(...),
    notification_days: int = Form(...),
    status: str = Form("active"),
    cost: str | None = Form(None),
    currency: str = Form("TWD"),
    notes: str | None = Form(None),
    owner_name: str | None = Form(None),
    category: str | None = Form(None),
    department: str | None = Form(None),
    billing_cycle: str | None = Form(None),
    payment_account: str | None = Form(None),
    auto_renew: bool = Form(False),
    trial_end_date: str | None = Form(None),
    next_billing_date: str | None = Form(None),
    uc=Depends(get_update_uc),
    single_uc=Depends(get_single_uc),
    current_user=Depends(require_update),
    audit_repo=Depends(get_audit_log_repo),
    config_repo=Depends(get_config_repo),
):
    try:
        parsed_expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        parsed_trial = datetime.strptime(trial_end_date, "%Y-%m-%d").date() if trial_end_date else None
        parsed_next_billing = datetime.strptime(next_billing_date, "%Y-%m-%d").date() if next_billing_date else None
    except ValueError:
        current_sub = single_uc.execute(subscription_id)
        return templates.TemplateResponse("edit.html", {
            "request": request,
            "sub": current_sub,
            "error": "日期格式不正確，請使用 YYYY-MM-DD 格式",
            "notification_options": NOTIFICATION_OPTIONS,
            "status_options": STATUS_OPTIONS,
            "currency_options": CURRENCY_OPTIONS,
            "category_options": [o.value for o in config_repo.get_by_type("category")],
            "department_options": _dept_options(config_repo),
            "billing_cycle_options": BILLING_CYCLE_OPTIONS,
            "current_user": current_user,
        }, status_code=422)

    sub = uc.execute(
        subscription_id=subscription_id,
        service_name=service_name,
        login_account=login_account,
        expiry_date=parsed_expiry,
        notification_emails=notification_emails,
        notification_days=NotificationDays(notification_days),
        status=SubscriptionStatus(status),
        cost=Decimal(cost) if cost and cost.strip() else None,
        currency=currency,
        notes=notes or None,
        owner_name=owner_name or None,
        category=category or None,
        department=department or None,
        billing_cycle=billing_cycle or None,
        payment_account=payment_account or None,
        auto_renew=bool(auto_renew),
        trial_end_date=parsed_trial,
        next_billing_date=parsed_next_billing,
    )
    audit_repo.add(AuditEntry(
        user_id=current_user.id,
        user_email=current_user.email,
        action="update",
        target_type="subscription",
        target_id=sub.id,
        target_name=sub.service_name,
    ))
    return RedirectResponse("/", status_code=303)


CAT_COLORS = {
    '生產力工具': '#6E5DE7',
    '開發工具':   '#2B5BD7',
    '設計工具':   '#D86A3D',
    '雲端基礎':   '#0E8C56',
    '資安合規':   '#C13066',
    '行銷廣告':   '#B57600',
    '財務會計':   '#7C3AED',
    'HR人資':     '#0891B2',
    '其他':       '#6B7280',
    '未分類':     '#B0AEC4',
}


def _build_report_sections(active: list) -> list[dict]:
    """Build per-currency report sections with chart JSON and department data embedded.

    Extracted for testability — called by the reports handler and unit tests alike.
    """
    cur_totals: dict[str, float] = defaultdict(float)
    cur_cat_map: dict[str, dict] = {}
    cur_dept_map: dict[str, dict] = {}

    for s in active:
        cur = s.currency or "TWD"

        # Category accumulator
        k = s.category or "未分類"
        if cur not in cur_cat_map:
            cur_cat_map[cur] = defaultdict(lambda: {"cost": 0.0, "count": 0})
        cur_cat_map[cur][k]["cost"] += s.annual_cost()
        cur_cat_map[cur][k]["count"] += 1

        # Department accumulator
        dept = s.department or "未分類"
        if cur not in cur_dept_map:
            cur_dept_map[cur] = defaultdict(lambda: {"cost": 0.0, "count": 0})
        cur_dept_map[cur][dept]["cost"] += s.annual_cost()
        cur_dept_map[cur][dept]["count"] += 1

        cur_totals[cur] += s.annual_cost()

    sections = []
    for cur in sorted(cur_totals, key=lambda c: -cur_totals[c]):
        total = cur_totals[cur]

        # Categories
        cats = sorted(
            [{"name": k, "cost": v["cost"], "count": v["count"]}
             for k, v in cur_cat_map[cur].items()],
            key=lambda c: -c["cost"],
        )
        for c in cats:
            c["monthly"] = c["cost"] / 12
            c["avg"] = c["cost"] / c["count"] if c["count"] else 0
            c["pct"] = round(c["cost"] / total * 100, 1) if total else 0

        # Departments
        depts = sorted(
            [{"name": k, "cost": v["cost"], "count": v["count"]}
             for k, v in cur_dept_map.get(cur, {}).items()],
            key=lambda d: -d["cost"],
        )
        for d in depts:
            d["monthly"] = d["cost"] / 12
            d["pct"] = round(d["cost"] / total * 100, 1) if total else 0

        sections.append({
            "currency": cur,
            "categories": cats,
            "total_annual": total,
            "total_monthly": total / 12,
            "count": sum(c["count"] for c in cats),
            "cat_labels_json": json.dumps([c["name"] for c in cats], ensure_ascii=False),
            "cat_values_json": json.dumps([round(c["cost"], 2) for c in cats]),
            "cat_colors_json": json.dumps(CAT_COLORS, ensure_ascii=False),
            "departments": depts,
        })

    return sections


@router.get("/reports")
def reports(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()

    active = [s for s in subscriptions if s.status.value in ("active", "renewed")]
    sections = _build_report_sections(active)

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "current_user": current_user,
        "sections": sections,
        "cat_colors": CAT_COLORS,
    })


@router.post("/subscriptions/bulk-renew")
def bulk_renew(
    ids: str = Form(...),
    single_uc=Depends(get_single_uc),
    uc=Depends(get_update_uc),
    current_user=Depends(require_update),
    audit_repo=Depends(get_audit_log_repo),
):
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
    for sub_id in id_list:
        sub = single_uc.execute(sub_id)
        if not sub:
            continue
        new_expiry = _add_billing_period(sub.expiry_date, sub.billing_cycle)
        uc.execute(
            subscription_id=sub_id,
            service_name=sub.service_name,
            login_account=sub.login_account,
            expiry_date=new_expiry,
            notification_emails=sub.notification_emails,
            notification_days=sub.notification_days,
            status=sub.status,
            cost=sub.cost,
            currency=sub.currency,
            notes=sub.notes,
            owner_name=sub.owner_name,
            category=sub.category,
            department=sub.department,
            billing_cycle=sub.billing_cycle,
            payment_account=sub.payment_account,
            auto_renew=sub.auto_renew,
            trial_end_date=sub.trial_end_date,
            next_billing_date=sub.next_billing_date,
            notifications_enabled=sub.notifications_enabled,
        )
        audit_repo.add(AuditEntry(
            user_id=current_user.id,
            user_email=current_user.email,
            action="renew",
            target_type="subscription",
            target_id=sub_id,
            target_name=sub.service_name,
        ))
    return RedirectResponse("/", status_code=303)


@router.post("/subscriptions/{subscription_id}/delete")
def delete(
    subscription_id: int,
    uc=Depends(get_delete_uc),
    single_uc=Depends(get_single_uc),
    current_user=Depends(require_delete),
    audit_repo=Depends(get_audit_log_repo),
):
    sub = single_uc.execute(subscription_id)
    service_name = sub.service_name if sub else str(subscription_id)
    uc.execute(subscription_id)
    audit_repo.add(AuditEntry(
        user_id=current_user.id,
        user_email=current_user.email,
        action="delete",
        target_type="subscription",
        target_id=subscription_id,
        target_name=service_name,
    ))
    return RedirectResponse("/", status_code=303)
