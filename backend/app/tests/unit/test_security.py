"""Testy modułu bezpieczeństwa."""

import pytest
from jose import jwt

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings

settings = get_settings()


def test_hash_and_verify_password():
    password = "MySuperSecretPass123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_create_access_token():
    token = create_access_token("user-123")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload


def test_create_refresh_token():
    token = create_refresh_token("user-456")
    payload = decode_token(token)

    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    with pytest.raises(Exception):
        decode_token("invalid.token.here")
