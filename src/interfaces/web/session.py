import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response

_SECRET_KEY = os.environ["SECRET_KEY"]
_serializer = URLSafeTimedSerializer(_SECRET_KEY)
SESSION_COOKIE = "session"
SESSION_MAX_AGE = 86400 * 7  # 7 days


def create_session_cookie(response: Response, user_id: int) -> None:
    token = _serializer.dumps({"user_id": user_id})
    response.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax",
        max_age=SESSION_MAX_AGE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def get_session_user_id(request: Request) -> int | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None
