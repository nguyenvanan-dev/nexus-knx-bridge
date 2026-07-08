import json
import time
import sqlite3
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.device_service import DeviceService
    from core.event_bus import EventBus
    from pathlib import Path

logger = logging.getLogger(__name__)

class ContextBuilder:
    def __init__(self, device_service: "DeviceService", event_bus: "EventBus", db_path: "Path"):
        self._device_service = device_service
        self._bus = event_bus
        self._db_path = db_path

    def build_context(self) -> str:
        """Xây dựng chuỗi ngữ cảnh realtime để tiêm vào AI."""
        context = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "house_mode": self._get_house_mode(),
            "devices": self._get_device_snapshot(),
            "recent_events": self._get_recent_events(limit=5)
        }
        return json.dumps(context, ensure_ascii=False)


    def _get_house_mode(self) -> str:
        return self._device_service.get_house_mode()

    def _get_device_snapshot(self) -> dict:
        """Lấy danh sách thiết bị và trạng thái hiện tại từ DeviceService."""
        return self._device_service.get_all_devices_with_state()

    def _get_recent_events(self, limit: int = 5) -> list[dict]:
        """Lấy sự kiện điều khiển gần nhất từ command_audit."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT who, device_id, action, new_value, result, timestamp 
                FROM command_audit 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for r in rows:
                events.append({
                    "device": r["device_id"],
                    "action": r["action"],
                    "value": r["new_value"],
                    "by": r["who"],
                    "result": r["result"],
                    # Convert float timestamp to human readable relative time or just leave it
                })
            return events
        except Exception as e:
            logger.warning(f"Không thể lấy recent events cho AI Context: {e}")
            return []

