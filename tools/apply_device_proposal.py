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
    """Extract all group addresses from a device dict, including nested capabilities and raw fields."""
    gas = []

    # Top-level & legacy_fields
    for key in ("onoff_ga", "status_ga", "brightness_ga", "brightness_status_ga",
                "color_ga", "color_status_ga", "color_rgb_ga", "color_temp_ga"):
        # Top-level
        val = dev.get(key)
        if val:
            gas.append(val)
        # legacy_fields
        val_legacy = dev.get("legacy_fields", {}).get(key)
        if val_legacy:
            gas.append(val_legacy)

    # Check functions list
    for fn in dev.get("functions", []):
        ga = fn.get("group_address")
        if ga:
            gas.append(ga)

    # Check capabilities nested dicts
    caps = dev.get("capabilities", {})
    if not caps and "knx_config_payload" in dev:
        payload = dev["knx_config_payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if isinstance(payload, dict):
            caps = payload.get("capabilities", {})

    if isinstance(caps, dict):
        for cap_name, cap_val in caps.items():
            if isinstance(cap_val, dict):
                for k, v in cap_val.items():
                    if k.endswith("_ga") or k == "write_ga" or k == "status_ga":
                        if v:
                            gas.append(v)

    # Raw GAs
    raw_gas = dev.get("knx_config_payload", {}).get("raw", {}).get("group_addresses", [])
    for rg in raw_gas:
        gas.append(rg)

    # Normalize GAs and unique
    normalized = []
    for ga in gas:
        if isinstance(ga, str) and ga.strip():
            ga_clean = ga.strip()
            parts = ga_clean.split("/")
            if len(parts) == 3:
                try:
                    normalized.append(f"{int(parts[0])}/{int(parts[1])}/{int(parts[2])}")
                except ValueError:
                    normalized.append(ga_clean)
            else:
                normalized.append(ga_clean)
    return sorted(list(set(normalized)))


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
    parser.add_argument("--include-needs-review", action="store_true",
                        help="Include needs_review status devices for import")
    parser.add_argument("--allow-duplicates", action="store_true",
                        help="Allow import even if duplicate group addresses are detected")
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

    # Select statuses to import
    allowed_statuses = ["ready"]
    if args.include_needs_review:
        allowed_statuses.append("needs_review")

    ready = [d for d in proposed if d.get("status") in allowed_statuses]

    if not ready:
        raise SystemExit(f"Không có thiết bị status thuộc {allowed_statuses} để thêm.")

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] Proposal: {proposal_path}")
    print(f"[{mode}] Database: {DB_PATH}")
    print(f"[{mode}] Devices selected: {len(ready)}")
    print()

    # === GATHER EXISTING GAs TO DETECT COLLISONS ===
    existing_ga_map = {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT device_id, name, onoff_ga, status_ga, brightness_ga, brightness_status_ga, color_ga, color_status_ga, knx_config_payload FROM devices WHERE enabled = 1")
        for row in cur.fetchall():
            row_dict = dict(row)
            # Find all GAs used by this existing device
            dev_gas = _extract_any_ga(row_dict)
            for g in dev_gas:
                existing_ga_map[g] = (row_dict["device_id"], row_dict["name"])
        conn.close()
    except Exception as e:
        print(f"Warning: Không thể kiểm tra trùng lặp GA từ DB: {e}")

    # Verify duplicate GAs inside proposal or against existing DB
    has_conflicts = False
    proposed_ga_map = {}

    for dev in ready:
        dev_id = _safe_device_id(dev)
        gas = _extract_any_ga(dev)
        for ga in gas:
            # Check internal proposal duplicates
            if ga in proposed_ga_map:
                print(f"TRÙNG LẶP NỘI BỘ: GA {ga} xuất hiện ở cả {proposed_ga_map[ga]} và {dev_id}")
                has_conflicts = True
            else:
                proposed_ga_map[ga] = dev_id

            # Check DB duplicates
            if ga in existing_ga_map:
                existing_id, existing_name = existing_ga_map[ga]
                if existing_id != dev_id:
                    print(f"TRÙNG LẶP DATABASE: GA {ga} đã được dùng bởi thiết bị '{existing_name}' ({existing_id}) trong DB")
                    has_conflicts = True

    if has_conflicts and not args.allow_duplicates:
        if args.confirm:
            raise SystemExit("Dừng tiến trình Apply do phát hiện trùng lặp địa chỉ nhóm (GA). Sử dụng --allow-duplicates nếu muốn bỏ qua.")
        else:
            print("\nCảnh báo: Phát hiện trùng lặp địa chỉ nhóm (GA) trong chế độ dry-run.")

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

        prefix = "WOULD " if args.dry_run else ""
        print(f"  {prefix}UPSERT: {dev['device_id']} "
              f"| name={dev.get('name')} | type={dev.get('type')} "
              f"| room={dev.get('room', 'N/A')}")
        if args.dry_run:
            added += 1

    if args.dry_run:
        print(f"\n[DRY-RUN] Would add/update {added} devices, skip {len(skipped)}")
        print("[DRY-RUN] Không tạo backup. Không sửa DB.")
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

    try:
        for dev in ready:
            dev["device_id"] = _safe_device_id(dev)
            valid, reason = _validate_device(dev)
            if not valid:
                continue

            # Fallback legacy fields mapping
            legacy = dev.get("legacy_fields", {})
            onoff_ga = dev.get("onoff_ga") or legacy.get("onoff_ga", "")
            status_ga = dev.get("status_ga") or legacy.get("status_ga", "")
            brightness_ga = dev.get("brightness_ga") or legacy.get("brightness_ga", "")
            brightness_status_ga = dev.get("brightness_status_ga") or legacy.get("brightness_status_ga", "")
            color_ga = dev.get("color_ga") or legacy.get("color_ga", "")
            color_status_ga = dev.get("color_status_ga") or legacy.get("color_status_ga", "")

            # Calculate supports_brightness
            supports_brightness = 1 if brightness_ga or dev.get("supports_brightness") or dev.get("type") == "dimmer" else 0

            # Capabilities payload json
            payload = dev.get("knx_config_payload", {})
            if isinstance(payload, str):
                payload_json = payload
            else:
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
                        color_ga = ?,
                        color_status_ga = ?,
                        knx_config_payload = ?,
                        enabled = 1
                    WHERE device_id = ?
                """, (
                    dev.get("name"),
                    dev.get("type"),
                    dev.get("room"),
                    onoff_ga,
                    status_ga,
                    supports_brightness,
                    brightness_ga,
                    brightness_status_ga,
                    color_ga,
                    color_status_ga,
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
                        color_ga, color_status_ga,
                        aliases, require_confirm, enabled,
                        knx_config_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)
                """, (
                    dev["device_id"],
                    dev.get("name"),
                    dev.get("type"),
                    dev.get("room"),
                    onoff_ga,
                    status_ga,
                    supports_brightness,
                    brightness_ga,
                    brightness_status_ga,
                    color_ga,
                    color_status_ga,
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
    print("[APPLY] Hoàn tất cập nhật SQLite device registry.")
    print("Vui lòng gọi endpoint reload (POST /api/platform/reload) hoặc gửi tín hiệu reload tới web admin để nạp cấu hình mới.")


if __name__ == "__main__":
    main()
