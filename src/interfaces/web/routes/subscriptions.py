from datetime import date, datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.domain.entities.subscription import NotificationDays
from src.interfaces.web.dependencies import (
    get_create_uc, get_delete_uc, get_list_uc, get_single_uc, get_update_uc,
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


@router.get("/")
def index(request: Request, uc=Depends(get_list_uc)):
    subscriptions = uc.execute()
    today = date.today()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "subscriptions": subscriptions,
        "today": today,
    })


@router.get("/subscriptions/create")
def create_form(request: Request):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "notification_options": NOTIFICATION_OPTIONS,
    })


@router.post("/subscriptions/create")
def create_submit(
    request: Request,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    responsible_person_email: str = Form(...),
    notification_days: int = Form(...),
    uc=Depends(get_create_uc),
):
    uc.execute(
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        responsible_person_email=responsible_person_email,
        notification_days=NotificationDays(notification_days),
    )
    return RedirectResponse("/", status_code=303)


@router.get("/subscriptions/{subscription_id}/edit")
def edit_form(request: Request, subscription_id: int, uc=Depends(get_single_uc)):
    sub = uc.execute(subscription_id)
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "sub": sub,
        "notification_options": NOTIFICATION_OPTIONS,
    })


@router.post("/subscriptions/{subscription_id}/edit")
def edit_submit(
    subscription_id: int,
    service_name: str = Form(...),
    login_account: str = Form(...),
    expiry_date: str = Form(...),
    responsible_person_email: str = Form(...),
    notification_days: int = Form(...),
    uc=Depends(get_update_uc),
):
    uc.execute(
        subscription_id=subscription_id,
        service_name=service_name,
        login_account=login_account,
        expiry_date=datetime.strptime(expiry_date, "%Y-%m-%d").date(),
        responsible_person_email=responsible_person_email,
        notification_days=NotificationDays(notification_days),
    )
    return RedirectResponse("/", status_code=303)


@router.post("/subscriptions/{subscription_id}/delete")
def delete(subscription_id: int, uc=Depends(get_delete_uc)):
    uc.execute(subscription_id)
    return RedirectResponse("/", status_code=303)
