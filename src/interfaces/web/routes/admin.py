import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from src.domain.entities.config_option import ConfigOption
from src.infrastructure.email.smtp_email_sender import SmtpEmailSender
from src.interfaces.web.dependencies import (
    get_user_repo, get_register_uc, get_update_permissions_uc,
    get_list_users_uc, require_admin, get_audit_log_repo, get_config_repo, templates,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


@router.get("/users")
def list_users(
    request: Request,
    uc=Depends(get_list_users_uc),
    current_user=Depends(require_admin),
):
    users = uc.execute()
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
    })


@router.get("/users/create")
def create_user_form(request: Request, current_user=Depends(require_admin)):
    return templates.TemplateResponse("admin/user_create.html", {
        "request": request,
        "current_user": current_user,
        "error": None,
    })


@router.post("/users/create")
def create_user_submit(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    can_create: bool = Form(False),
    can_update: bool = Form(False),
    can_delete: bool = Form(False),
    current_user=Depends(require_admin),
    uc=Depends(get_register_uc),
):
    try:
        user = uc.execute(
            email=email,
            display_name=display_name,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
        )
    except ValueError as e:
        return templates.TemplateResponse("admin/user_create.html", {
            "request": request,
            "current_user": current_user,
            "error": str(e),
        })
    # Send invite email
    try:
        base = str(request.base_url).rstrip("/")
        invite_url = f"{base}/auth/invite/{user.invite_token}"
        sender = SmtpEmailSender()
        sender.send(
            to=email,
            subject="[SubTrack] 您已被邀請加入，請設定密碼",
            body=(
                f"您好，{display_name}，\n\n"
                f"系統管理員已為您建立 SubTrack 帳號。\n\n"
                f"請點擊以下連結設定您的登入密碼（連結 72 小時內有效）：\n\n"
                f"{invite_url}\n\n"
                f"若您未預期收到此信，請忽略即可。\n\n"
                f"此信為系統自動發送，請勿回覆。"
            ),
        )
    except Exception:
        log.exception("Failed to send invite email to %s", email)
    return RedirectResponse("/admin/users?invited=1", status_code=303)


@router.post("/users/{user_id}/resend-invite")
def resend_invite(
    request: Request,
    user_id: int,
    current_user=Depends(require_admin),
    repo=Depends(get_user_repo),
):
    import secrets
    from datetime import datetime, timedelta, timezone
    user = repo.get_by_id(user_id)
    if user and user.invite_token:
        user.invite_token = secrets.token_urlsafe(32)
        user.invite_expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
        repo.update(user)
        try:
            base = str(request.base_url).rstrip("/")
            invite_url = f"{base}/auth/invite/{user.invite_token}"
            from src.infrastructure.email.smtp_email_sender import SmtpEmailSender
            SmtpEmailSender().send(
                to=user.email,
                subject="[SubTrack] 邀請連結已重新發送，請設定密碼",
                body=(
                    f"您好，{user.display_name}，\n\n"
                    f"這是一封重新發送的邀請信。\n\n"
                    f"請點擊以下連結設定您的登入密碼（連結 72 小時內有效）：\n\n"
                    f"{invite_url}\n\n"
                    f"此信為系統自動發送，請勿回覆。"
                ),
            )
        except Exception:
            log.exception("Failed to resend invite email to user_id=%s", user_id)
    return RedirectResponse("/admin/users?invited=1", status_code=303)


@router.get("/users/{user_id}/edit")
def edit_user_form(
    request: Request,
    user_id: int,
    current_user=Depends(require_admin),
    repo=Depends(get_user_repo),
):
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/user_edit.html", {
        "request": request,
        "user": user,
        "current_user": current_user,
        "error": None,
    })


@router.post("/users/{user_id}/edit")
def edit_user_submit(
    user_id: int,
    can_create: bool = Form(False),
    can_update: bool = Form(False),
    can_delete: bool = Form(False),
    is_active: bool = Form(False),
    current_user=Depends(require_admin),
    uc=Depends(get_update_permissions_uc),
):
    uc.execute(
        user_id=user_id,
        can_create=can_create,
        can_update=can_update,
        can_delete=can_delete,
        is_active=is_active,
    )
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    current_user=Depends(require_admin),
    repo=Depends(get_user_repo),
):
    user = repo.get_by_id(user_id)
    if user and user.role != "admin":
        repo.delete(user_id)
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/settings")
def settings(
    request: Request,
    saved: bool = False,
    current_user=Depends(require_admin),
    repo=Depends(get_config_repo),
):
    repo.seed_defaults_if_empty()
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "current_user": current_user,
        "categories": repo.get_by_type("category"),
        "dept_tree": repo.get_tree("department"),
        "saved": saved,
    })


@router.post("/settings/add")
def settings_add(
    type: str = Form(...),
    value: str = Form(...),
    parent_id: int | None = Form(None),
    current_user=Depends(require_admin),
    repo=Depends(get_config_repo),
):
    value = value.strip()
    if value and not repo.exists(type, value, parent_id):
        repo.add(ConfigOption(type=type, value=value, parent_id=parent_id))
    return RedirectResponse("/admin/settings", status_code=303)


@router.post("/settings/{option_id}/rename")
def settings_rename(
    option_id: int,
    value: str = Form(...),
    current_user=Depends(require_admin),
    repo=Depends(get_config_repo),
):
    value = value.strip()
    if value:
        repo.rename(option_id, value)
    return RedirectResponse("/admin/settings", status_code=303)


@router.post("/settings/{option_id}/delete")
def settings_delete(
    option_id: int,
    current_user=Depends(require_admin),
    repo=Depends(get_config_repo),
):
    repo.delete(option_id)
    return RedirectResponse("/admin/settings", status_code=303)


@router.get("/audit-log")
def audit_log(
    request: Request,
    audit_repo=Depends(get_audit_log_repo),
    current_user=Depends(require_admin),
):
    entries = audit_repo.get_recent(limit=200)
    return templates.TemplateResponse("admin/audit_log.html", {
        "request": request,
        "entries": entries,
        "current_user": current_user,
    })
