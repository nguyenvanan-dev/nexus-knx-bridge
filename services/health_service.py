"""
HealthService — Thu thập metrics từ toàn bộ hệ thống.

Không có dependency vào bất kỳ module nào — chỉ nhận references qua constructor.
"""
from __future__ import annotations

import time
import asyncio
from typing import TYPE_CHECKING, Optional

try:
    from config import DEVICE_OFFLINE_TIMEOUT
except ImportError:
    DEVICE_OFFLINE_TIMEOUT = 300

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
        import os
        import subprocess
        from datetime import datetime

        # API Version & Build Info
        try:
            git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        except Exception:
            git_commit = "unknown"
        
        build_time = "2026-07-09T10:15:00Z" # Dummy fallback
        try:
            build_time = subprocess.check_output(["git", "log", "-1", "--format=%cI"], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        except Exception:
            pass

        # Read CPU / Load Average without psutil
        try:
            load1, load5, load15 = os.getloadavg()
            cpu_percent = round(load1 / os.cpu_count() * 100, 1)
        except Exception:
            cpu_percent = -1

        # Read Mem from /proc/meminfo
        mem_mb = -1
        mem_total_mb = -1
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            total_kb = 0
            free_kb = 0
            avail_kb = 0
            for line in meminfo.splitlines():
                if line.startswith('MemTotal:'):
                    total_kb = int(line.split()[1])
                elif line.startswith('MemFree:'):
                    free_kb = int(line.split()[1])
                elif line.startswith('MemAvailable:'):
                    avail_kb = int(line.split()[1])
            
            if total_kb > 0:
                mem_total_mb = round(total_kb / 1024, 1)
                # Use MemAvailable if present, else fallback to MemFree
                used_kb = total_kb - (avail_kb if avail_kb > 0 else free_kb)
                mem_mb = round(used_kb / 1024, 1)
        except Exception:
            pass

        # Process Memory (Resident Set Size) from /proc/self/statm
        process_mem_mb = -1
        try:
            with open('/proc/self/statm', 'r') as f:
                pages = int(f.read().split()[1])
                page_size = os.sysconf('SC_PAGE_SIZE')
                process_mem_mb = round((pages * page_size) / 1024 / 1024, 1)
        except Exception:
            pass

        # Offline devices (Not updated in 2 hours = 7200s, or never updated)
        offline_devices = []
        now = time.time()
        for d in self._registry.all():
            did = d.device_id
            state = self._state.get(did)
            if state:
                age = now - state.last_update
                if age > DEVICE_OFFLINE_TIMEOUT:
                    offline_devices.append({
                        "id": did,
                        "name": d.name or did,
                        "room": d.room or "Unknown",
                        "last_update_age_s": round(age),
                        "status": "Offline"
                    })
            else:
                # Never reported
                offline_devices.append({
                    "id": did,
                    "name": d.name or did,
                    "room": d.room or "Unknown",
                    "last_update_age_s": None,
                    "status": "No Data"
                })

        # Prefer the configured service log; fall back to systemd journal.
        recent_logs = []
        log_path = os.getenv("KNX_BACKEND_LOG", "/var/log/knx-bridge.log")
        try:
            tail_output = subprocess.check_output(
                ["tail", "-n", "20", log_path],
                stderr=subprocess.DEVNULL,
            )
            recent_logs = tail_output.decode("utf-8").splitlines()
        except Exception:
            try:
                journal_output = subprocess.check_output(
                    ["journalctl", "-u", "knx-bridge.service", "-n", "20",
                     "--no-pager", "-o", "cat"],
                    stderr=subprocess.DEVNULL,
                )
                recent_logs = journal_output.decode("utf-8").splitlines()
            except Exception:
                recent_logs = ["Backend service logs are unavailable."]

        knx_status = self._get_knx_status()

        # Overall Status
        overall_status = "HEALTHY"
        if not knx_status.get("connected") or process_mem_mb == -1:
            overall_status = "ERROR"
        elif len(offline_devices) > 0:
            overall_status = "WARNING"

        return {
            "version": {
                "version": "v0.9.0",
                "git_commit": git_commit,
                "build_time": build_time,
            },
            "overall_status": overall_status,
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
                "cpu_percent": cpu_percent,
                "mem_used_mb": mem_mb,
                "mem_total_mb": mem_total_mb,
                "process_mem_mb": process_mem_mb,
            },
            "offline_devices": offline_devices,
            "recent_logs": recent_logs,
        }
