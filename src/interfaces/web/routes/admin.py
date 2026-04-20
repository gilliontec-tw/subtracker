from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.interfaces.web.dependencies import (
    get_user_repo, get_register_uc, get_update_permissions_uc,
    get_list_users_uc, require_admin,
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="src/interfaces/web/templates")


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
    password: str = Form(...),
    can_create: bool = Form(False),
    can_update: bool = Form(False),
    can_delete: bool = Form(False),
    current_user=Depends(require_admin),
    uc=Depends(get_register_uc),
):
    try:
        uc.execute(
            email=email,
            display_name=display_name,
            password=password,
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
    return RedirectResponse("/admin/users", status_code=303)


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
