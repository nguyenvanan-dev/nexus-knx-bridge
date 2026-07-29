from pathlib import Path

from local_memory.db import DEFAULT_MEMORY_DB, MemoryStore, resolve_memory_db_path


def test_default_memory_path_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENT_MEMORY_DB", raising=False)

    assert resolve_memory_db_path() == DEFAULT_MEMORY_DB


def test_memory_path_can_be_overridden_for_isolated_tests(tmp_path, monkeypatch):
    database = tmp_path / "memory.sqlite3"
    monkeypatch.setenv("AGENT_MEMORY_DB", str(database))

    store = MemoryStore()

    assert Path(store.db_path) == database
    assert database.exists()
    assert database.stat().st_mode & 0o777 == 0o600
