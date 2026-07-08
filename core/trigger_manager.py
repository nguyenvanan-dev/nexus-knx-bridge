"""
TriggerManager — Background worker cho Time/Cron/Sun triggers.

Chạy các triggers không phải event-driven (không có KNX telegram trigger).
Ví dụ: "Bật đèn lúc 22:00 mỗi ngày" hoặc "Tắt đèn 30 phút sau hoàng hôn".
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from core.event_bus import EventBus, DomainEvent

logger = logging.getLogger(__name__)

try:
    from astral import LocationInfo
    from astral.sun import sun
    HAS_ASTRAL = True
except ImportError:
    HAS_ASTRAL = False
    logger.info("TriggerManager: astral not installed, sunrise/sunset disabled")


@dataclass
class TimedTrigger:
    """Một trigger chạy theo thời gian."""
    rule_id: str
    trigger_type: str       # "time" / "cron" / "sun"
    trigger_config: dict    # {"at": "22:00", "days": [...]} or {"cron": "0 22 * * *"}
    callback: Callable      # async (rule_id: str) -> None
    last_fired: float = 0.0
    _fired_today: set = field(default_factory=set)  # {date_str: True}


class TriggerManager:
    """
    Background worker poll-based để xử lý time-based triggers.
    Chạy mỗi 30 giây, kiểm tra tất cả triggers.
    """

    def __init__(self, event_bus: "EventBus", poll_interval: float = 30.0):
        self._bus = event_bus
        self._poll_interval = poll_interval
        self._triggers: list[TimedTrigger] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._fired_count = 0

        # Hanoi location for sunrise/sunset
        self._location = None
        if HAS_ASTRAL:
            self._location = LocationInfo(
                name="Hanoi", region="Vietnam",
                timezone="Asia/Ho_Chi_Minh",
                latitude=21.0285, longitude=105.8542
            )

    def add_trigger(self, rule_id: str, trigger_config: dict, callback: Callable):
        """Register a new time-based trigger."""
        ttype = trigger_config.get("type", "time")
        if ttype not in ("time", "cron", "sun"):
            return  # Not a time trigger

        self._triggers.append(TimedTrigger(
            rule_id=rule_id,
            trigger_type=ttype,
            trigger_config=trigger_config,
            callback=callback,
        ))
        logger.debug("TriggerManager: added trigger for rule '%s' (type=%s)", rule_id, ttype)

    def remove_trigger(self, rule_id: str):
        self._triggers = [t for t in self._triggers if t.rule_id != rule_id]

    def reload_triggers(self, triggers: list[dict], callback: Callable):
        """Replace all triggers (called when rules are reloaded)."""
        self._triggers.clear()
        for t in triggers:
            self.add_trigger(t["rule_id"], t["trigger_config"], callback)

    def start(self) -> asyncio.Task:
        """Start the background polling task."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("TriggerManager: started (poll_interval=%.0fs)", self._poll_interval)
        return self._task

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self._check_all()
            except Exception as e:
                logger.error("TriggerManager: error in loop: %s", e)
            await asyncio.sleep(self._poll_interval)

    async def _check_all(self):
        import datetime
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        for trigger in self._triggers:
            try:
                should_fire = False

                if trigger.trigger_type == "time":
                    should_fire = self._check_time_trigger(trigger, now, today_str)
                elif trigger.trigger_type == "cron":
                    should_fire = self._check_cron_trigger(trigger, now)
                elif trigger.trigger_type == "sun":
                    should_fire = self._check_sun_trigger(trigger, now, today_str)

                if should_fire:
                    trigger.last_fired = time.time()
                    trigger._fired_today.add(today_str)
                    self._fired_count += 1
                    logger.info("TriggerManager: firing rule '%s' (type=%s)", trigger.rule_id, trigger.trigger_type)
                    try:
                        await trigger.callback(trigger.rule_id)
                    except Exception as e:
                        logger.error("TriggerManager: callback error for rule '%s': %s", trigger.rule_id, e)

            except Exception as e:
                logger.error("TriggerManager: error checking trigger for rule '%s': %s", trigger.rule_id, e)

    def _check_time_trigger(self, trigger: TimedTrigger, now, today_str: str) -> bool:
        """Check "at" time trigger — fires once per day at specified time."""
        config = trigger.trigger_config
        at_str = config.get("at")
        if not at_str:
            return False

        # Already fired today?
        if today_str in trigger._fired_today:
            return False

        # Check days filter
        days = config.get("days", [])  # [] = every day
        if days:
            day_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            today_name = day_map[now.weekday()]
            if today_name not in [d.lower() for d in days]:
                return False

        # Check time (within current poll window ±30s)
        import datetime
        try:
            target_time = datetime.time.fromisoformat(at_str)
            target_dt = now.replace(hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0)
            diff = abs((now - target_dt).total_seconds())
            return diff <= self._poll_interval
        except Exception:
            return False

    def _check_cron_trigger(self, trigger: TimedTrigger, now) -> bool:
        """Check cron expression trigger."""
        cron_expr = trigger.trigger_config.get("cron", "")
        if not cron_expr:
            return False
        try:
            from croniter import croniter
            cron = croniter(cron_expr, now)
            prev = cron.get_prev(type(now))
            diff = abs((now - prev).total_seconds())
            return diff <= self._poll_interval and diff > 0
        except ImportError:
            logger.warning("TriggerManager: croniter not installed, cron triggers disabled")
            return False
        except Exception:
            return False

    def _check_sun_trigger(self, trigger: TimedTrigger, now, today_str: str) -> bool:
        """Check sunrise/sunset trigger."""
        if not HAS_ASTRAL or not self._location:
            return False

        # Already fired today?
        if today_str in trigger._fired_today:
            return False

        config = trigger.trigger_config
        event = config.get("event", "sunset")
        offset_min = int(config.get("offset_minutes", 0))

        try:
            import datetime as dt
            sun_times = sun(self._location.observer, date=now.date(),
                           tzinfo=self._location.timezone)
            base_time = sun_times.get(event)
            if base_time is None:
                return False

            target = base_time + dt.timedelta(minutes=offset_min)
            # Convert to naive for comparison
            target_naive = target.replace(tzinfo=None)
            diff = abs((now - target_naive).total_seconds())
            return diff <= self._poll_interval
        except Exception as e:
            logger.debug("TriggerManager: sun trigger error: %s", e)
            return False

    def get_stats(self) -> dict:
        return {
            "active_triggers": len(self._triggers),
            "fired_total": self._fired_count,
            "running": self._running,
        }
