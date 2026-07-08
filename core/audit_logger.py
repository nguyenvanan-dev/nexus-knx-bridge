"""
AuditLogger — Ghi lại đầy đủ lịch sử lệnh: who, when, result, latency.

Subscriber của EventBus, nhận COMMAND_EXECUTED / COMMAND_REJECTED / COMMAND_FAILED
và ghi vào bảng command_audit trong SQLite.
"""
from __future__ import annotations

import aiosqlite
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.event_bus import EventBus, DomainEvent

logger = logging.getLogger(__name__)


def init_audit_schema(db_path: Path):
    """Tạo bảng command_audit nếu chưa có."""
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS command_audit (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id  TEXT,
            who         TEXT,
            device_id   TEXT,
            action      TEXT,
            old_value   TEXT,
            new_value   TEXT,
            priority    INTEGER,
            result      TEXT,       -- SUCCESS / FAILED / REJECTED
            reason      TEXT,
            latency_ms  INTEGER,
            timestamp   REAL
        )
    """)
    # Thêm cột source vào device_history nếu chưa có
    try:
        conn.execute("ALTER TABLE device_history ADD COLUMN source TEXT DEFAULT 'Unknown'")
    except Exception:
        pass
    conn.commit()
    conn.close()
    logger.info("AuditLogger: schema initialized")


class AuditLogger:
    """
    Ghi audit trail cho mỗi lệnh đã thực thi/bị từ chối/thất bại.
    Hoạt động hoàn toàn bất đồng bộ — không block bất kỳ thứ gì.
    """

    def __init__(self, db_path: Path, event_bus: "EventBus"):
        self._db_path = db_path
        self._bus = event_bus
        self._written_count = 0

    def register(self):
        """Đăng ký nhận tất cả command events."""
        from core.event_bus import EventType
        self._bus.subscribe(EventType.COMMAND_EXECUTED, self.handle_executed)
        self._bus.subscribe(EventType.COMMAND_REJECTED, self.handle_rejected)
        self._bus.subscribe(EventType.COMMAND_FAILED, self.handle_failed)
        logger.info("AuditLogger: registered with EventBus")

    async def _write(
        self,
        command_id: str,
        who: str,
        device_id: str,
        action: str,
        new_value: str,
        result: str,
        reason: str,
        latency_ms: int,
        priority: int = 0,
    ):
        try:
            async with aiosqlite.connect(str(self._db_path)) as db:
                await db.execute(
                    """INSERT INTO command_audit
                       (command_id, who, device_id, action, new_value, priority, result, reason, latency_ms, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (command_id, who, device_id, action, new_value, priority, result, reason, latency_ms, time.time())
                )
                await db.commit()
            self._written_count += 1
        except Exception as e:
            logger.error("AuditLogger: write error: %s", e)

    async def handle_executed(self, event: "DomainEvent"):
        p = event.payload
        await self._write(
            command_id=p.get("command_id", "?"),
            who=p.get("who", event.source),
            device_id=event.device_id or "?",
            action=p.get("action", "?"),
            new_value=p.get("new_state", "?"),
            result="SUCCESS",
            reason=p.get("reason") or "",
            latency_ms=p.get("latency_ms", 0),
            priority=event.priority,
        )

    async def handle_rejected(self, event: "DomainEvent"):
        p = event.payload
        await self._write(
            command_id=p.get("command_id", "?"),
            who=p.get("who", event.source),
            device_id=event.device_id or "?",
            action=p.get("action", "?"),
            new_value="",
            result="REJECTED",
            reason=p.get("reason", ""),
            latency_ms=0,
            priority=event.priority,
        )

    async def handle_failed(self, event: "DomainEvent"):
        p = event.payload
        await self._write(
            command_id=p.get("command_id", "?"),
            who=event.source,
            device_id=event.device_id or "?",
            action=p.get("action", "?"),
            new_value="",
            result="FAILED",
            reason=p.get("error", ""),
            latency_ms=p.get("latency_ms", 0),
            priority=event.priority,
        )

    def get_stats(self) -> dict:
        return {"audit_records_written": self._written_count}
