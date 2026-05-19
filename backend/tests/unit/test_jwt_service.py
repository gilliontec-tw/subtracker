import jwt as pyjwt
import pytest
from infrastructure.auth.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_create_access_token_returns_string():
    token = create_access_token(user_id=1, role="admin")
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_has_correct_claims():
    token = create_access_token(user_id=42, role="manager")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "manager"
    assert payload["type"] == "access"


def test_create_refresh_token_returns_token_and_jti():
    token, jti = create_refresh_token(user_id=1)
    assert isinstance(token, str)
    assert isinstance(jti, str)
    assert len(jti) > 0


def test_decode_refresh_token_has_correct_claims():
    token, jti = create_refresh_token(user_id=99)
    payload = decode_refresh_token(token)
    assert payload["sub"] == "99"
    assert payload["jti"] == jti
    assert payload["type"] == "refresh"


def test_decode_access_token_rejects_wrong_secret():
    bad_token = pyjwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(pyjwt.exceptions.InvalidSignatureError):
        decode_access_token(bad_token)


def test_access_token_cannot_decode_as_refresh():
    token = create_access_token(user_id=1, role="user")
    with pytest.raises(pyjwt.exceptions.InvalidSignatureError):
        decode_refresh_token(token)
