"""
DeviceRegistry — Quản lý thiết bị thống nhất với full indexing.
Thay thế hoàn toàn dict DEVICES thô trong app.py.

Tất cả module chỉ làm việc với Registry, không ai đọc DB trực tiếp để tra cứu thiết bị.
"""
from __future__ import annotations

import json
import sqlite3
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Device:
    device_id: str
    name: str
    room: Optional[str] = None
    type: Optional[str] = None
    # KNX Group Addresses
    onoff_ga: Optional[str] = None
    status_ga: Optional[str] = None
    supports_brightness: bool = False
    brightness_ga: Optional[str] = None
    brightness_status_ga: Optional[str] = None
    color_ga: Optional[str] = None
    color_status_ga: Optional[str] = None
    # Metadata
    role: Optional[str] = None
    aliases: list[str] = field(default_factory=list)
    safety_level: Optional[str] = None  # "low" / "medium" / "high" / "critical"
    require_confirm: bool = False
    enabled: bool = True
    knx_config_payload: Optional[str] = None
    capabilities: dict = field(default_factory=dict)

    def all_gas(self) -> list[str]:
        """Trả về tất cả Group Addresses của thiết bị này."""
        gas = []
        for attr in ("onoff_ga", "status_ga", "brightness_ga",
                     "brightness_status_ga", "color_ga", "color_status_ga"):
            val = getattr(self, attr)
            if val:
                gas.append(val)

        # Index all GAs in capabilities payload
        def extract_gas(d: Any):
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(k, str) and (k.endswith("_ga") or k in ("write_ga", "status_ga")):
                        if isinstance(v, str) and v:
                            gas.append(v)
                    elif isinstance(v, (dict, list)):
                        extract_gas(v)
            elif isinstance(d, list):
                for item in d:
                    extract_gas(item)

        if self.capabilities:
            extract_gas(self.capabilities)

        # Deduplicate and filter out empties
        return list(set(g for g in gas if g))

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "type": self.type,
            "onoff_ga": self.onoff_ga,
            "status_ga": self.status_ga,
            "supports_brightness": self.supports_brightness,
            "brightness_ga": self.brightness_ga,
            "brightness_status_ga": self.brightness_status_ga,
            "color_ga": self.color_ga,
            "color_status_ga": self.color_status_ga,
            "role": self.role,
            "aliases": self.aliases,
            "safety_level": self.safety_level,
            "require_confirm": self.require_confirm,
            "enabled": self.enabled,
            "knx_config_payload": self.knx_config_payload,
            "capabilities": self.capabilities,
        }


class DeviceRegistry:
    """
    Nguồn dữ liệu duy nhất (Single Source of Truth) cho metadata thiết bị.

    - Đọc từ SQLite một lần khi khởi động (hoặc khi reload() được gọi).
    - Lưu vào RAM với các index để tra cứu O(1).
    - Không bao giờ ghi DB (đó là việc của các API endpoints khác).
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._devices: dict[str, Device] = {}       # device_id → Device
        self._ga_index: dict[str, str] = {}          # ga_string → device_id
        self._alias_index: dict[str, str] = {}       # alias_lower → device_id
        self._room_index: dict[str, list[str]] = {}  # room_lower → [device_id, ...]
        self._type_index: dict[str, list[str]] = {}  # type → [device_id, ...]

    def reload(self) -> int:
        """
        Đọc toàn bộ thiết bị từ SQLite và build lại tất cả index.
        Trả về số lượng thiết bị đã load.
        """
        if not self._db_path.exists():
            logger.warning("DeviceRegistry: database file not found at %s", self._db_path)
            return 0

        devices: dict[str, Device] = {}
        ga_index: dict[str, str] = {}
        alias_index: dict[str, str] = {}
        room_index: dict[str, list[str]] = {}
        type_index: dict[str, list[str]] = {}

        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices")
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            logger.error("DeviceRegistry: failed to load from SQLite: %s", e)
            return 0

        for row in rows:
            d = dict(row)
            aliases_raw = d.get("aliases") or "[]"
            try:
                aliases = json.loads(aliases_raw) if isinstance(aliases_raw, str) else aliases_raw
            except Exception:
                aliases = []

            # Parse knx_config_payload
            knx_config_payload_raw = d.get("knx_config_payload") or "{}"
            try:
                payload = json.loads(knx_config_payload_raw) if isinstance(knx_config_payload_raw, str) else knx_config_payload_raw
            except Exception:
                payload = {}

            if not isinstance(payload, dict):
                payload = {}

            # If payload has key "capabilities", use it
            if "capabilities" in payload:
                capabilities = payload["capabilities"]
            else:
                capabilities = payload

            if not isinstance(capabilities, dict):
                capabilities = {}

            device = Device(
                device_id=d["device_id"],
                name=d.get("name", "Unknown"),
                room=d.get("room"),
                type=d.get("type"),
                onoff_ga=d.get("onoff_ga"),
                status_ga=d.get("status_ga"),
                supports_brightness=bool(d.get("supports_brightness", False)),
                brightness_ga=d.get("brightness_ga"),
                brightness_status_ga=d.get("brightness_status_ga"),
                color_ga=d.get("color_ga"),
                color_status_ga=d.get("color_status_ga"),
                role=d.get("role"),
                aliases=aliases if isinstance(aliases, list) else [],
                safety_level=d.get("safety_level"),
                require_confirm=bool(d.get("require_confirm", False)),
                enabled=bool(d.get("enabled", True)),
                knx_config_payload=knx_config_payload_raw if isinstance(knx_config_payload_raw, str) else json.dumps(knx_config_payload_raw, ensure_ascii=False),
                capabilities=capabilities
            )

            devices[device.device_id] = device

            # Build GA index (all GAs → device_id)
            for ga in device.all_gas():
                if ga:
                    ga_index[ga] = device.device_id

            # Build alias index (lowercase)
            for alias in device.aliases:
                alias_index[alias.lower().strip()] = device.device_id
            # Also index name itself
            alias_index[device.name.lower().strip()] = device.device_id

            # Build room index
            if device.room:
                room_key = device.room.lower().strip()
                room_index.setdefault(room_key, []).append(device.device_id)

            # Build type index
            if device.type:
                type_index.setdefault(device.type, []).append(device.device_id)

        # Atomic swap
        self._devices = devices
        self._ga_index = ga_index
        self._alias_index = alias_index
        self._room_index = room_index
        self._type_index = type_index

        logger.info("DeviceRegistry: loaded %d devices", len(devices))
        return len(devices)

    # ──────────────────────────────────────────────
    # Lookup methods (all O(1) except find_by_room/type)
    # ──────────────────────────────────────────────

    def get(self, device_id: str) -> Optional[Device]:
        """Tra cứu thiết bị theo device_id."""
        return self._devices.get(device_id)

    def find_by_ga(self, ga: str) -> Optional[Device]:
        """Tra cứu thiết bị theo Group Address. O(1)."""
        device_id = self._ga_index.get(ga)
        return self._devices.get(device_id) if device_id else None

    def find_by_alias(self, alias: str) -> Optional[Device]:
        """Tra cứu thiết bị theo tên hoặc alias (case-insensitive). O(1)."""
        device_id = self._alias_index.get(alias.lower().strip())
        return self._devices.get(device_id) if device_id else None

    def find_by_room(self, room: str) -> list[Device]:
        """Lấy tất cả thiết bị trong một phòng."""
        ids = self._room_index.get(room.lower().strip(), [])
        return [self._devices[did] for did in ids if did in self._devices]

    def find_by_type(self, device_type: str) -> list[Device]:
        """Lấy tất cả thiết bị theo loại (light, sensor, curtain...)."""
        ids = self._type_index.get(device_type, [])
        return [self._devices[did] for did in ids if did in self._devices]

    def all(self) -> list[Device]:
        """Trả về tất cả thiết bị."""
        return list(self._devices.values())

    def all_dict(self) -> dict[str, Device]:
        """Trả về dict device_id → Device (tương thích với DEVICES cũ)."""
        return dict(self._devices)

    def validate(self, device_id: str) -> bool:
        """Kiểm tra device_id có tồn tại và đang enabled."""
        device = self._devices.get(device_id)
        return device is not None and device.enabled

    def count(self) -> int:
        return len(self._devices)

    def rooms(self) -> list[str]:
        return list(self._room_index.keys())

    def types(self) -> list[str]:
        return list(self._type_index.keys())
