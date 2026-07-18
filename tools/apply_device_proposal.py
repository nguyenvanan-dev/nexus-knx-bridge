#!/usr/bin/env python3
"""Apply KNX device proposal to SQLite device registry.

Usage:
    python3 tools/apply_device_proposal.py proposal.json --dry-run
    python3 tools/apply_device_proposal.py proposal.json --confirm
"""
import argparse
import json
import re
import shutil
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path.home() / "knx-bridge"
DB_PATH = BASE_DIR / "smarthome.db"


def _safe_device_id(dev: dict) -> str:
    """Generate a safe device_id from name/room/type if not provided."""
    did = dev.get("device_id", "").strip()
    if did:
        return did
    parts = []
    for key in ("room", "type", "name"):
        val = dev.get(key, "")
        if val:
            parts.append(re.sub(r"[^a-z0-9]+", "_", str(val).lower().strip()))
    return "_".join(parts) or f"device_{int(time.time())}"


def _extract_any_ga(dev: dict) -> list[str]:
    """Extract all group addresses from a device dict, including nested."""
    gas = []
    for key in ("onoff_ga", "status_ga", "brightness_ga", "brightness_status_ga",
                 "color_ga", "color_status_ga"):
        val = dev.get(key)
        if val:
            gas.append(val)

    # Check functions list
    for fn in dev.get("functions", []):
        ga = fn.get("group_address")
        if ga:
            gas.append(ga)

    # Check capabilities nested dicts
    caps = dev.get("capabilities", {})
    if isinstance(caps, dict):
        for cap_name, cap_val in caps.items():
            if isinstance(cap_val, dict):
                for k, v in cap_val.items():
                    if k.endswith("_ga") or k == "write_ga" or k == "status_ga":
                        if v:
                            gas.append(v)
    return gas


def _validate_device(dev: dict) -> tuple[bool, str]:
    """Validate minimum required fields."""
    if not dev.get("name"):
        return False, "missing name"
    if not dev.get("type"):
        return False, "missing type"
    gas = _extract_any_ga(dev)
    if not gas:
        return False, "no group address found"
    return True, "ok"


def main():
    parser = argparse.ArgumentParser(
        description="Apply KNX device proposal to SQLite device registry"
    )
    parser.add_argument("proposal", help="Path to proposal JSON")
    parser.add_argument("--confirm", action="store_true",
                        help="Required to write to SQLite DB")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying DB")
    args = parser.parse_args()

    if not args.confirm and not args.dry_run:
        raise SystemExit(
            "Thiếu --confirm hoặc --dry-run.\n"
            "  --dry-run   Xem trước thay đổi, không sửa DB\n"
            "  --confirm   Ghi thật vào SQLite device registry"
        )

    if args.confirm and args.dry_run:
        raise SystemExit("Không thể dùng --confirm và --dry-run cùng lúc.")

    proposal_path = Path(args.proposal).expanduser().resolve()
    if not proposal_path.exists():
        raise SystemExit(f"Không tìm thấy proposal: {proposal_path}")

    if not DB_PATH.exists():
        raise SystemExit(f"Không tìm thấy database: {DB_PATH}")

    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposed = proposal.get("proposed_devices", [])
    ready = [d for d in proposed if d.get("status") == "ready"]

    if not ready:
        raise SystemExit("Không có thiết bị status=ready để thêm.")

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] Proposal: {proposal_path}")
    print(f"[{mode}] Database: {DB_PATH}")
    print(f"[{mode}] Devices ready: {len(ready)}")
    print()

    added = 0
    updated = 0
    skipped = []

    for dev in ready:
        dev["device_id"] = _safe_device_id(dev)
        valid, reason = _validate_device(dev)
        if not valid:
            skipped.append((dev["device_id"], reason))
            print(f"  SKIP: {dev['device_id']} ({reason})")
            continue

        # Build knx_config_payload from capabilities/functions
        payload = {}
        if dev.get("capabilities"):
            payload = dev["capabilities"]
        elif dev.get("functions"):
            payload["functions"] = dev["functions"]

        prefix = "WOULD " if args.dry_run else ""
        print(f"  {prefix}UPSERT: {dev['device_id']} "
              f"| name={dev.get('name')} | type={dev.get('type')} "
              f"| room={dev.get('room', 'N/A')}")
        if args.dry_run:
            added += 1
        # Actual insert handled below

    if args.dry_run:
        print(f"\n[DRY-RUN] Would add/update {added} devices, skip {len(skipped)}")
        print("[DRY-RUN] Không tạo backup. Không sửa DB.")
        print("[DRY-RUN] Không cập nhật devices.json.")
        return

    # === APPLY MODE ===
    backup_path = DB_PATH.with_name(
        f"smarthome.db.bak.apply_proposal.{int(time.time())}"
    )
    shutil.copy2(DB_PATH, backup_path)
    print(f"\nBackup: {backup_path}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(devices)")
    columns = [col[1] for col in cursor.fetchall()]

    try:
        for dev in ready:
            dev["device_id"] = _safe_device_id(dev)
            valid, reason = _validate_device(dev)
            if not valid:
                continue

            payload = {}
            if dev.get("capabilities"):
                payload = dev["capabilities"]
            elif dev.get("functions"):
                payload["functions"] = dev["functions"]

            payload_json = json.dumps(payload, ensure_ascii=False) if payload else "{}"

            # Check if device exists
            cursor.execute(
                "SELECT device_id FROM devices WHERE device_id = ?",
                (dev["device_id"],)
            )
            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE devices SET
                        name = ?,
                        type = ?,
                        room = ?,
                        onoff_ga = ?,
                        status_ga = ?,
                        supports_brightness = ?,
                        brightness_ga = ?,
                        brightness_status_ga = ?,
                        knx_config_payload = ?,
                        enabled = 1
                    WHERE device_id = ?
                """, (
                    dev.get("name"),
                    dev.get("type"),
                    dev.get("room"),
                    dev.get("onoff_ga"),
                    dev.get("status_ga"),
                    1 if dev.get("supports_brightness") else 0,
                    dev.get("brightness_ga"),
                    dev.get("brightness_status_ga"),
                    payload_json,
                    dev["device_id"],
                ))
                updated += 1
            else:
                aliases_json = json.dumps(dev.get("aliases", []), ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO devices (
                        device_id, name, type, room,
                        onoff_ga, status_ga,
                        supports_brightness, brightness_ga, brightness_status_ga,
                        aliases, require_confirm, enabled,
                        knx_config_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)
                """, (
                    dev["device_id"],
                    dev.get("name"),
                    dev.get("type"),
                    dev.get("room"),
                    dev.get("onoff_ga"),
                    dev.get("status_ga"),
                    1 if dev.get("supports_brightness") else 0,
                    dev.get("brightness_ga"),
                    dev.get("brightness_status_ga"),
                    aliases_json,
                    payload_json,
                ))
                added += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Lỗi khi ghi DB: {e}")
    finally:
        conn.close()

    print(f"\n[APPLY] Added: {added}, Updated: {updated}, Skipped: {len(skipped)}")
    print(f"[APPLY] Backup DB: {backup_path}")
    print("[APPLY] Không cập nhật devices.json.")
    print("[APPLY] Không KNX write. Không restart service.")


if __name__ == "__main__":
    main()
