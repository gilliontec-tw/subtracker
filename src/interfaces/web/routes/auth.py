from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from src.interfaces.web.dependencies import get_login_uc
from src.interfaces.web.session import create_session_cookie, clear_session_cookie, get_session_user_id

router = APIRouter()
templates = Jinja2Templates(directory="src/interfaces/web/templates")


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
