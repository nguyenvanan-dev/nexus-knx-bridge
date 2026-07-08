"""
AutomationEngine — IF/THEN Rule Engine hoạt động hoàn toàn độc lập với AI.

Nhận events từ EventBus, đánh giá rules, phát lệnh qua CommandPipeline.
Rules được lưu trong SQLite bảng automation_rules.

Không cần AI, không cần internet, không cần cloud.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.event_bus import EventBus, DomainEvent
    from core.state_manager import StateManager
    from core.command_pipeline import CommandPipeline, Command, CommandPriority

logger = logging.getLogger(__name__)


@dataclass
class Condition:
    """
    Điều kiện phụ để rule có hiệu lực (ngoài trigger chính).
    Ví dụ: chỉ trigger nếu time_of_day trong khoảng 18:00–06:00
    """
    condition_type: str     # "time_range" / "device_state" / "always"
    params: dict = field(default_factory=dict)

    def evaluate(self, state_manager: "StateManager") -> bool:
        if self.condition_type == "always":
            return True

        if self.condition_type == "time_range":
            import datetime
            now = datetime.datetime.now().time()
            start_str = self.params.get("start", "00:00")
            end_str = self.params.get("end", "23:59")
            try:
                start = datetime.time.fromisoformat(start_str)
                end = datetime.time.fromisoformat(end_str)
                if start <= end:
                    return start <= now <= end
                else:  # Overnight range e.g. 22:00–06:00
                    return now >= start or now <= end
            except Exception:
                return True

        if self.condition_type == "device_state":
            device_id = self.params.get("device_id")
            expected = self.params.get("state")
            if device_id and expected:
                actual = state_manager.get_state_str(device_id, "UNKNOWN")
                operator = self.params.get("operator", "==")
                if operator == "==":
                    return actual == expected
                elif operator == "!=":
                    return actual != expected
            return True

        return True


@dataclass
class AutomationRule:
    """
    Một quy tắc tự động hóa.
    """
    rule_id: str
    name: str
    enabled: bool = True
    priority: int = 50          # Sử dụng CommandPriority values

    # ── Trigger ──────────────────────────────────
    trigger_type: str = "device_state"
    # device_state: trigger khi device thay đổi trạng thái
    # time: trigger theo giờ (cron-like, chưa implement trong v1)
    trigger_device_id: Optional[str] = None
    trigger_state: Optional[str] = None       # "ON" / "OFF" / ">25" etc.
    trigger_operator: str = "=="              # "==" / "!=" / ">" / "<"

    # ── Condition (optional) ──────────────────────
    condition: Optional[Condition] = None

    # ── Actions ───────────────────────────────────
    actions: list[dict] = field(default_factory=list)
    # [{"device_id": "den_b", "action": "on"},
    #  {"device_id": "den_c", "action": "brightness", "value": 80}]

    # ── Cooldown ──────────────────────────────────
    cooldown_seconds: float = 5.0   # Không trigger lại trong X giây
    _last_triggered: float = field(default=0.0, repr=False)

    def matches_trigger(self, event: "DomainEvent") -> bool:
        """Kiểm tra event có khớp với trigger của rule không."""
        from core.event_bus import EventType
        if not self.enabled:
            return False

        if self.trigger_type == "device_state":
            if event.event_type != EventType.DEVICE_STATE_CHANGED:
                return False
            if event.device_id != self.trigger_device_id:
                return False

            actual_state = event.payload.get("state", "")
            if self.trigger_operator == "==":
                return actual_state == self.trigger_state
            elif self.trigger_operator == "!=":
                return actual_state != self.trigger_state
            elif self.trigger_operator == ">":
                try:
                    return float(actual_state.replace("%", "")) > float(self.trigger_state)
                except Exception:
                    return False
            elif self.trigger_operator == "<":
                try:
                    return float(actual_state.replace("%", "")) < float(self.trigger_state)
                except Exception:
                    return False

        return False

    def is_in_cooldown(self) -> bool:
        return (time.time() - self._last_triggered) < self.cooldown_seconds

    def mark_triggered(self):
        self._last_triggered = time.time()

    @staticmethod
    def from_db_row(row: dict) -> "AutomationRule":
        try:
            actions = json.loads(row.get("actions_json") or "[]")
        except Exception:
            actions = []
        try:
            condition_data = json.loads(row.get("condition_json") or "null")
            condition = Condition(**condition_data) if condition_data else None
        except Exception:
            condition = None

        return AutomationRule(
            rule_id=row["rule_id"],
            name=row.get("name", "Unnamed Rule"),
            enabled=bool(row.get("enabled", True)),
            priority=int(row.get("priority", 50)),
            trigger_type=row.get("trigger_type", "device_state"),
            trigger_device_id=row.get("trigger_device_id"),
            trigger_state=row.get("trigger_state"),
            trigger_operator=row.get("trigger_operator", "=="),
            condition=condition,
            actions=actions,
            cooldown_seconds=float(row.get("cooldown_seconds", 5.0)),
        )

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "trigger_type": self.trigger_type,
            "trigger_device_id": self.trigger_device_id,
            "trigger_state": self.trigger_state,
            "trigger_operator": self.trigger_operator,
            "condition": {"condition_type": self.condition.condition_type, "params": self.condition.params} if self.condition else None,
            "actions": self.actions,
            "cooldown_seconds": self.cooldown_seconds,
        }


def init_automation_schema(db_path: Path):
    """Tạo bảng automation_rules nếu chưa có."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS automation_rules (
            rule_id          TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            enabled          BOOLEAN DEFAULT 1,
            priority         INTEGER DEFAULT 50,
            trigger_type     TEXT DEFAULT 'device_state',
            trigger_device_id TEXT,
            trigger_state    TEXT,
            trigger_operator TEXT DEFAULT '==',
            condition_json   TEXT,          -- JSON Condition object
            actions_json     TEXT NOT NULL, -- JSON array of actions
            cooldown_seconds REAL DEFAULT 5.0,
            created_at       REAL,
            updated_at       REAL
        )
    """)
    conn.commit()
    conn.close()


class AutomationEngine:
    """
    Rule Engine độc lập.

    Đăng ký với EventBus và đánh giá rules mỗi khi có sự kiện.
    Khi rule match, phát Command qua CommandPipeline.

    Không gọi AI, không gọi internet, không gọi DB (chỉ đọc rules lúc load/reload).
    """

    def __init__(
        self,
        db_path: Path,
        event_bus: "EventBus",
        state_manager: "StateManager",
        command_pipeline: "CommandPipeline",
    ):
        self._db_path = db_path
        self._bus = event_bus
        self._state = state_manager
        self._pipeline = command_pipeline
        self._rules: list[AutomationRule] = []
        self._trigger_count = 0
        self._action_count = 0

    def load_rules(self) -> int:
        """Đọc rules từ SQLite. Gọi khi startup hoặc khi admin thêm/sửa rule."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM automation_rules WHERE enabled=1").fetchall()
            conn.close()
        except Exception as e:
            logger.error("AutomationEngine: failed to load rules: %s", e)
            return 0

        self._rules = [AutomationRule.from_db_row(dict(row)) for row in rows]
        logger.info("AutomationEngine: loaded %d enabled rules", len(self._rules))
        return len(self._rules)

    async def handle(self, event: "DomainEvent"):
        """
        Subscriber callback — được EventBus gọi khi có event.
        """
        from core.event_bus import EventType, DomainEvent as DE
        from core.command_pipeline import Command, CommandPriority

        matching_rules = []
        for rule in self._rules:
            if rule.matches_trigger(event):
                if rule.is_in_cooldown():
                    logger.debug(
                        "AutomationEngine: rule '%s' matched but in cooldown (%.1fs remaining)",
                        rule.name,
                        rule.cooldown_seconds - (time.time() - rule._last_triggered)
                    )
                    continue
                matching_rules.append(rule)

        for rule in matching_rules:
            rule.mark_triggered()
            self._trigger_count += 1

            logger.info("AutomationEngine: rule '%s' triggered by %s", rule.name, event.device_id)

            # Publish automation triggered event
            await self._bus.publish(DE(
                event_type=EventType.AUTOMATION_TRIGGERED,
                device_id=event.device_id,
                source=f"automation:{rule.rule_id}",
                payload={
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "trigger_device": event.device_id,
                    "trigger_state": event.payload.get("state"),
                    "action_count": len(rule.actions),
                }
            ))

            # Execute each action via CommandPipeline
            for action_def in rule.actions:
                device_id = action_def.get("device_id") or action_def.get("device")
                if not device_id:
                    continue
                self._action_count += 1
                try:
                    cmd = Command(
                        device_id=device_id,
                        action=action_def.get("action", "on"),
                        value=action_def.get("value"),
                        reason=f"Automation rule: {rule.name}",
                        who=f"automation:{rule.rule_id}",
                        priority=CommandPriority(min(rule.priority, 99)),
                    )
                    result = await self._pipeline.execute(cmd)
                    if not result.success:
                        logger.warning(
                            "AutomationEngine: action on '%s' failed: %s",
                            device_id, result.rejection_reason or result.error
                        )
                except Exception as e:
                    logger.error("AutomationEngine: error executing action for rule '%s': %s", rule.name, e)

    def register(self):
        """Đăng ký với EventBus để nhận state_changed events."""
        from core.event_bus import EventType
        self._bus.subscribe(EventType.DEVICE_STATE_CHANGED, self.handle)
        logger.info("AutomationEngine: registered with EventBus")

    def get_rules(self) -> list[dict]:
        return [r.to_dict() for r in self._rules]

    def get_all_rules_from_db(self) -> list[dict]:
        """Đọc tất cả rules (bao gồm disabled) từ DB."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM automation_rules ORDER BY priority DESC").fetchall()
            conn.close()
            return [AutomationRule.from_db_row(dict(row)).to_dict() for row in rows]
        except Exception as e:
            logger.error("AutomationEngine: get_all_rules error: %s", e)
            return []

    def get_stats(self) -> dict:
        return {
            "loaded_rules": len(self._rules),
            "triggers_total": self._trigger_count,
            "actions_total": self._action_count,
        }
