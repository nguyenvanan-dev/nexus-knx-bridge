#!/usr/bin/env python3
import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


DEVICE_JSON = Path.home() / "knx-bridge" / "devices.json"


def backup_devices():
    backup = DEVICE_JSON.with_name(
        f"devices.json.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(DEVICE_JSON, backup)
    return backup


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Apply KNX device proposal to devices.json")
    parser.add_argument("proposal", help="Path to proposal JSON")
    parser.add_argument("--confirm", action="store_true", help="Required to write devices.json")
    args = parser.parse_args()

    if not args.confirm:
        raise SystemExit("Thiếu --confirm. Tool không ghi devices.json nếu chưa xác nhận.")

    proposal_path = Path(args.proposal).expanduser().resolve()

    if not proposal_path.exists():
        raise SystemExit(f"Không tìm thấy proposal: {proposal_path}")

    if not DEVICE_JSON.exists():
        raise SystemExit(f"Không tìm thấy devices.json: {DEVICE_JSON}")

    proposal = load_json(proposal_path)
    devices_data = load_json(DEVICE_JSON)

    proposed = proposal.get("proposed_devices", [])
    ready = [d for d in proposed if d.get("status") == "ready"]

    if not ready:
        raise SystemExit("Không có thiết bị status=ready để thêm.")

    backup = backup_devices()

    if isinstance(devices_data, list):
        devices_data.extend(ready)
    elif isinstance(devices_data, dict):
        if "devices" not in devices_data:
            devices_data["devices"] = []
        if not isinstance(devices_data["devices"], list):
            raise SystemExit("devices.json có key devices nhưng không phải list.")
        devices_data["devices"].extend(ready)
    else:
        raise SystemExit("devices.json không phải list hoặc dict.")

    save_json(DEVICE_JSON, devices_data)

    # Validate JSON after write
    load_json(DEVICE_JSON)

    print("OK: Đã cập nhật devices.json")
    print(f"Backup: {backup}")
    print(f"Added ready devices: {len(ready)}")
    print(f"devices.json: {DEVICE_JSON}")


if __name__ == "__main__":
    main()
