from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import json
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from src.domain.entities.audit_entry import AuditEntry
from src.domain.entities.subscription import NotificationDays, SubscriptionStatus
from src.interfaces.web.dependencies import (
    get_create_uc, get_delete_uc, get_list_uc, get_single_uc, get_update_uc,
    get_current_user, require_create, require_update, require_delete,
    get_audit_log_repo,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/interfaces/web/templates")

NOTIFICATION_OPTIONS = [
    (3,   "3 天前"),
    (7,   "7 天前"),
    (14,  "14 天前"),
    (30,  "1 個月前"),
    (90,  "3 個月前"),
    (120, "4 個月前"),
]

STATUS_OPTIONS = [
    ("active",    "使用中"),
    ("renewed",   "已續約"),
    ("cancelled", "已取消"),
    ("suspended", "暫停"),
]

CURRENCY_OPTIONS = ["TWD", "USD", "EUR", "JPY"]

CATEGORY_OPTIONS = [
    "生產力工具", "開發工具", "資安合規", "設計工具",
    "行銷廣告", "雲端基礎", "財務會計", "HR人資", "其他",
]

DEPARTMENT_OPTIONS = [
    "全公司", "工程", "設計", "行銷", "業務", "財務", "HR", "IT", "其他",
]

BILLING_CYCLE_OPTIONS = [
    ("monthly", "月付"),
    ("annual",  "年付"),
]


@router.get("/dashboard")
def dashboard(request: Request, uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    subscriptions = uc.execute()
    today = date.today()

    def annual_cost(s):
        if s.cost is None:
            return 0
        c = float(s.cost)
        bc = (s.billing_cycle or "").lower()
        if bc == "monthly":
            return c * 12
        return c  # annual / empty → treat as annual

    active_subs = [s for s in subscriptions if s.status.value in ("active", "renewed")]
    total_annual_cost = sum(annual_cost(s) for s in active_subs)
    total_monthly_cost = total_annual_cost / 12

    upcoming_30 = [s for s in active_subs if 0 <= (s.expiry_date - today).days <= 30]
    upcoming_90 = sorted(
        [s for s in active_subs if 0 <= (s.expiry_date - today).days <= 90],
        key=lambda s: s.expiry_date,
    )
    no_owner = [s for s in active_subs if not s.owner_name]

    # ── Donut chart: cost by category ────────────────────────────────────
    cat_costs: dict[str, float] = defaultdict(float)
    for s in active_subs:
        cat = s.category or "未分類"
        cat_costs[cat] += annual_cost(s)
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
            month_data[key] += annual_cost(s)

    chart_month_labels = json.dumps([f"{k[:4]}/{int(k[5:7])}月" for k in month_labels_raw], ensure_ascii=False)
    chart_month_values = json.dumps([round(month_data[k], 2) for k in month_labels_raw])

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "today": today,
        "total_subscriptions": len(subscriptions),
        "active_count": len(active_subs),
        "total_annual_cost": total_annual_cost,
        "total_monthly_cost": total_monthly_cost,
        "upcoming_30_count": len(upcoming_30),
        "no_owner_count": len(no_owner),
        "upcoming_90": upcoming_90,
        "chart_cat_labels": chart_cat_labels,
        "chart_cat_values": chart_cat_values,
        "chart_month_labels": chart_month_labels,
        "chart_month_values": chart_month_values,
    })


@router.get("/subscriptions/export")
def export_csv(uc=Depends(get_list_uc), current_user=Depends(get_current_user)):
    import csv, io
    subscriptions = uc.execute()
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM for Excel
    writer = csv.writer(buf)
    writer.writerow(["服務名稱", "登入帳號", "到期日", "狀態", "費用", "幣別",
                     "計費週期", "負責人", "分類", "部門", "備註"])
    for s in subscriptions:
        writer.writerow([
            s.service_name, s.login_account, s.expiry_date, s.status.value,
            s.cost or "", s.currency, s.billing_cycle or "",
            s.owner_name or "", s.category or "", s.department or "", s.notes or "",
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


@router.get("/subscriptions/create")
def create_form(request: Request, current_user=Depends(require_create)):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "category_options": CATEGORY_OPTIONS,
        "department_options": DEPARTMENT_OPTIONS,
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
    uc=Depends(get_create_uc),
    current_user=Depends(require_create),
    audit_repo=Depends(get_audit_log_repo),
):
    sub = uc.execute(
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
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
):
    sub = uc.execute(subscription_id)
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "sub": sub,
        "notification_options": NOTIFICATION_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "currency_options": CURRENCY_OPTIONS,
        "category_options": CATEGORY_OPTIONS,
        "department_options": DEPARTMENT_OPTIONS,
        "billing_cycle_options": BILLING_CYCLE_OPTIONS,
        "current_user": current_user,
    })


@router.post("/subscriptions/{subscription_id}/edit")
def edit_submit(
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
    uc=Depends(get_update_uc),
    current_user=Depends(require_update),
    audit_repo=Depends(get_audit_log_repo),
):
    sub = uc.execute(
        subscription_id=subscription_id,
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
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
