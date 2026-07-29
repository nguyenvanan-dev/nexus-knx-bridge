#!/usr/bin/env python3
import argparse
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "scenes.json"
DEFAULT_DB = PROJECT_ROOT / "smarthome.db"


def load_source(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scene source must be a JSON object.")
    return data


def validate_scene(name, scene, device_ids):
    errors = []
    if not isinstance(scene, dict):
        return [f"{name}: scene payload must be an object"]
    actions = scene.get("actions")
    if not isinstance(actions, list) or not actions:
        errors.append(f"{name}: actions must be a non-empty list")
        return errors

    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            errors.append(f"{name}: action {index} must be an object")
            continue
        device = action.get("device")
        verb = action.get("action")
        if not isinstance(device, str) or not device.strip():
            errors.append(f"{name}: action {index} has no device")
        elif device not in device_ids:
            errors.append(f"{name}: action {index} references unknown device '{device}'")
        if not isinstance(verb, str) or not verb.strip():
            errors.append(f"{name}: action {index} has no action")
    return errors


def migrate(source, db_path, confirm=False, replace=False):
    scenes = load_source(source)
    conn = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required = {"devices", "scenes", "scene_actions", "scene_versions"}
        missing = sorted(required - tables)
        if missing:
            raise RuntimeError(f"Missing database tables: {', '.join(missing)}")

        device_ids = {
            row[0] for row in conn.execute("SELECT device_id FROM devices")
        }
        existing_names = {
            row[0] for row in conn.execute("SELECT name FROM scenes")
        }

        errors = []
        for name, scene in scenes.items():
            errors.extend(validate_scene(name, scene, device_ids))
            if name in existing_names and not replace:
                errors.append(
                    f"{name}: scene already exists; use --replace to overwrite"
                )

        print(f"Source scenes: {len(scenes)}")
        print(f"Target database: {db_path}")
        print(f"Mode: {'APPLY' if confirm else 'DRY-RUN'}")
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 2

        action_count = sum(len(scene["actions"]) for scene in scenes.values())
        print(f"Validated scenes: {len(scenes)}")
        print(f"Validated actions: {action_count}")
        if not confirm:
            print("No backup created. Database was not modified.")
            return 0

        backup = db_path.with_name(
            f"{db_path.name}.bak.scenes.{int(time.time())}"
        )
        shutil.copy2(db_path, backup)
        print(f"Backup created: {backup}")

        with conn:
            for name, scene in scenes.items():
                existing = conn.execute(
                    "SELECT id FROM scenes WHERE name=?", (name,)
                ).fetchone()
                if existing:
                    scene_id = existing[0]
                    conn.execute(
                        "UPDATE scenes SET description=? WHERE id=?",
                        (scene.get("description", ""), scene_id),
                    )
                    conn.execute(
                        "DELETE FROM scene_actions WHERE scene_id=?", (scene_id,)
                    )
                else:
                    cursor = conn.execute(
                        "INSERT INTO scenes (name, description) VALUES (?, ?)",
                        (name, scene.get("description", "")),
                    )
                    scene_id = cursor.lastrowid

                version_actions = []
                for action in scene["actions"]:
                    value = action.get("value")
                    value_text = str(value) if value is not None else None
                    conn.execute(
                        """
                        INSERT INTO scene_actions
                        (scene_id, device_id, action, value, delay_seconds,
                         condition_json, retry_count, timeout_seconds, comment,
                         enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            scene_id,
                            action["device"],
                            action["action"],
                            value_text,
                            action.get("delay_seconds", 0.0),
                            action.get("condition_json"),
                            action.get("retry_count", 0),
                            action.get("timeout_seconds", 30.0),
                            action.get("comment"),
                            int(action.get("enabled", True)),
                        ),
                    )
                    version_actions.append(action)

                conn.execute(
                    """
                    INSERT INTO scene_versions
                    (scene_id, actions_json, updated_at) VALUES (?, ?, ?)
                    """,
                    (
                        scene_id,
                        json.dumps(version_actions, ensure_ascii=False),
                        time.time(),
                    ),
                )
        print(f"Imported scenes: {len(scenes)}")
        print(f"Imported actions: {action_count}")
        print("Source JSON was retained.")
        return 0
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Safely migrate legacy scenes.json data into SQLite."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Apply the migration. Without this flag, only validation runs.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace scenes with the same name; requires --confirm.",
    )
    args = parser.parse_args()

    if args.replace and not args.confirm:
        parser.error("--replace requires --confirm")
    if not args.source.is_file():
        parser.error(f"source file not found: {args.source}")
    if not args.db_path.is_file():
        parser.error(f"database file not found: {args.db_path}")

    try:
        return migrate(args.source, args.db_path, args.confirm, args.replace)
    except (OSError, ValueError, sqlite3.Error, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
