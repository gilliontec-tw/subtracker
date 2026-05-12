from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from src.domain.entities.subscription import NotificationDays
from src.interfaces.web.constants import NOTIFICATION_OPTIONS
from src.interfaces.web.dependencies import (
    get_list_uc, get_update_uc, get_single_uc,
    get_current_user, require_update, templates,
)

router = APIRouter()


@router.get("/notifications/settings")
def notif_settings(
    request: Request,
    saved: bool = False,
    uc=Depends(get_list_uc),
    current_user=Depends(get_current_user),
):
    subscriptions = uc.execute()
    today = date.today()
    active = sorted(
        [s for s in subscriptions if s.status.value in ("active", "renewed")],
        key=lambda s: s.expiry_date,
    )
    return templates.TemplateResponse("notifications/settings.html", {
        "request": request,
        "current_user": current_user,
        "subscriptions": active,
        "today": today,
        "timedelta": timedelta,
        "notification_options": NOTIFICATION_OPTIONS,
        "saved": saved,
        "error": None,
    })


@router.post("/notifications/settings")
async def notif_settings_save(
    request: Request,
    uc=Depends(get_update_uc),
    list_uc=Depends(get_list_uc),
    current_user=Depends(require_update),
):
    form = await request.form()
    sub_ids_raw = form.get("sub_ids", "")
    ids = [int(i) for i in sub_ids_raw.split(",") if i.strip().isdigit()]

    # Pre-load all subscriptions once to avoid N+1 DB calls in the loops below.
    all_subscriptions = list_uc.execute()
    sub_map = {s.id: s for s in all_subscriptions}
    today = date.today()
    active = sorted(
        [s for s in all_subscriptions if s.status.value in ("active", "renewed")],
        key=lambda s: s.expiry_date,
    )

    # Validate: reject if any enabled subscription has empty email (per D-03).
    # Collect all errors in one pass so the user sees all issues at once.
    errors = []
    for sid in ids:
        if f"notify_{sid}" in form:
            emails_check = form.get(f"emails_{sid}", "").strip()
            if not emails_check:
                sub_check = sub_map.get(sid)
                name = sub_check.service_name if sub_check else str(sid)
                errors.append(f"「{name}」已啟用通知但收件人 Email 為空，請填寫後再儲存")

    if errors:
        return templates.TemplateResponse("notifications/settings.html", {
            "request": request,
            "current_user": current_user,
            "subscriptions": active,
            "today": today,
            "timedelta": timedelta,
            "notification_options": NOTIFICATION_OPTIONS,
            "saved": False,
            "error": errors[0],
        })

    for sid in ids:
        sub = sub_map.get(sid)
        if sub is None:
            continue

        enabled = f"notify_{sid}" in form
        emails_from_form = form.get(f"emails_{sid}", "").strip()
        emails = emails_from_form if enabled else sub.notification_emails  # preserve on disable (per D-04)
        days_val = int(form.get(f"days_{sid}", str(sub.notification_days.value)))

        try:
            nd = NotificationDays(days_val)
        except ValueError:
            nd = sub.notification_days

        uc.execute(
            subscription_id=sid,
            service_name=sub.service_name,
            login_account=sub.login_account,
            expiry_date=sub.expiry_date,
            notification_emails=emails,
            notification_days=nd,
            status=sub.status,
            cost=sub.cost,
            currency=sub.currency,
            notes=sub.notes,
            user_name=sub.user_name,
            category=sub.category,
            department=sub.department,
            billing_cycle=sub.billing_cycle,
            payment_account=sub.payment_account,
            auto_renew=sub.auto_renew,
            notifications_enabled=enabled,
        )

    return RedirectResponse("/notifications/settings?saved=true", status_code=303)
