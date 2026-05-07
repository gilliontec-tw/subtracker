from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from src.infrastructure.auth.hash_utils import hash_password
from src.interfaces.web.dependencies import get_login_uc, get_change_password_uc, get_current_user, get_user_repo, templates
from src.interfaces.web.session import create_session_cookie, clear_session_cookie, get_session_user_id

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    if get_session_user_id(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    uc=Depends(get_login_uc),
):
    try:
        user = uc.execute(email=email, password=password)
    except ValueError:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "帳號或密碼錯誤，請重試。"}
        )
    response = RedirectResponse("/", status_code=303)
    create_session_cookie(response, user.id)
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response


@router.get("/account/password")
def change_password_form(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse("account/change_password.html", {
        "request": request,
        "current_user": current_user,
        "error": None,
        "success": False,
    })


@router.post("/account/password")
def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    current_user=Depends(get_current_user),
    uc=Depends(get_change_password_uc),
):
    if new_password != new_password_confirm:
        return templates.TemplateResponse("account/change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "新密碼兩次輸入不一致。",
            "success": False,
        })
    try:
        uc.execute(
            user_id=current_user.id,
            current_password=current_password,
            new_password=new_password,
        )
    except ValueError as e:
        return templates.TemplateResponse("account/change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": str(e),
            "success": False,
        })
    return templates.TemplateResponse("account/change_password.html", {
        "request": request,
        "current_user": current_user,
        "error": None,
        "success": True,
    })


# ── Invite / set-password (public, no auth required) ────────────────────────
@router.get("/auth/invite/{token}")
def invite_form(request: Request, token: str, repo=Depends(get_user_repo)):
    user = repo.get_by_invite_token(token)
    error = None
    if not user:
        error = "連結無效或已使用。"
    elif user.invite_expires_at and user.invite_expires_at < datetime.now():
        error = "此邀請連結已過期，請聯絡管理員重新發送。"
    return templates.TemplateResponse("auth/set_password.html", {
        "request": request,
        "token": token,
        "email": user.email if user else "",
        "error": error,
        "success": False,
    })


@router.post("/auth/invite/{token}")
def invite_submit(
    request: Request,
    token: str,
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    repo=Depends(get_user_repo),
):
    user = repo.get_by_invite_token(token)
    if not user:
        return templates.TemplateResponse("auth/set_password.html", {
            "request": request, "token": token, "email": "",
            "error": "連結無效或已使用。", "success": False,
        })
    if user.invite_expires_at and user.invite_expires_at < datetime.now():
        return templates.TemplateResponse("auth/set_password.html", {
            "request": request, "token": token, "email": user.email,
            "error": "此邀請連結已過期，請聯絡管理員重新發送。", "success": False,
        })
    if new_password != new_password_confirm:
        return templates.TemplateResponse("auth/set_password.html", {
            "request": request, "token": token, "email": user.email,
            "error": "兩次輸入的密碼不一致。", "success": False,
        })
    if len(new_password) < 8:
        return templates.TemplateResponse("auth/set_password.html", {
            "request": request, "token": token, "email": user.email,
            "error": "密碼至少需要 8 個字元。", "success": False,
        })
    user.hashed_password   = hash_password(new_password)
    user.invite_token      = None
    user.invite_expires_at = None
    repo.update(user)
    return templates.TemplateResponse("auth/set_password.html", {
        "request": request, "token": token, "email": user.email,
        "error": None, "success": True,
    })
