"""
RuleEvaluator — Evaluate condition trees với AND/OR/NOT logic.

Dùng để evaluate Conditions trong AutomationRule mới (JSON schema).
Tách biệt hoàn toàn với trigger và action — chỉ trả về bool.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.state_manager import StateManager

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """
    Evaluate nested condition trees.

    Condition structure (JSON / dict):
    
    Single condition:
    {
        "type": "device_state",     -- loại condition
        "device_id": "den_a",
        "state": "ON",
        "op": "=="                  -- == / != / > / < / >= / <=
    }
    
    Compound:
    {
        "op": "AND",    -- AND / OR / NOT
        "items": [...]
    }
    """

    def __init__(self, state_manager: "StateManager"):
        self._state = state_manager

    def evaluate(self, condition: dict) -> bool:
        """
        Recursively evaluate a condition tree.
        Returns True if the condition is satisfied.
        """
        if not condition:
            return True  # No condition = always true

        op = condition.get("op", "==")
        ctype = condition.get("type")

        # ── Compound operators ────────────────────────────────────
        if op == "AND":
            return all(self.evaluate(item) for item in condition.get("items", []))
        if op == "OR":
            return any(self.evaluate(item) for item in condition.get("items", []))
        if op == "NOT":
            items = condition.get("items", [])
            return not self.evaluate(items[0]) if items else True

        # ── Leaf conditions ───────────────────────────────────────
        if ctype == "device_state":
            return self._eval_device_state(condition)
        if ctype == "time_range":
            return self._eval_time_range(condition)
        if ctype == "day_of_week":
            return self._eval_day_of_week(condition)
        if ctype == "always":
            return True
        if ctype == "never":
            return False

        logger.warning("RuleEvaluator: unknown condition type '%s'", ctype)
        return True

    def _eval_device_state(self, cond: dict) -> bool:
        device_id = cond.get("device_id")
        expected = str(cond.get("state", ""))
        op = cond.get("op", "==")

        actual_str = self._state.get_state_str(device_id or "", "UNKNOWN")

        try:
            actual_num = float(actual_str.replace("%", "").replace("°C", "").strip())
            expected_num = float(expected.replace("%", "").replace("°C", "").strip())
            if op == "==":  return actual_num == expected_num
            if op == "!=":  return actual_num != expected_num
            if op == ">":   return actual_num > expected_num
            if op == "<":   return actual_num < expected_num
            if op == ">=":  return actual_num >= expected_num
            if op == "<=":  return actual_num <= expected_num
        except (ValueError, AttributeError):
            # String comparison fallback
            if op == "==": return actual_str.upper() == expected.upper()
            if op == "!=": return actual_str.upper() != expected.upper()

        return False

    def _eval_time_range(self, cond: dict) -> bool:
        import datetime
        now = datetime.datetime.now().time()
        from_str = cond.get("from", "00:00")
        to_str = cond.get("to", "23:59")
        try:
            from_t = datetime.time.fromisoformat(from_str)
            to_t = datetime.time.fromisoformat(to_str)
            if from_t <= to_t:
                return from_t <= now <= to_t
            else:  # Overnight: e.g. 22:00 – 06:00
                return now >= from_t or now <= to_t
        except Exception:
            return True

    def _eval_day_of_week(self, cond: dict) -> bool:
        import datetime
        # days: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        days = cond.get("days", [])
        if not days:
            return True
        day_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        today = day_map[datetime.datetime.now().weekday()]
        return today in [d.lower() for d in days]
