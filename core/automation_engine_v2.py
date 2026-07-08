"""
AutomationEngine v2 — Full Rule Engine với JSON schema.

Hỗ trợ:
- Trigger: device_state, time (at/days), cron, sun (sunrise/sunset), system
- Conditions: AND, OR, NOT trees
- Actions: control, activate_scene, delay, wait_for, repeat, notify, set_var, if_action
- Cooldown, max_runs_per_day, priority

Schema automation_rules_v2 thay thế automation_rules cũ.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING

from core.rule_evaluator import RuleEvaluator
from core.action_executor import ActionExecutor
from core.trigger_manager import TriggerManager

if TYPE_CHECKING:
    from core.event_bus import EventBus, DomainEvent
    from core.state_manager import StateManager
    from core.command_pipeline import CommandPipeline

logger = logging.getLogger(__name__)


def init_automation_schema_v2(db_path: Path):
    """Tạo schema v2 cho automation rules."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS automation_rules_v2 (
            rule_id          TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            description      TEXT DEFAULT '',
            enabled          BOOLEAN DEFAULT 1,
            priority         INTEGER DEFAULT 50,
            
            -- Trigger (JSON object)
            trigger_json     TEXT NOT NULL DEFAULT '{"type":"device_state"}',
            
            -- Conditions (JSON — AND/OR/NOT tree, null = no conditions)
            conditions_json  TEXT,
            
            -- Actions (JSON array)
            actions_json     TEXT NOT NULL DEFAULT '[]',
            
            -- Time filter (optional: limit which days/hours rule can fire)
            time_filter_json TEXT,
            
            -- Runtime settings
            cooldown_seconds REAL DEFAULT 5.0,
            max_runs_per_day INTEGER DEFAULT 0,
            
            -- Stats
            run_count        INTEGER DEFAULT 0,
            last_run_at      REAL,
            last_error       TEXT,
            
            created_at       REAL,
            updated_at       REAL
        );
        
        -- Migrate old rules if they exist
        INSERT OR IGNORE INTO automation_rules_v2 (
            rule_id, name, enabled, priority,
            trigger_json, conditions_json, actions_json,
            cooldown_seconds, created_at, updated_at
        )
        SELECT 
            rule_id, name, enabled, priority,
            json_object(
                'type', trigger_type,
                'device_id', trigger_device_id,
                'state', trigger_state,
                'op', trigger_operator
            ),
            condition_json,
            actions_json,
            cooldown_seconds,
            created_at, updated_at
        FROM automation_rules
        WHERE trigger_type IS NOT NULL;
    """)
    conn.commit()
    conn.close()
    logger.info("AutomationEngine v2: schema initialized")


@dataclass
class RuleV2:
    """Rule với đầy đủ JSON schema v2."""
    rule_id: str
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 50

    trigger: dict = field(default_factory=dict)
    conditions: Optional[dict] = None
    actions: list[dict] = field(default_factory=list)
    time_filter: Optional[dict] = None

    cooldown_seconds: float = 5.0
    max_runs_per_day: int = 0

    run_count: int = 0
    last_run_at: float = 0.0
    last_error: Optional[str] = None

    _runs_today: int = field(default=0, repr=False)
    _runs_today_date: str = field(default="", repr=False)

    @staticmethod
    def from_row(row: dict) -> "RuleV2":
        def _parse(s, default):
            if not s:
                return default
            try:
                return json.loads(s)
            except Exception:
                return default

        return RuleV2(
            rule_id=row["rule_id"],
            name=row.get("name", "Unnamed"),
            description=row.get("description", ""),
            enabled=bool(row.get("enabled", True)),
            priority=int(row.get("priority", 50)),
            trigger=_parse(row.get("trigger_json"), {}),
            conditions=_parse(row.get("conditions_json"), None),
            actions=_parse(row.get("actions_json"), []),
            time_filter=_parse(row.get("time_filter_json"), None),
            cooldown_seconds=float(row.get("cooldown_seconds", 5.0)),
            max_runs_per_day=int(row.get("max_runs_per_day", 0)),
            run_count=int(row.get("run_count", 0)),
            last_run_at=float(row.get("last_run_at") or 0),
            last_error=row.get("last_error"),
        )

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "trigger": self.trigger,
            "conditions": self.conditions,
            "actions": self.actions,
            "time_filter": self.time_filter,
            "cooldown_seconds": self.cooldown_seconds,
            "max_runs_per_day": self.max_runs_per_day,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at,
            "last_error": self.last_error,
        }

    def is_in_cooldown(self) -> bool:
        return (time.time() - self.last_run_at) < self.cooldown_seconds

    def exceeded_daily_limit(self) -> bool:
        if self.max_runs_per_day <= 0:
            return False
        import datetime
        today = datetime.date.today().isoformat()
        if self._runs_today_date != today:
            self._runs_today = 0
            self._runs_today_date = today
        return self._runs_today >= self.max_runs_per_day

    def increment_runs(self):
        import datetime
        today = datetime.date.today().isoformat()
        if self._runs_today_date != today:
            self._runs_today = 0
            self._runs_today_date = today
        self._runs_today += 1

    def check_time_filter(self) -> bool:
        """Kiểm tra time filter (days/hours global filter cho toàn rule)."""
        if not self.time_filter:
            return True
        evaluator = RuleEvaluator.__new__(RuleEvaluator)
        # Create a minimal evaluator just for time checks
        evaluator._state = None  # type: ignore

        days = self.time_filter.get("days", [])
        if days:
            import datetime
            day_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            today = day_map[datetime.datetime.now().weekday()]
            if today not in [d.lower() for d in days]:
                return False

        from_t = self.time_filter.get("from")
        to_t = self.time_filter.get("to")
        if from_t or to_t:
            real_evaluator = RuleEvaluator.__new__(RuleEvaluator)
            real_evaluator._state = None  # type: ignore
            return real_evaluator._eval_time_range({"from": from_t or "00:00", "to": to_t or "23:59"})

        return True

    def matches_event_trigger(self, event: "DomainEvent") -> bool:
        """Check if an event matches this rule's trigger."""
        if not self.enabled:
            return False
        from core.event_bus import EventType
        ttype = self.trigger.get("type")

        if ttype == "device_state":
            if event.event_type != EventType.DEVICE_STATE_CHANGED:
                return False
            if event.device_id != self.trigger.get("device_id"):
                return False
            actual = event.payload.get("state", "")
            expected = str(self.trigger.get("state", ""))
            op = self.trigger.get("op", "==")
            try:
                a_num = float(actual.replace("%", "").replace("°C", "").strip())
                e_num = float(expected.replace("%", "").replace("°C", "").strip())
                if op == "==": return a_num == e_num
                if op == "!=": return a_num != e_num
                if op == ">":  return a_num > e_num
                if op == "<":  return a_num < e_num
                if op == ">=": return a_num >= e_num
                if op == "<=": return a_num <= e_num
            except Exception:
                if op == "==": return actual.upper() == expected.upper()
                if op == "!=": return actual.upper() != expected.upper()

        elif ttype == "knx_telegram":
            if event.event_type != EventType.KNX_TELEGRAM_RAW:
                return False
            if event.payload.get("destination_address") != self.trigger.get("ga"):
                return False
            return True

        elif ttype == "scene_activated":
            if event.event_type != "scene.activated":
                return False
            return event.payload.get("scene_id") == self.trigger.get("scene_id")

        elif ttype == "system":
            return event.event_type == f"system.{self.trigger.get('event', '')}"

        return False


class AutomationEngineV2:
    """
    Full Rule Engine v2.
    
    - EventBus subscriber để xử lý device_state và system triggers
    - TriggerManager để xử lý time/cron/sun triggers
    - RuleEvaluator để evaluate AND/OR/NOT conditions
    - ActionExecutor để run action sequences
    """

    def __init__(
        self,
        db_path: Path,
        event_bus: "EventBus",
        state_manager: "StateManager",
        command_pipeline: "CommandPipeline",
        notify_fn=None,
        scene_fn=None,
    ):
        self._db_path = db_path
        self._bus = event_bus
        self._state = state_manager
        self._pipeline = command_pipeline
        self._scene_fn = scene_fn

        self._rules: list[RuleV2] = []
        self._evaluator = RuleEvaluator(state_manager)
        self._executor = ActionExecutor(
            pipeline=command_pipeline,
            state_manager=state_manager,
            evaluator=self._evaluator,
            event_bus=event_bus,
            scene_fn=scene_fn,
        )
        self._trigger_manager = TriggerManager(event_bus)

        self._trigger_count = 0
        self._action_count = 0
        self._error_count = 0

    def load_rules(self) -> int:
        """Load enabled rules from DB."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM automation_rules_v2 WHERE enabled=1 ORDER BY priority DESC"
            ).fetchall()
            conn.close()
        except Exception as e:
            logger.error("AutomationEngineV2: failed to load rules: %s", e)
            return 0

        self._rules = [RuleV2.from_row(dict(row)) for row in rows]

        # Reload TriggerManager
        self._trigger_manager.reload_triggers(
            [{"rule_id": r.rule_id, "trigger_config": r.trigger} for r in self._rules
             if r.trigger.get("type") in ("time", "cron", "sun")],
            callback=self._fire_rule_by_id,
        )

        logger.info("AutomationEngineV2: loaded %d enabled rules", len(self._rules))
        return len(self._rules)

    def get_all_rules_from_db(self) -> list[dict]:
        """Get all rules (including disabled) from DB."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM automation_rules_v2 ORDER BY priority DESC, name"
            ).fetchall()
            conn.close()
            return [RuleV2.from_row(dict(row)).to_dict() for row in rows]
        except Exception as e:
            logger.error("AutomationEngineV2: get_all_rules error: %s", e)
            return []

    def register(self):
        """Register with EventBus for event-driven triggers."""
        from core.event_bus import EventType
        self._bus.subscribe(EventType.DEVICE_STATE_CHANGED, self.handle)
        self._bus.subscribe(EventType.SYSTEM_STARTUP, self.handle)
        self._trigger_manager.start()
        logger.info("AutomationEngineV2: registered with EventBus, TriggerManager started")

    async def handle(self, event: "DomainEvent"):
        """EventBus subscriber handler."""
        for rule in self._rules:
            if rule.matches_event_trigger(event):
                asyncio.create_task(self._fire_rule(rule, event))

    async def _fire_rule_by_id(self, rule_id: str):
        """Called by TriggerManager for time-based triggers."""
        rule = next((r for r in self._rules if r.rule_id == rule_id), None)
        if rule:
            await self._fire_rule(rule, None)

    async def _fire_rule(self, rule: RuleV2, trigger_event: Optional["DomainEvent"]):
        """Fire a matched rule — evaluate conditions then execute actions."""
        from core.event_bus import DomainEvent, EventType

        # Cooldown check
        if rule.is_in_cooldown():
            logger.debug("AutomationEngineV2: rule '%s' in cooldown", rule.name)
            return

        # Daily limit check
        if rule.exceeded_daily_limit():
            logger.debug("AutomationEngineV2: rule '%s' exceeded daily limit", rule.name)
            return

        # Time filter check
        if not rule.check_time_filter():
            logger.debug("AutomationEngineV2: rule '%s' blocked by time_filter", rule.name)
            return

        # Condition evaluation (AND/OR/NOT)
        if rule.conditions:
            if not self._evaluator.evaluate(rule.conditions):
                logger.debug("AutomationEngineV2: rule '%s' conditions not met", rule.name)
                return

        # All checks passed — fire!
        rule.last_run_at = time.time()
        rule.increment_runs()
        self._trigger_count += 1
        device_id = trigger_event.device_id if trigger_event else None
        trigger_state = trigger_event.payload.get("state") if trigger_event else None

        logger.info(
            "AutomationEngineV2: firing rule '%s' (trigger=%s, state=%s)",
            rule.name, device_id, trigger_state
        )

        # Publish automation triggered event
        await self._bus.publish(DomainEvent(
            event_type=EventType.AUTOMATION_TRIGGERED,
            device_id=device_id,
            source=f"automation:{rule.rule_id}",
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "trigger_device": device_id,
                "trigger_state": trigger_state,
                "action_count": len(rule.actions),
            }
        ))

        # Execute actions
        who = f"automation:{rule.rule_id}"
        try:
            results = await self._executor.execute_actions(
                rule.actions, who=who, priority=rule.priority
            )
            self._action_count += results.get("success", 0)
            if results.get("errors"):
                self._error_count += 1
                rule.last_error = "; ".join(results["errors"][:3])
                self._update_rule_stats(rule, error=rule.last_error)
            else:
                rule.last_error = None
                self._update_rule_stats(rule)
        except Exception as e:
            self._error_count += 1
            rule.last_error = str(e)
            self._update_rule_stats(rule, error=str(e))
            logger.error("AutomationEngineV2: rule '%s' action error: %s", rule.name, e)

    def _update_rule_stats(self, rule: RuleV2, error: Optional[str] = None):
        """Update run stats in DB asynchronously."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "UPDATE automation_rules_v2 SET run_count=run_count+1, last_run_at=?, last_error=? WHERE rule_id=?",
                (rule.last_run_at, error, rule.rule_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("AutomationEngineV2: stats update error: %s", e)

    def get_rules(self) -> list[dict]:
        return [r.to_dict() for r in self._rules]

    def get_stats(self) -> dict:
        return {
            "loaded_rules": len(self._rules),
            "triggers_total": self._trigger_count,
            "actions_total": self._action_count,
            "errors_total": self._error_count,
            "trigger_manager": self._trigger_manager.get_stats(),
        }
