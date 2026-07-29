import importlib.util
import json
import sqlite3
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "migrate_scenes_json.py"
SPEC = importlib.util.spec_from_file_location("migrate_scenes_json", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def create_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE devices (device_id TEXT PRIMARY KEY);
        CREATE TABLE scenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE scene_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER,
            device_id TEXT,
            action TEXT,
            value TEXT,
            delay_seconds REAL DEFAULT 0.0,
            condition_json TEXT,
            retry_count INTEGER DEFAULT 0,
            timeout_seconds REAL DEFAULT 30.0,
            comment TEXT,
            enabled BOOLEAN DEFAULT 1
        );
        CREATE TABLE scene_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER,
            actions_json TEXT,
            updated_at REAL
        );
        INSERT INTO devices (device_id) VALUES ('light_1');
        """
    )
    conn.commit()
    conn.close()


def create_source(path):
    path.write_text(
        json.dumps(
            {
                "Evening": {
                    "description": "Test scene",
                    "actions": [
                        {"device": "light_1", "action": "on"},
                        {
                            "device": "light_1",
                            "action": "color_temperature",
                            "value": 2700,
                        },
                    ],
                }
            }
        ),
        encoding="utf-8",
    )


def test_dry_run_does_not_modify_database(tmp_path):
    db_path = tmp_path / "test.db"
    source = tmp_path / "scenes.json"
    create_db(db_path)
    create_source(source)

    assert MODULE.migrate(source, db_path) == 0
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT count(*) FROM scenes").fetchone()[0] == 0
    conn.close()
    assert not list(tmp_path.glob("*.bak.scenes.*"))


def test_confirm_imports_scene_actions_and_version(tmp_path):
    db_path = tmp_path / "test.db"
    source = tmp_path / "scenes.json"
    create_db(db_path)
    create_source(source)

    assert MODULE.migrate(source, db_path, confirm=True) == 0
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT count(*) FROM scenes").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM scene_actions").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM scene_versions").fetchone()[0] == 1
    conn.close()
    assert len(list(tmp_path.glob("*.bak.scenes.*"))) == 1


def test_unknown_device_blocks_migration(tmp_path):
    db_path = tmp_path / "test.db"
    source = tmp_path / "scenes.json"
    create_db(db_path)
    source.write_text(
        json.dumps(
            {
                "Broken": {
                    "actions": [{"device": "missing", "action": "on"}]
                }
            }
        ),
        encoding="utf-8",
    )

    assert MODULE.migrate(source, db_path) == 2
