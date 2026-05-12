"""
csrf.py
~~~~~~~
CSRF 保護模組 — Double Submit Cookie Pattern

原理:
  1. 每個 HTTP 回應都在 Response 中注入一個 `csrf_token` cookie（非 HttpOnly）。
  2. 所有狀態變更請求（POST/PUT/DELETE/PATCH）必須在 form body 提交
     同名欄位 `csrf_token`，其值需與 cookie 中的值一致。
  3. 攻擊者在跨站環境中無法讀取 cookie（Same-Origin Policy），
     因此無法偽造合法的 CSRF token。

Token 結構:
  - 使用 `itsdangerous.URLSafeTimedSerializer` 簽名，防止偽造。
  - salt="csrf-protection" 與 session salt 不同，確保 token 用途分離。
  - 有效期 CSRF_MAX_AGE 秒（預設 1 小時），過期後 middleware 自動輪換。

Middleware 豁免路徑（CSRF_EXEMPT_PATHS）:
  - 全部為 GET 路由，不需豁免（POST 登入也受保護）。
  - 若需要對特定端點豁免，可將路徑前綴加入 CSRF_EXEMPT_PATHS set。
"""
import os
import secrets

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response, HTTPException

_SECRET_KEY = os.getenv("SECRET_KEY", "")
_csrf_serializer = URLSafeTimedSerializer(_SECRET_KEY, salt="csrf-protection")

CSRF_COOKIE = "csrf_token"
CSRF_FIELD  = "csrf_token"          # HTML <input name="csrf_token">
CSRF_MAX_AGE = 3600                  # 1 小時

# 不需要 CSRF 驗證的 HTTP 方法（冪等操作）
CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# SEC-H1: 使用 COOKIE_SECURE 設定（與 session cookie 一致）
_COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").strip().lower() == "true"


# ── Token 生成 ─────────────────────────────────────────────────────────────
def generate_csrf_token() -> str:
    """生成簽名的 CSRF token（含隨機 nonce）。"""
    nonce = secrets.token_urlsafe(24)
    return _csrf_serializer.dumps(nonce)


def _is_valid_token(token: str) -> bool:
    """驗證 CSRF token 簽名與有效期。"""
    try:
        _csrf_serializer.loads(token, max_age=CSRF_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


# ── Cookie 設定 ─────────────────────────────────────────────────────────────
def set_csrf_cookie(response: Response, token: str) -> None:
    """將 CSRF token 寫入 cookie（非 HttpOnly，讓 HTML form 可讀取）。"""
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,          # form 需要讀取此值注入 hidden field
        samesite="lax",
        secure=_COOKIE_SECURE,
        max_age=CSRF_MAX_AGE,
    )


# ── Request 驗證 ─────────────────────────────────────────────────────────────
def get_cookie_token(request: Request) -> str | None:
    """從 request cookie 取得 CSRF token。"""
    return request.cookies.get(CSRF_COOKIE)


async def validate_csrf_request(request: Request) -> bool:
    """
    驗證 POST/PUT/DELETE/PATCH 請求的 CSRF token。
    比對 cookie token == form body token（常數時間比較防止 timing attack）。
    """
    if request.method in CSRF_SAFE_METHODS:
        return True

    cookie_token = get_cookie_token(request)
    if not cookie_token:
        return False

    # 從 form body 讀取 token
    try:
        form = await request.form()
        submitted_token = form.get(CSRF_FIELD, "")
    except Exception:
        return False

    # 1. 簽名驗證（防偽造）
    if not _is_valid_token(cookie_token):
        return False

    # 2. 常數時間比較 cookie token vs form token（防 timing attack）
    return secrets.compare_digest(cookie_token, str(submitted_token))

async def verify_csrf(request: Request):
    """
    FastAPI Dependency to verify CSRF tokens.
    """
    if request.method in CSRF_SAFE_METHODS:
        return

    is_valid = await validate_csrf_request(request)
    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail="CSRF token 驗證失敗，請重新整理頁面後再試。"
        )
