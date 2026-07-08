"""
EventBus — Pub/Sub nội bộ cho toàn bộ hệ thống.

Thay thế việc gọi trực tiếp giữa các module. Mỗi module đăng ký
subscriber và nhận event thông qua bus — hoàn toàn tách rời nhau.

Muốn thêm Notification, Analytics, AI Memory? Chỉ cần thêm subscriber.
Không cần sửa process_telegrams hay bất kỳ module nào khác.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional, Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Event Types (chuẩn hóa tên event)
# ──────────────────────────────────────────────
class EventType:
    # KNX Bus
    KNX_TELEGRAM_RAW    = "knx.telegram_raw"      # Mỗi gói tin thô từ bus
    KNX_CONNECTED       = "knx.connected"
    KNX_DISCONNECTED    = "knx.disconnected"

    # Device State
    DEVICE_STATE_CHANGED = "device.state_changed"  # Sau khi StateManager.update()
    DEVICE_ADDED        = "device.added"
    DEVICE_REMOVED      = "device.removed"
    DEVICE_REGISTRY_UPDATED = "device.registry_updated"

    # Command
    COMMAND_RECEIVED    = "command.received"        # Trước khi thực thi
    COMMAND_EXECUTED    = "command.executed"        # Sau khi thực thi thành công
    COMMAND_FAILED      = "command.failed"
    COMMAND_REJECTED    = "command.rejected"        # Bị từ chối do permission/priority

    # Automation
    AUTOMATION_TRIGGERED = "automation.triggered"
    AUTOMATION_RULE_MATCH = "automation.rule_match"

    # System
    SYSTEM_STARTUP      = "system.startup"
    SYSTEM_SHUTDOWN     = "system.shutdown"
    HEALTH_CHECK        = "system.health_check"
    
    # Notification
    NOTIFICATION_REQUEST = "notification.request"


@dataclass
class DomainEvent:
    """
    Đơn vị dữ liệu truyền qua Event Bus.
    Mọi thứ đều là DomainEvent — từ telegram KNX đến lệnh AI.
    """
    event_type: str
    payload: dict                           # Dữ liệu cụ thể của event
    source: str = "system"                  # Ai phát sinh event này
    device_id: Optional[str] = None        # Thiết bị liên quan (nếu có)
    priority: int = 0                       # 0=normal, 50=automation, 99=emergency
    timestamp: float = field(default_factory=time.time)
    event_id: Optional[str] = None         # UUID nếu cần tracing

    def to_sse_dict(self) -> dict:
        """Serialize cho SSE stream."""
        return {
            "event_type": self.event_type,
            "device_id": self.device_id,
            "source": self.source,
            "priority": self.priority,
            "timestamp": self.timestamp,
            **self.payload,
        }


# Type alias
Handler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """
    Asyncio-native Pub/Sub bus.

    Usage:
        # Đăng ký
        event_bus.subscribe(EventType.DEVICE_STATE_CHANGED, my_handler)

        # Phát sự kiện
        await event_bus.publish(DomainEvent(
            event_type=EventType.DEVICE_STATE_CHANGED,
            device_id="den_phong_khach",
            payload={"state": "ON", "previous": "OFF"},
            source="KNX Bus"
        ))
    """

    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = {}
        self._wildcard_subscribers: list[Handler] = []  # subscribe("*", handler)
        self._published_count: int = 0
        self._error_count: int = 0

    def subscribe(self, event_type: str, handler: Handler):
        """
        Đăng ký nhận một loại event.
        Dùng "*" để nhận tất cả events.
        """
        if event_type == "*":
            self._wildcard_subscribers.append(handler)
            logger.debug("EventBus: wildcard subscriber registered: %s", handler.__qualname__)
        else:
            self._subscribers.setdefault(event_type, []).append(handler)
            logger.debug("EventBus: %s → %s", event_type, handler.__qualname__)

    def unsubscribe(self, event_type: str, handler: Handler):
        if event_type == "*":
            self._wildcard_subscribers = [h for h in self._wildcard_subscribers if h != handler]
        else:
            handlers = self._subscribers.get(event_type, [])
            self._subscribers[event_type] = [h for h in handlers if h != handler]

    async def publish(self, event: DomainEvent):
        """
        Phát event đến tất cả subscribers.
        Chạy các handlers tuần tự (không song song) để tránh race condition.
        Handlers lỗi được bắt và log, không làm dừng các handlers khác.
        """
        self._published_count += 1

        handlers = list(self._subscribers.get(event.event_type, []))
        handlers += self._wildcard_subscribers

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "EventBus: handler %s raised exception for event %s: %s",
                    handler.__qualname__, event.event_type, e
                )

    async def publish_many(self, events: list[DomainEvent]):
        """Phát nhiều events liên tiếp."""
        for event in events:
            await self.publish(event)

    def subscriber_count(self, event_type: Optional[str] = None) -> int:
        if event_type:
            return len(self._subscribers.get(event_type, []))
        total = sum(len(v) for v in self._subscribers.values())
        return total + len(self._wildcard_subscribers)

    def get_stats(self) -> dict:
        return {
            "published_total": self._published_count,
            "error_total": self._error_count,
            "subscriber_count": self.subscriber_count(),
            "event_types_with_subscribers": list(self._subscribers.keys()),
        }
