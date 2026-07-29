import sqlite3

import pytest

from app import (
    _backup_sqlite_database,
    _database_admin_authorizer,
    _redact_database_admin_row,
    _validate_database_admin_query,
)


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE devices SET enabled = 0",
        "DELETE FROM devices",
        "PRAGMA table_info(devices)",
        "SELECT * FROM devices; DELETE FROM devices",
        "SELECT * FROM devices -- bypass",
    ],
)
def test_database_admin_rejects_unsafe_queries(query):
    with pytest.raises(ValueError):
        _validate_database_admin_query(query)


def test_database_admin_allows_approved_read_and_redacts_secrets():
    query = _validate_database_admin_query("SELECT device_id FROM devices LIMIT 1")
    assert query.startswith("SELECT")
    assert _redact_database_admin_row(
        {"device_id": "light_1", "api_token": "secret", "password_hash": "hash"}
    ) == {
        "device_id": "light_1",
        "api_token": "[REDACTED]",
        "password_hash": "[REDACTED]",
    }


def test_database_admin_authorizer_blocks_unapproved_tables(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE devices (device_id TEXT)")
        conn.execute("CREATE TABLE users (username TEXT, password_hash TEXT)")
        conn.execute("INSERT INTO devices VALUES ('light_1')")
        conn.execute("INSERT INTO users VALUES ('admin', 'secret')")
        conn.commit()
        conn.set_authorizer(_database_admin_authorizer)
        assert conn.execute("SELECT device_id FROM devices").fetchone() == ("light_1",)
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("SELECT username FROM users").fetchall()
        conn.set_authorizer(None)


def test_database_admin_authorizer_blocks_sensitive_source_columns(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE devices (device_id TEXT, api_token TEXT)")
        conn.execute("INSERT INTO devices VALUES ('light_1', 'not-a-real-secret')")
        conn.commit()
        conn.set_authorizer(_database_admin_authorizer)
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("SELECT hex(api_token) AS value FROM devices").fetchall()
        conn.set_authorizer(None)


def test_sqlite_backup_includes_committed_wal_data(tmp_path):
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"

    with sqlite3.connect(source) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE devices (device_id TEXT)")
        conn.execute("INSERT INTO devices VALUES ('light_1')")
        conn.commit()
        _backup_sqlite_database(source, destination)

    with sqlite3.connect(destination) as backup:
        assert backup.execute("SELECT device_id FROM devices").fetchall() == [("light_1",)]
