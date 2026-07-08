"""
HealthService — Thu thập metrics từ toàn bộ hệ thống.

Không có dependency vào bất kỳ module nào — chỉ nhận references qua constructor.
"""
from __future__ import annotations

import time
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.state_manager import StateManager
    from core.device_registry import DeviceRegistry
    from core.event_bus import EventBus
    from core.command_pipeline import CommandPipeline
    from core.automation_engine import AutomationEngine


class HealthService:
    def __init__(
        self,
        state_manager: "StateManager",
        device_registry: "DeviceRegistry",
        event_bus: "EventBus",
        command_pipeline: "CommandPipeline",
        automation_engine: "AutomationEngine",
        raw_queue: asyncio.Queue,
        event_queue: asyncio.Queue,
        sse_event_clients: list,
        sse_bus_clients: list,
        get_knx_status_fn,   # Callable → dict
    ):
        self._state = state_manager
        self._registry = device_registry
        self._bus = event_bus
        self._pipeline = command_pipeline
        self._automation = automation_engine
        self._raw_queue = raw_queue
        self._event_queue = event_queue
        self._sse_event_clients = sse_event_clients
        self._sse_bus_clients = sse_bus_clients
        self._get_knx_status = get_knx_status_fn
        self._startup_time = time.time()
        self._last_telegram_at: Optional[float] = None

    def record_telegram(self):
        self._last_telegram_at = time.time()

    async def get_detail(self) -> dict:
        """Trả về toàn bộ health metrics."""
        import psutil
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            mem_mb = round(mem.used / 1024 / 1024, 1)
            mem_total_mb = round(mem.total / 1024 / 1024, 1)
        except Exception:
            cpu = -1
            mem_mb = -1
            mem_total_mb = -1

        knx_status = self._get_knx_status()

        return {
            "knx": {
                **knx_status,
                "last_telegram_at": self._last_telegram_at,
                "last_telegram_age_s": round(time.time() - self._last_telegram_at, 1) if self._last_telegram_at else None,
            },
            "queues": {
                "raw_telegram_queue_size": self._raw_queue.qsize(),
                "device_event_queue_size": self._event_queue.qsize(),
            },
            "sse": {
                "event_clients": len(self._sse_event_clients),
                "bus_clients": len(self._sse_bus_clients),
            },
            "state_manager": self._state.get_snapshot(),
            "device_registry": {
                "total_devices": self._registry.count(),
                "rooms": self._registry.rooms(),
                "types": self._registry.types(),
            },
            "event_bus": self._bus.get_stats(),
            "command_pipeline": self._pipeline.get_stats(),
            "automation_engine": self._automation.get_stats(),
            "system": {
                "uptime_seconds": round(time.time() - self._startup_time),
                "cpu_percent": cpu,
                "mem_used_mb": mem_mb,
                "mem_total_mb": mem_total_mb,
            },
        }
