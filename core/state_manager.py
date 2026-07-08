"""
StateManager — Nguồn trạng thái duy nhất trong RAM.

Mọi module chỉ đọc StateManager để biết trạng thái thiết bị.
KHÔNG AI đọc DB để lấy trạng thái hiện tại.
DB chỉ là lịch sử (history), không phải trạng thái (state).
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DeviceState:
    """Trạng thái hiện tại của một thiết bị — lưu trong RAM."""
    device_id: str
    state: str                          # "ON" / "OFF" / "26.5" / "75"
    previous_state: Optional[str] = None
    brightness: Optional[int] = None    # 0–100 nếu là dimmer
    temperature: Optional[float] = None # Celsius nếu là sensor nhiệt
    position: Optional[int] = None      # 0–100 nếu là rèm/cửa
    source: str = "Unknown"             # "KNX Bus" / "Dashboard/AI" / "Automation" / "Schedule"
    last_update: float = field(default_factory=time.time)
    update_count: int = 0               # tổng số lần cập nhật kể từ khi startup

    def is_stale(self, threshold_seconds: float = 300.0) -> bool:
        """Trả về True nếu trạng thái không được cập nhật trong threshold_seconds."""
        return (time.time() - self.last_update) > threshold_seconds

    def age_seconds(self) -> float:
        return time.time() - self.last_update

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "state": self.state,
            "previous_state": self.previous_state,
            "brightness": self.brightness,
            "temperature": self.temperature,
            "position": self.position,
            "source": self.source,
            "last_update": self.last_update,
            "update_count": self.update_count,
            "age_seconds": round(self.age_seconds(), 1),
        }


class StateManager:
    """
    Quản lý trạng thái runtime của tất cả thiết bị trong RAM.

    Thiết kế:
    - Thread-safe (asyncio single-thread, không cần Lock trong Python asyncio)
    - Không bao giờ đọc/ghi DB (đó là việc của AuditLogger / DBWriter)
    - Là nơi duy nhất quyết định "trạng thái hiện tại" của thiết bị
    """

    def __init__(self):
        self._states: dict[str, DeviceState] = {}
        self._total_updates: int = 0
        self._startup_time: float = time.time()

    def update(
        self,
        device_id: str,
        state: str,
        source: str = "Unknown",
        brightness: Optional[int] = None,
        temperature: Optional[float] = None,
        position: Optional[int] = None,
    ) -> DeviceState:
        """
        Cập nhật trạng thái thiết bị. Trả về DeviceState mới.
        Được gọi bởi: Telegram Parser, execute_action, Automation Engine.
        """
        existing = self._states.get(device_id)
        previous = existing.state if existing else None
        update_count = (existing.update_count + 1) if existing else 1

        new_state = DeviceState(
            device_id=device_id,
            state=state,
            previous_state=previous,
            brightness=brightness if brightness is not None else (existing.brightness if existing else None),
            temperature=temperature if temperature is not None else (existing.temperature if existing else None),
            position=position if position is not None else (existing.position if existing else None),
            source=source,
            last_update=time.time(),
            update_count=update_count,
        )

        self._states[device_id] = new_state
        self._total_updates += 1

        logger.debug(
            "StateManager: %s %s → %s (source=%s)",
            device_id, previous, state, source
        )
        return new_state

    def get(self, device_id: str) -> Optional[DeviceState]:
        """Lấy trạng thái hiện tại của thiết bị. Trả về None nếu chưa có."""
        return self._states.get(device_id)

    def get_state_str(self, device_id: str, default: str = "UNKNOWN") -> str:
        """Lấy chuỗi trạng thái, trả về default nếu chưa có."""
        s = self._states.get(device_id)
        return s.state if s else default

    def get_all(self) -> dict[str, DeviceState]:
        """Trả về toàn bộ snapshot trạng thái."""
        return dict(self._states)

    def get_by_room(self, device_ids: list[str]) -> dict[str, DeviceState]:
        """Lấy trạng thái của danh sách device_ids (dùng cùng DeviceRegistry)."""
        return {did: self._states[did] for did in device_ids if did in self._states}

    def get_snapshot(self) -> dict:
        """Trả về snapshot dạng dict cho Health Monitor."""
        states = list(self._states.values())
        stale = [s for s in states if s.is_stale(300)]
        return {
            "total_tracked": len(states),
            "stale_count": len(stale),
            "stale_devices": [s.device_id for s in stale],
            "total_updates_since_startup": self._total_updates,
            "uptime_seconds": round(time.time() - self._startup_time),
        }

    def has(self, device_id: str) -> bool:
        return device_id in self._states

    def remove(self, device_id: str):
        """Xóa trạng thái khi thiết bị bị disabled/removed."""
        self._states.pop(device_id, None)
