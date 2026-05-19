from api.middleware.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, CSRFMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient

_app = FastAPI()
_app.add_middleware(CSRFMiddleware)


@_app.get("/safe")
def safe_get():
    return {"ok": True}


@_app.post("/unsafe")
def unsafe_post():
    return {"ok": True}


@_app.post("/api/v1/auth/login")
def login_exempt():
    return {"ok": True}


client = TestClient(_app, raise_server_exceptions=False)


def test_get_passes_without_csrf():
    r = client.get("/safe")
    assert r.status_code == 200


def test_post_without_any_token_returns_403():
    r = client.post("/unsafe")
    assert r.status_code == 403
    assert r.json()["success"] is False


def test_post_with_matching_tokens_passes():
    r = client.post(
        "/unsafe",
        cookies={CSRF_COOKIE_NAME: "abc123"},
        headers={CSRF_HEADER_NAME: "abc123"},
    )
    assert r.status_code == 200


def test_post_with_mismatched_tokens_returns_403():
    r = client.post(
        "/unsafe",
        cookies={CSRF_COOKIE_NAME: "abc123"},
        headers={CSRF_HEADER_NAME: "different"},
    )
    assert r.status_code == 403


def test_login_path_is_exempt():
    r = client.post("/api/v1/auth/login")
    assert r.status_code == 200


def test_post_with_only_header_no_cookie_returns_403():
    r = client.post("/unsafe", headers={CSRF_HEADER_NAME: "abc123"})
    assert r.status_code == 403
