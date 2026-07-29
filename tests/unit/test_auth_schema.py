import sqlite3

import auth_utils


def test_ensure_auth_schema_creates_empty_users_table(tmp_path):
    db_path = tmp_path / "auth.db"

    auth_utils.ensure_auth_schema(db_path)

    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        user_count = conn.execute("SELECT count(*) FROM users").fetchone()[0]

    assert {
        "id",
        "username",
        "password_hash",
        "role",
        "created_at",
    }.issubset(columns)
    assert user_count == 0


def test_ensure_auth_schema_is_idempotent(tmp_path):
    db_path = tmp_path / "auth.db"

    auth_utils.ensure_auth_schema(db_path)
    auth_utils.ensure_auth_schema(db_path)

    with sqlite3.connect(db_path) as conn:
        table_count = conn.execute(
            """
            SELECT count(*) FROM sqlite_master
            WHERE type='table' AND name='users'
            """
        ).fetchone()[0]

    assert table_count == 1
