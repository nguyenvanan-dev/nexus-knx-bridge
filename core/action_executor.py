"""
ActionExecutor — Execute action lists với đầy đủ các loại action.

Hỗ trợ: control, activate_scene, delay, wait_for, repeat, notify, set_var, if_action.
Chạy tuần tự (sequential) — mỗi action hoàn thành mới sang action tiếp theo.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from core.command_pipeline import CommandPipeline, Command, CommandPriority
    from core.state_manager import StateManager
    from core.rule_evaluator import RuleEvaluator

logger = logging.getLogger(__name__)

# Global variables store (per session, không persist qua restart)
_RULE_VARS: dict[str, Any] = {}


class ActionExecutor:
    """
    Execute action sequences defined in Rule's actions_json.
    
    Each action is a dict with "type" field:
    - control: điều khiển thiết bị
    - activate_scene: kích hoạt scene
    - delay: chờ N giây
    - wait_for: chờ cho đến khi condition thỏa mãn
    - repeat: lặp lại actions
    - notify: gửi thông báo
    - set_var: đặt biến
    - if_action: điều kiện trong action
    """

    def __init__(
        self,
        pipeline: "CommandPipeline",
        state_manager: "StateManager",
        evaluator: "RuleEvaluator",
        event_bus: "EventBus",
        scene_fn=None,
    ):
        self._state = state_manager
        self._evaluator = evaluator
        self._bus = event_bus
        self._pipeline = pipeline
        self._scene_fn = scene_fn
        self._executed_count = 0

    async def execute_actions(
        self,
        actions: list[dict],
        who: str = "automation",
        priority: int = 50,
        timeout_seconds: float = 120.0,
    ) -> dict:
        """
        Execute a list of actions in order.
        Returns summary dict with counts and any errors.
        """
        from core.command_pipeline import CommandPriority

        results = {"success": 0, "failed": 0, "errors": []}
        start = time.time()

        for i, action in enumerate(actions):
            if time.time() - start > timeout_seconds:
                results["errors"].append(f"Timeout after action {i}")
                break
            try:
                await self._execute_one(action, who, priority, results)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Action {i} ({action.get('type')}): {e}")
                logger.error("ActionExecutor: action %d failed: %s", i, e)

        return results

    async def _execute_one(self, action: dict, who: str, priority: int, results: dict):
        from core.command_pipeline import Command, CommandPriority

        atype = action.get("type", "control")

        if atype == "control":
            await self._do_control(action, who, priority)
            results["success"] += 1
            self._executed_count += 1

        elif atype == "activate_scene":
            if self._scene_fn:
                await self._scene_fn(action.get("scene_id"), who)
                results["success"] += 1

        elif atype == "delay":
            secs = float(action.get("seconds", 1))
            secs = min(secs, 300)  # Max 5 phút
            logger.debug("ActionExecutor: delay %.1fs", secs)
            await asyncio.sleep(secs)

        elif atype == "wait_for":
            condition = action.get("condition", {})
            max_wait = float(action.get("max_wait_seconds", 30))
            poll_interval = float(action.get("poll_interval_seconds", 1.0))
            start_wait = time.time()
            while time.time() - start_wait < max_wait:
                if self._evaluator.evaluate(condition):
                    results["success"] += 1
                    return
                await asyncio.sleep(poll_interval)
            logger.warning("ActionExecutor: wait_for timed out after %.0fs", max_wait)
            results["failed"] += 1

        elif atype == "repeat":
            count = int(action.get("count", 1))
            interval = float(action.get("interval_seconds", 1))
            inner_actions = action.get("actions", [])
            count = min(count, 20)  # Safety cap
            for n in range(count):
                await self.execute_actions(inner_actions, who, priority)
                if n < count - 1:
                    await asyncio.sleep(interval)
            results["success"] += 1

        elif atype == "notify":
            title = action.get("title", "Smart Home")
            msg = action.get("message", "")
            channel = action.get("channel", "telegram")
            from core.event_bus import EventType, DomainEvent
            import time
            await self._bus.publish(DomainEvent(
                event_type=EventType.NOTIFICATION_REQUEST,
                device_id="system",
                source=who,
                payload={
                    "title": title,
                    "message": msg,
                    "channel": channel,
                    "timestamp": time.time()
                }
            ))
            results["success"] += 1

        elif atype == "set_var":
            name = action.get("name")
            value = action.get("value")
            if name:
                _RULE_VARS[name] = value
                results["success"] += 1

        elif atype == "if_action":
            condition = action.get("condition", {})
            if self._evaluator.evaluate(condition):
                inner = action.get("then", [])
            else:
                inner = action.get("else", [])
            if inner:
                sub = await self.execute_actions(inner, who, priority)
                results["success"] += sub.get("success", 0)
                results["failed"] += sub.get("failed", 0)
                results["errors"] += sub.get("errors", [])

        else:
            logger.warning("ActionExecutor: unknown action type '%s'", atype)

    async def _do_control(self, action: dict, who: str, priority: int):
        from core.command_pipeline import Command, CommandPriority
        device_id = action.get("device_id") or action.get("device")
        act = action.get("action", "on")
        value = action.get("value")

        if not device_id:
            raise ValueError("control action missing device_id")

        cmd = Command(
            device_id=device_id,
            action=act,
            value=value,
            reason=action.get("reason", f"Automation by {who}"),
            who=who,
            priority=CommandPriority(min(priority, 99)),
        )
        result = await self._pipeline.execute(cmd)
        if not result.success:
            raise RuntimeError(result.rejection_reason or result.error or "Command failed")

    def get_var(self, name: str, default: Any = None) -> Any:
        return _RULE_VARS.get(name, default)

    def set_var(self, name: str, value: Any):
        _RULE_VARS[name] = value

    def get_stats(self) -> dict:
        return {"actions_executed": self._executed_count}
