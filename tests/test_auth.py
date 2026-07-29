import asyncio
import sqlite3
from datetime import timedelta

import pytest
from fastapi import HTTPException

import auth_utils


@pytest.fixture
def isolated_auth(monkeypatch, tmp_path):
    db_path = tmp_path / "auth.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                role TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO users (username, role) VALUES (?, ?)",
            [("admin_test", "Admin"), ("normal_test", "Member")],
        )
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-secret-not-for-runtime")
    monkeypatch.setenv("SMARTHOME_DB_PATH", str(db_path))
    return db_path


def test_create_and_verify_valid_token(isolated_auth):
    token = auth_utils.create_access_token(
        {"sub": "admin_test", "role": "Member"}
    )
    user = asyncio.run(auth_utils.get_current_user(token))
    assert user["username"] == "admin_test"
    assert user["role"] == "Admin"
    assert isinstance(user["id"], int)


def test_verify_invalid_token(isolated_auth):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth_utils.get_current_user("invalid.token.signature"))
    assert exc_info.value.status_code == 401


def test_verify_expired_token(isolated_auth):
    expired_token = auth_utils.create_access_token(
        {"sub": "normal_test"},
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth_utils.get_current_user(expired_token))
    assert exc_info.value.status_code == 401


def test_verify_deleted_user(isolated_auth):
    token = auth_utils.create_access_token({"sub": "missing_user"})
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth_utils.get_current_user(token))
    assert exc_info.value.status_code == 401


def test_missing_secret_fails_closed(isolated_auth, monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        auth_utils.create_access_token({"sub": "admin_test"})


def test_require_admin_success(isolated_auth):
    admin_user = {"id": 1, "username": "admin_test", "role": "Admin"}
    assert asyncio.run(auth_utils.require_admin(admin_user)) == admin_user


def test_require_admin_forbidden_for_normal_user(isolated_auth):
    normal_user = {"id": 2, "username": "normal_test", "role": "Member"}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth_utils.require_admin(normal_user))
    assert exc_info.value.status_code == 403
