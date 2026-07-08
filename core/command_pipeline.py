"""
CommandPipeline — Xử lý lệnh điều khiển theo thứ tự:
Permission → Validation → Priority → Execution → Verify → Audit

Mọi lệnh điều khiển (từ AI, Web UI, Automation, Schedule) đều phải đi qua đây.
Không ai gọi write_knx() trực tiếp nữa — gọi CommandPipeline.execute().
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.device_registry import DeviceRegistry, Device
    from core.state_manager import StateManager
    from core.event_bus import EventBus, DomainEvent

logger = logging.getLogger(__name__)


class CommandPriority(IntEnum):
    """Thứ tự ưu tiên lệnh. Số cao = ưu tiên cao hơn."""
    SCHEDULE   = 10   # Lệnh hẹn giờ
    AI         = 20   # AI đề xuất
    MANUAL     = 30   # Người dùng bấm Web UI
    AUTOMATION = 50   # Rule Engine
    SAFETY     = 80   # Khóa cửa, báo động
    EMERGENCY  = 99   # Cháy, thoát hiểm


@dataclass
class Command:
    """Đơn vị lệnh điều khiển."""
    device_id: str
    action: str                     # "on" / "off" / "brightness" / "set"
    value: Optional[Any] = None     # 0–100 cho brightness
    reason: Optional[str] = None
    who: str = "system"             # "user:admin" / "ai" / "automation:rule_id"
    priority: CommandPriority = CommandPriority.MANUAL
    command_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    issued_at: float = field(default_factory=time.time)


@dataclass
class CommandResult:
    """Kết quả thực thi lệnh."""
    command_id: str
    success: bool
    device_id: str
    action: str
    result_state: Optional[str] = None      # Trạng thái sau khi thực thi
    error: Optional[str] = None
    rejection_reason: Optional[str] = None  # Lý do từ chối nếu bị block
    latency_ms: Optional[int] = None        # Thời gian thực thi (ms)
    timestamp: float = field(default_factory=time.time)


# ──────────────────────────────────────────────
# Active Command Registry (chống xung đột priority)
# ──────────────────────────────────────────────
_active_commands: dict[str, Command] = {}  # device_id → lệnh đang chạy


class CommandPipeline:
    """
    Pipeline xử lý lệnh 6 bước:
    1. Permission Check
    2. Priority Conflict Check
    3. Validation
    4. Execution (write KNX)
    5. State Update
    6. Audit + Event publish
    """

    def __init__(
        self,
        registry: "DeviceRegistry",
        state_manager: "StateManager",
        event_bus: "EventBus",
        default_driver: "BaseDriver",
    ):
        self._registry = registry
        self._state = state_manager
        self._bus = event_bus
        self._driver = default_driver
        self._executed_count = 0
        self._rejected_count = 0
        self._failed_count = 0

    async def execute(self, command: Command) -> CommandResult:
        """Thực thi lệnh qua toàn bộ pipeline."""
        from core.event_bus import DomainEvent, EventType
        start_time = time.time()

        # ── Bước 1: Validate device ──────────────────
        device = self._registry.get(command.device_id)
        if device is None:
            self._rejected_count += 1
            return CommandResult(
                command_id=command.command_id,
                success=False,
                device_id=command.device_id,
                action=command.action,
                rejection_reason=f"Device '{command.device_id}' không tồn tại",
            )

        if not device.enabled:
            self._rejected_count += 1
            return CommandResult(
                command_id=command.command_id,
                success=False,
                device_id=command.device_id,
                action=command.action,
                rejection_reason=f"Device '{command.device_id}' đang bị disabled",
            )

        # ── Bước 2: Permission check ──────────────────
        permission_result = self._check_permission(command, device)
        if permission_result:
            self._rejected_count += 1
            await self._bus.publish(DomainEvent(
                event_type=EventType.COMMAND_REJECTED,
                device_id=command.device_id,
                source=command.who,
                priority=int(command.priority),
                payload={
                    "command_id": command.command_id,
                    "action": command.action,
                    "reason": permission_result,
                    "who": command.who,
                }
            ))
            return CommandResult(
                command_id=command.command_id,
                success=False,
                device_id=command.device_id,
                action=command.action,
                rejection_reason=permission_result,
            )

        # ── Bước 3: Priority conflict check ──────────
        conflict = _active_commands.get(command.device_id)
        if conflict and conflict.priority > command.priority:
            self._rejected_count += 1
            reason = (
                f"Lệnh bị chặn: đang có lệnh ưu tiên cao hơn "
                f"({conflict.priority.name} > {command.priority.name}) "
                f"từ '{conflict.who}'"
            )
            return CommandResult(
                command_id=command.command_id,
                success=False,
                device_id=command.device_id,
                action=command.action,
                rejection_reason=reason,
            )

        # ── Bước 4: Execution ─────────────────────────
        _active_commands[command.device_id] = command
        try:
            await self._do_execute(command, device)
        except Exception as e:
            _active_commands.pop(command.device_id, None)
            self._failed_count += 1
            latency_ms = int((time.time() - start_time) * 1000)
            await self._bus.publish(DomainEvent(
                event_type=EventType.COMMAND_FAILED,
                device_id=command.device_id,
                source=command.who,
                payload={
                    "command_id": command.command_id,
                    "action": command.action,
                    "error": str(e),
                    "latency_ms": latency_ms,
                }
            ))
            return CommandResult(
                command_id=command.command_id,
                success=False,
                device_id=command.device_id,
                action=command.action,
                error=str(e),
                latency_ms=latency_ms,
            )
        finally:
            _active_commands.pop(command.device_id, None)

        # ── Bước 5: State update ──────────────────────
        act = command.action.lower()
        new_state = "UNKNOWN"
        brightness = None
        if act == "on":
            new_state = "ON"
        elif act == "off":
            new_state = "OFF"
        elif act == "brightness" and command.value is not None:
            new_state = f"{command.value}%"
            brightness = command.value

        self._state.update(
            device_id=command.device_id,
            state=new_state,
            source=command.who,
            brightness=brightness,
        )

        latency_ms = int((time.time() - start_time) * 1000)
        self._executed_count += 1

        # ── Bước 6: Publish events ────────────────────
        await self._bus.publish(DomainEvent(
            event_type=EventType.COMMAND_EXECUTED,
            device_id=command.device_id,
            source=command.who,
            priority=int(command.priority),
            payload={
                "command_id": command.command_id,
                "action": command.action,
                "value": command.value,
                "new_state": new_state,
                "reason": command.reason,
                "latency_ms": latency_ms,
                "who": command.who,
            }
        ))

        await self._bus.publish(DomainEvent(
            event_type=EventType.DEVICE_STATE_CHANGED,
            device_id=command.device_id,
            source=command.who,
            payload={
                "state": new_state,
                "brightness": brightness,
                "action": command.action,
                "source": command.who,
                "timestamp": time.time(),
            }
        ))

        logger.info(
            "CommandPipeline: [%s] %s %s → %s (%dms) by %s",
            command.command_id, command.device_id,
            command.action, new_state, latency_ms, command.who
        )

        return CommandResult(
            command_id=command.command_id,
            success=True,
            device_id=command.device_id,
            action=command.action,
            result_state=new_state,
            latency_ms=latency_ms,
        )

    def _check_permission(self, command: Command, device: "Device") -> Optional[str]:
        """
        Kiểm tra permission. Trả về None nếu OK, trả về lý do nếu bị từ chối.
        """
        safety = device.safety_level or "low"
        act = command.action.lower()

        # Critical devices (gate, main breaker) — chỉ MANUAL+ mới được
        if safety == "critical" and command.priority < CommandPriority.MANUAL:
            return (
                f"Thiết bị critical '{device.device_id}' "
                f"không cho phép lệnh từ {command.who} (cần priority >= MANUAL)"
            )

        # High safety devices — AI không được phép, phải MANUAL+
        if safety == "high" and command.priority < CommandPriority.MANUAL and command.who.startswith("ai"):
            return (
                f"Thiết bị safety_level=high không cho phép AI tự động điều khiển. "
                f"Cần xác nhận thủ công."
            )

        # require_confirm — AI/Schedule phải qua proposal
        if device.require_confirm and command.priority <= CommandPriority.AI:
            return (
                f"Thiết bị '{device.device_id}' yêu cầu xác nhận thủ công. "
                f"Lệnh từ {command.who} bị từ chối."
            )

        return None

    async def _do_execute(self, command: Command, device: "Device"):
        """Gửi lệnh xuống Driver."""
        act = command.action.lower()
        if act == "on":
            await self._driver.write(device.onoff_ga, True)
            if device.type == "light_group":
                await asyncio.sleep(0.5)
                await self._driver.write(device.onoff_ga, False)
        elif act == "off":
            await self._driver.write(device.onoff_ga, False)
        elif act == "brightness":
            if not device.supports_brightness or not device.brightness_ga:
                raise ValueError(f"Device '{device.device_id}' không hỗ trợ brightness")
            await self._driver.write(device.brightness_ga, command.value, value_type="percent")
        else:
            raise ValueError(f"Unsupported action: {command.action}")

    def get_stats(self) -> dict:
        return {
            "executed": self._executed_count,
            "rejected": self._rejected_count,
            "failed": self._failed_count,
            "active_commands": len(_active_commands),
        }
