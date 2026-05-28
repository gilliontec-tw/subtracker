from api.exception_handlers import register_exception_handlers
from domain.exceptions import (
    DuplicateEmailException,
    ForbiddenException,
    LastAdminException,
    NotAuthenticatedException,
    NotFoundException,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

_app = FastAPI()
register_exception_handlers(_app)


@_app.get("/not-auth")
def raise_not_auth():
    raise NotAuthenticatedException()


@_app.get("/forbidden")
def raise_forbidden():
    raise ForbiddenException()


@_app.get("/not-found")
def raise_not_found():
    raise NotFoundException()


@_app.get("/duplicate-email")
def raise_duplicate_email():
    raise DuplicateEmailException("test@corp.com")


@_app.get("/last-admin")
def raise_last_admin():
    raise LastAdminException()


client = TestClient(_app, raise_server_exceptions=False)


def test_not_authenticated_returns_401():
    r = client.get("/not-auth")
    assert r.status_code == 401
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None


def test_forbidden_returns_403():
    r = client.get("/forbidden")
    assert r.status_code == 403
    body = r.json()
    assert body["success"] is False


def test_not_found_returns_404():
    r = client.get("/not-found")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False


def test_duplicate_email_returns_409():
    r = client.get("/duplicate-email")
    assert r.status_code == 409
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None


def test_last_admin_returns_400():
    r = client.get("/last-admin")
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None
