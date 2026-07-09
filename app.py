import os
import re
import json
import asyncio
import secrets
import socket
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
import sqlite3
import aiosqlite
import time
import logging

from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

import auth_utils

# Removed xknx imports to use Driver Abstraction Layer
from core.drivers.knx_driver import KNXDriver


# ── Domain Layer (Core) ──────────────────────────────────────────
from core.device_registry import DeviceRegistry
from core.state_manager import StateManager
from core.event_bus import EventBus, DomainEvent, EventType
from core.ai_context import ContextBuilder
from core.command_pipeline import CommandPipeline, Command, CommandPriority
from core.automation_engine import AutomationEngine, init_automation_schema
from core.automation_engine_v2 import AutomationEngineV2, init_automation_schema_v2, RuleV2
from core.rule_evaluator import RuleEvaluator
from core.action_executor import ActionExecutor
from core.trigger_manager import TriggerManager
from core.trigger_manager import TriggerManager
from core.audit_logger import AuditLogger, init_audit_schema
from core.notification_engine import NotificationEngine
from services.health_service import HealthService
from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent
DEVICES_FILE = BASE_DIR / "devices.json"
DB_FILE = BASE_DIR / "data" / "chat_history.db"

# Create data dir if not exists
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

def init_db():
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT,
            group_name TEXT,
            sender_id TEXT,
            sender_name TEXT,
            text TEXT,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def init_smarthome_db():
    conn = sqlite3.connect(str(BASE_DIR / 'smarthome.db'))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            action TEXT,
            state TEXT,
            source TEXT DEFAULT 'Unknown',
            timestamp INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scene_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER,
            device_id TEXT,
            action TEXT,
            value TEXT,
            delay_seconds REAL DEFAULT 0.0,
            condition_json TEXT,
            retry_count INTEGER DEFAULT 0,
            timeout_seconds REAL DEFAULT 30.0,
            comment TEXT,
            enabled BOOLEAN DEFAULT 1,
            FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
        )
    ''')
    # Add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE scene_actions ADD COLUMN condition_json TEXT")
        cursor.execute("ALTER TABLE scene_actions ADD COLUMN retry_count INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE scene_actions ADD COLUMN timeout_seconds REAL DEFAULT 30.0")
        cursor.execute("ALTER TABLE scene_actions ADD COLUMN comment TEXT")
        cursor.execute("ALTER TABLE scene_actions ADD COLUMN enabled BOOLEAN DEFAULT 1")
    except sqlite3.OperationalError:
        pass # Columns already exist

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scene_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER,
            actions_json TEXT,
            updated_at REAL,
            FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

init_db()
init_smarthome_db()

load_dotenv(BASE_DIR / ".env")

KNX_GATEWAY_IP = os.getenv("KNX_GATEWAY_IP", "10.1.10.137")
KNX_GATEWAY_PORT = int(os.getenv("KNX_GATEWAY_PORT", "3671"))

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((KNX_GATEWAY_IP, KNX_GATEWAY_PORT))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

KNX_LOCAL_IP_ENV = os.getenv("KNX_LOCAL_IP", "auto")
KNX_API_TOKEN = os.getenv("KNX_API_TOKEN", "")

DEVICE_ID_RE = re.compile(r"^[a-z0-9_]+$")
GA_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{1,3}$")

app = FastAPI(title="KNX Smart Home Platform", version="3.0.0")

knx_lock = asyncio.Lock()
_knx_driver: Optional[KNXDriver] = None
xknx_instance = None # Kept for backward compatibility references
PENDING_PROPOSALS: dict[str, dict[str, Any]] = {}
SCHEDULED_TASKS: dict[str, dict[str, Any]] = {}

# Event-Driven Queues (for raw telegram ingestion only)
raw_telegram_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
device_event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
sse_event_clients = []
sse_bus_clients = []

# ── Domain Layer Singletons ───────────────────────────────────────
_SMARTHOME_DB = BASE_DIR / 'smarthome.db'

device_registry = DeviceRegistry(_SMARTHOME_DB)
state_manager = StateManager()
event_bus = EventBus()

from core.device_service import DeviceService
device_service = DeviceService(registry=device_registry, state_manager=state_manager)

_context_builder = ContextBuilder(device_service=device_service, event_bus=event_bus, db_path=_SMARTHOME_DB)

# CommandPipeline and AutomationEngine initialized after write_knx is defined
# (see _init_domain_layer() called in startup_event)
_command_pipeline: Optional[CommandPipeline] = None
_automation_engine: Optional[AutomationEngineV2] = None
_audit_logger: Optional[AuditLogger] = None
_notification_engine: Optional[NotificationEngine] = None
_health_service: Optional[HealthService] = None


def load_devices() -> dict:
    db_path = BASE_DIR / "smarthome.db"
    if not db_path.exists():
        return {}
        
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices")
        rows = cursor.fetchall()
        conn.close()
        
        devices = {}
        for row in rows:
            d = dict(row)
            if d.get("aliases"):
                d["aliases"] = json.loads(d["aliases"])
            else:
                d["aliases"] = []
            d["supports_brightness"] = bool(d["supports_brightness"])
            d["require_confirm"] = bool(d["require_confirm"])
            d["enabled"] = bool(d["enabled"])
            devices[d["device_id"]] = d
        return devices
    except Exception as e:
        print(f"Error loading devices from SQLite: {e}")
        return {}

def save_devices():
    db_path = BASE_DIR / "smarthome.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            room TEXT,
            type TEXT,
            onoff_ga TEXT,
            status_ga TEXT,
            supports_brightness BOOLEAN,
            brightness_ga TEXT,
            brightness_status_ga TEXT,
            color_ga TEXT,
            color_status_ga TEXT,
            role TEXT,
            aliases TEXT,
            safety_level TEXT,
            require_confirm BOOLEAN,
            enabled BOOLEAN
        )
    ''')
    
    for device_id, data in DEVICES.items():
        aliases_json = json.dumps(data.get("aliases", []), ensure_ascii=False)
        cursor.execute('''
            INSERT OR REPLACE INTO devices (
                device_id, name, room, type, 
                onoff_ga, status_ga, supports_brightness, 
                brightness_ga, brightness_status_ga, 
                color_ga, color_status_ga, 
                role, aliases, safety_level, 
                require_confirm, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            device_id,
            data.get("name", "Unknown"),
            data.get("room"),
            data.get("type"),
            data.get("onoff_ga"),
            data.get("status_ga"),
            bool(data.get("supports_brightness", False)),
            data.get("brightness_ga"),
            data.get("brightness_status_ga"),
            data.get("color_ga"),
            data.get("color_status_ga"),
            data.get("role"),
            aliases_json,
            data.get("safety_level"),
            bool(data.get("require_confirm", False)),
            bool(data.get("enabled", True))
        ))
    
    conn.commit()
    conn.close()


DEVICES = load_devices()

# Keep DEVICES in sync with DeviceRegistry for backward compat
# (API endpoints still use DEVICES dict until fully migrated)
device_registry.reload()


class LightCommand(BaseModel):
    device: str = Field(..., examples=["den_led_day"])
    action: str = Field(..., examples=["on", "off", "brightness"])
    value: Optional[int] = Field(None, ge=0, le=100)


class ContextCommand(BaseModel):
    mode: str = Field(..., examples=["daylight", "weather"])
    sun_percent: Optional[int] = Field(None, ge=0, le=100)
    outside_temp: Optional[float] = None
    rain_expected: Optional[bool] = None


class ActionItem(BaseModel):
    device: str
    action: str
    value: Optional[int] = Field(None, ge=0, le=100)
    reason: Optional[str] = None


class ProposalCommand(BaseModel):
    summary: str
    actions: list[ActionItem]
    require_confirm: bool = True


class EnvironmentProposalCommand(BaseModel):
    sun_percent: Optional[int] = Field(None, ge=0, le=100)
    outside_temp: Optional[float] = None
    rain_expected: Optional[bool] = None
    note: Optional[str] = None


class ExecuteProposalCommand(BaseModel):
    confirm: bool = False


class ZaloGroupLogCommand(BaseModel):
    group_id: str
    group_name: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: int


class AskAICommand(BaseModel):
    text: str


class DeviceAddCommand(BaseModel):
    confirmed: bool = False
    device_id: str
    name: str
    room: str = "phong_rd"
    type: str = "light"
    onoff_ga: str
    status_ga: Optional[str] = None
    supports_brightness: bool = False
    brightness_ga: Optional[str] = None
    brightness_status_ga: Optional[str] = None
    color_ga: Optional[str] = None
    color_status_ga: Optional[str] = None
    role: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    safety_level: str = "safe_demo"
    require_confirm: bool = False
    enabled: bool = True


class DeviceUpdateCommand(BaseModel):
    confirmed: bool = False
    device_id: str
    name: Optional[str] = None
    room: Optional[str] = None
    type: Optional[str] = None
    onoff_ga: Optional[str] = None
    status_ga: Optional[str] = None
    supports_brightness: Optional[bool] = None
    brightness_ga: Optional[str] = None
    brightness_status_ga: Optional[str] = None
    color_ga: Optional[str] = None
    color_status_ga: Optional[str] = None
    role: Optional[str] = None
    aliases: Optional[list[str]] = None
    safety_level: Optional[str] = None
    require_confirm: Optional[bool] = None
    enabled: Optional[bool] = None


class DeviceDisableCommand(BaseModel):
    confirmed: bool = False
    device_id: str


class ScheduleCommand(BaseModel):
    device: str
    action: str
    value: Optional[int] = Field(None, ge=0, le=100)
    delay_seconds: int = Field(..., gt=0, description="Thoi gian cho (giay)")
    reason: Optional[str] = None


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def check_auth(x_knx_token: Optional[str]):
    pass


def validate_ga(ga: Optional[str], field_name: str):
    if ga is None:
        return
    if not GA_RE.match(ga):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} không đúng định dạng group address: {ga}"
        )


def validate_device_id(device_id: str):
    if not DEVICE_ID_RE.match(device_id):
        raise HTTPException(
            status_code=400,
            detail="device_id chỉ được dùng chữ thường, số và dấu gạch dưới. Ví dụ: den_ban"
        )


def get_device(device_id: str):
    """Backward-compat wrapper — returns dict for existing endpoints."""
    # Try DeviceRegistry first (authoritative)
    d = device_registry.get(device_id)
    if d is not None:
        if not d.enabled or d.type == "disabled":
            raise HTTPException(status_code=403, detail=f"Device disabled: {device_id}")
        return d.to_dict()
    # Fallback to legacy DEVICES dict
    device = DEVICES.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device: {device_id}")
    if device.get("enabled", True) is False or device.get("type") == "disabled":
        raise HTTPException(status_code=403, detail=f"Device disabled: {device_id}")
    return device


async def telegram_received_cb(telegram):
    """Step 1: Receive raw telegram — push to queue immediately. No processing here."""
    try:
        if not hasattr(telegram, 'destination_address'): return
        try:
            raw_telegram_queue.put_nowait(telegram)
        except asyncio.QueueFull:
            logger.warning("raw_telegram_queue full — dropping telegram")
    except Exception as e:
        logger.error("Telegram listener error: %s", e)


async def process_telegrams():
    """
    Step 2: Telegram Parser Worker.
    Reads raw telegrams, resolves device via DeviceRegistry (O(1)),
    updates StateManager, then publishes domain events via EventBus.
    
    DOES NOT write to DB — that's the DB Writer subscriber's job.
    DOES NOT push to SSE directly — that's the SSE subscriber's job.
    """
    while True:
        telegram = await raw_telegram_queue.get()
        try:
            ga = str(telegram.destination_address)
            source_addr = str(telegram.source_address) if hasattr(telegram, 'source_address') else "0.0.0"

            # Determine source identity
            source = 'KNX Bus'
            if _knx_driver and _knx_driver.current_address:
                if source_addr == _knx_driver.current_address:
                    source = 'Dashboard/AI'

            # ── Bus Monitor: publish raw telegram event (to Bus Monitor UI) ──
            raw_data = {
                "timestamp": int(time.time()),
                "source_address": source_addr,
                "destination_address": ga,
                "payload": str(telegram.payload),
                "direction": telegram.direction.value if hasattr(telegram, 'direction') else "Incoming"
            }
            for q in sse_bus_clients:
                try:
                    q.put_nowait(raw_data)
                except asyncio.QueueFull:
                    pass

            # ── Device Lookup via DeviceRegistry O(1) ────────────────────────
            device = device_registry.find_by_ga(ga)
            if device is None:
                # Fallback: check legacy DEVICES dict
                device_id = None
                state_str = "UNKNOWN"
                brightness = None
                for did, dev in DEVICES.items():
                    if dev.get('onoff_ga') == ga or dev.get('status_ga') == ga:
                        device_id = did
                        if hasattr(telegram.payload, 'value'):
                            val = telegram.payload.value
                            state_str = "ON" if val else "OFF"
                        break
                    elif dev.get('brightness_ga') == ga or dev.get('brightness_status_ga') == ga:
                        device_id = did
                        if hasattr(telegram.payload, 'value'):
                            val = telegram.payload.value
                            state_str = str(val[0]) if isinstance(val, tuple) else str(val)
                        break
            else:
                device_id = device.device_id
                brightness = None
                state_str = "UNKNOWN"
                if hasattr(telegram.payload, 'value'):
                    val = telegram.payload.value
                    if ga in (device.onoff_ga, device.status_ga):
                        state_str = "ON" if val else "OFF"
                    elif ga in (device.brightness_ga, device.brightness_status_ga):
                        raw_val = val[0] if isinstance(val, tuple) else val
                        try:
                            brightness = int(raw_val)
                            state_str = f"{brightness}%"
                        except Exception:
                            state_str = str(raw_val)

            if device_id:
                # ── Step 3: Update StateManager (RAM) ────────────────────────
                state_manager.update(
                    device_id=device_id,
                    state=state_str,
                    source=source,
                    brightness=brightness if 'brightness' in dir() else None,
                )

                # ── Step 4: Publish domain event → EventBus ──────────────────
                await event_bus.publish(DomainEvent(
                    event_type=EventType.DEVICE_STATE_CHANGED,
                    device_id=device_id,
                    source=source,
                    payload={
                        "device_id": device_id,
                        "action": "bus_event",
                        "state": state_str,
                        "source": source,
                        "timestamp": int(time.time()),
                    }
                ))

        except Exception as e:
            logger.error("process_telegrams error: %s", e)
        finally:
            raw_telegram_queue.task_done()


async def _sse_state_subscriber(event: DomainEvent):
    """EventBus subscriber: pushes device state changes to all SSE event clients."""
    data = event.to_sse_dict()
    for q in sse_event_clients:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass


async def _db_writer_subscriber(event: DomainEvent):
    """EventBus subscriber: writes device state change to device_history table."""
    p = event.payload
    try:
        async with aiosqlite.connect(str(_SMARTHOME_DB)) as db:
            await db.execute(
                'INSERT INTO device_history (device_id, action, state, source, timestamp) VALUES (?, ?, ?, ?, ?)',
                (p.get('device_id'), p.get('action', 'bus_event'), p.get('state'), p.get('source'), p.get('timestamp', int(time.time())))
            )
            await db.commit()
    except Exception as e:
        logger.error("db_writer_subscriber error: %s", e)

async def start_knx():
    global _knx_driver, xknx_instance

    if _knx_driver is not None and _knx_driver.is_connected:
        return

    _knx_driver = KNXDriver(
        gateway_ip=KNX_GATEWAY_IP,
        gateway_port=KNX_GATEWAY_PORT,
        local_ip=KNX_LOCAL_IP_ENV
    )
    _knx_driver.register_callback(telegram_received_cb)
    
    await _knx_driver.start()
    
    # Backward compatibility dummy
    xknx_instance = _knx_driver if _knx_driver.is_connected else None


async def stop_knx():
    global _knx_driver, xknx_instance

    if _knx_driver is not None:
        await _knx_driver.stop()
        _knx_driver = None
        xknx_instance = None


async def _do_fetch_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=21.0285&longitude=105.8542&current_weather=true"
        def _get():
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        
        data = await asyncio.to_thread(_get)
        current = data.get("current_weather", {})
        weather_code = current.get("weathercode", 0)
        temp = current.get("temperature", 25.0)

        print(f"[WEATHER] Fetch success: Temp={temp}C, Code={weather_code}")

        # WMO Codes:
        # <=3: Clear, Partly cloudy -> Sunlight ON
        # >=50: Rain, Drizzle, Thunderstorm -> Rain ON
        
        if weather_code >= 50:
            if "den_e" in DEVICES and DEVICES["den_e"].get("onoff_ga"):
                await execute_action({"device": "den_e", "action": "on", "who": "automation:weather"})
            if "den_f" in DEVICES and DEVICES["den_f"].get("onoff_ga"):
                await execute_action({"device": "den_f", "action": "off", "who": "automation:weather"})
            print("[WEATHER] Action: Mưa -> Bật đèn mô phỏng mưa (den_e)")
        elif weather_code <= 3:
            if "den_f" in DEVICES and DEVICES["den_f"].get("onoff_ga"):
                await execute_action({"device": "den_f", "action": "on", "who": "automation:weather"})
            if "den_e" in DEVICES and DEVICES["den_e"].get("onoff_ga"):
                await execute_action({"device": "den_e", "action": "off", "who": "automation:weather"})
            print("[WEATHER] Action: Nắng -> Bật đèn mô phỏng nắng (den_f)")
        else:
            if "den_e" in DEVICES and DEVICES["den_e"].get("onoff_ga"):
                await execute_action({"device": "den_e", "action": "off", "who": "automation:weather"})
            if "den_f" in DEVICES and DEVICES["den_f"].get("onoff_ga"):
                await execute_action({"device": "den_f", "action": "off", "who": "automation:weather"})
            print("[WEATHER] Action: Mây/Mù -> Tắt các đèn mô phỏng thời tiết")
            
        return {"temp": temp, "code": weather_code}
    except Exception as e:
        print(f"[WEATHER] Fetch error: {e}")
        return {"error": str(e)}

async def fetch_real_weather_loop():
    while True:
        await _do_fetch_weather()
        # Sleep for 1 hour (3600 seconds)
        await asyncio.sleep(3600)

async def _scene_activate_fn(scene_id: str, who: str):
    """Callback for ActionExecutor to activate scenes."""
    try:
        conn = sqlite3.connect(str(_SMARTHOME_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT sa.* FROM scene_actions sa WHERE sa.scene_id=?", (scene_id,)
        ).fetchall()
        conn.close()
        for row in rows:
            action_data = dict(row)
            action_data["who"] = who
            delay_sec = float(action_data.get("delay_seconds") or 0.0)
            if delay_sec > 0:
                await asyncio.sleep(delay_sec)
            try:
                await execute_action(action_data)
            except Exception as e:
                logger.error("scene_activate_fn: %s", e)
    except Exception as e:
        logger.error("scene_activate_fn: scene '%s' error: %s", scene_id, e)


def _init_domain_layer():
    """Initialize Domain Layer singletons after write_knx is defined."""
    global _command_pipeline, _automation_engine, _audit_logger, _notification_engine, _health_service

    # Init DB schemas
    init_automation_schema(_SMARTHOME_DB)       # v1 (backward compat)
    init_automation_schema_v2(_SMARTHOME_DB)    # v2 (new full schema)
    init_audit_schema(_SMARTHOME_DB)
    _init_floorplan_schema()
    _init_analytics_schema()

    # Wire up CommandPipeline
    _command_pipeline = CommandPipeline(
        registry=device_registry,
        state_manager=state_manager,
        event_bus=event_bus,
        default_driver=_knx_driver or KNXDriver(KNX_GATEWAY_IP, KNX_GATEWAY_PORT, KNX_LOCAL_IP_ENV),
    )

    _notification_engine = NotificationEngine(event_bus=event_bus)
    _notification_engine.register()
    
    # Wire up AutomationEngine v2 (replaces v1)
    _automation_engine = AutomationEngineV2(
        db_path=_SMARTHOME_DB,
        event_bus=event_bus,
        state_manager=state_manager,
        command_pipeline=_command_pipeline,
        scene_fn=_scene_activate_fn,
    )
    _automation_engine.load_rules()
    _automation_engine.register()

    # Wire up AuditLogger
    _audit_logger = AuditLogger(db_path=_SMARTHOME_DB, event_bus=event_bus)
    _audit_logger.register()

    # Register core EventBus subscribers
    event_bus.subscribe(EventType.DEVICE_STATE_CHANGED, _sse_state_subscriber)
    event_bus.subscribe(EventType.DEVICE_STATE_CHANGED, _db_writer_subscriber)
    event_bus.subscribe(EventType.AUTOMATION_TRIGGERED, _sse_state_subscriber)

    # Wire up HealthService
    def _get_knx_status():
        return {
            "connected": _knx_driver.is_connected if _knx_driver else False,
            "knx_connected": _knx_driver.is_connected if _knx_driver else False,
            "gateway": f"{KNX_GATEWAY_IP}:{KNX_GATEWAY_PORT}",
            "knx_gateway_ip": KNX_GATEWAY_IP,
            "knx_gateway_port": KNX_GATEWAY_PORT,
            "tunnel_state": _knx_driver.tunnel_state if _knx_driver else "DISCONNECTED",
            "interface_ip": _knx_driver.gateway_ip if _knx_driver else KNX_GATEWAY_IP,
            "interface_port": _knx_driver.gateway_port if _knx_driver else KNX_GATEWAY_PORT,
            "reconnect_count": _knx_driver.reconnect_count if _knx_driver else 0,
            "connection_time": _knx_driver.connection_time if _knx_driver else None,
        }

    _health_service = HealthService(
        state_manager=state_manager,
        device_registry=device_registry,
        event_bus=event_bus,
        command_pipeline=_command_pipeline,
        automation_engine=_automation_engine,
        raw_queue=raw_telegram_queue,
        event_queue=device_event_queue,
        sse_event_clients=sse_event_clients,
        sse_bus_clients=sse_bus_clients,
        get_knx_status_fn=_get_knx_status,
    )

    logger.info("Domain Layer v3.1 initialized: Registry=%d devices, Rules=%d",
                device_registry.count(), len(_automation_engine.get_rules()))


@app.on_event("startup")
async def startup_event():
    _init_domain_layer()
    # Serve uploaded floor plan images
    import os
    os.makedirs(str(BASE_DIR / 'uploads'), exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / 'uploads')), name="uploads")
    await start_knx()
    asyncio.create_task(fetch_real_weather_loop())
    asyncio.create_task(process_telegrams())
    logger.info("KNX Smart Home Platform v3.1 started")


@app.post("/test-weather")
async def test_weather():
    result = await _do_fetch_weather()
    return {"status": "ok", "result": result}

async def sse_event_generator(q: asyncio.Queue):
    try:
        while True:
            data = await q.get()
            yield dict(data=json.dumps(data))
    except asyncio.CancelledError:
        pass

@app.get("/events/stream")
async def stream_events(request: Request):
    q = asyncio.Queue()
    sse_event_clients.append(q)
    async def sse_wrapper():
        try:
            async for msg in sse_event_generator(q):
                if await request.is_disconnected():
                    break
                yield msg
        finally:
            sse_event_clients.remove(q)
    return EventSourceResponse(sse_wrapper())

@app.get("/bus/stream")
async def stream_bus(request: Request):
    q = asyncio.Queue()
    sse_bus_clients.append(q)
    async def sse_wrapper():
        try:
            async for msg in sse_event_generator(q):
                if await request.is_disconnected():
                    break
                yield msg
        finally:
            sse_bus_clients.remove(q)
    return EventSourceResponse(sse_wrapper())


@app.on_event("shutdown")
async def shutdown_event():
    await stop_knx()


async def write_knx(ga: str, value: Any, value_type: Optional[str] = None):
    global _knx_driver

    async with knx_lock:
        if _knx_driver is None or not _knx_driver.is_connected:
            await start_knx()

        if _knx_driver is None or not _knx_driver.is_connected:
            raise HTTPException(
                status_code=503,
                detail="KNX connection is not ready. Có thể KNX IP Interface đang hết tunnel connection."
            )

        try:
            await _knx_driver.write(ga, value, value_type=value_type)
            await asyncio.sleep(0.8)

        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"KNX write failed: {type(exc).__name__}: {exc}"
            )


async def read_knx_status(ga: str, value_type: str = "switch"):
    global _knx_driver

    if _knx_driver is None or not _knx_driver.is_connected:
        await start_knx()

    if _knx_driver is None or not _knx_driver.is_connected:
        return None

    try:
        return await _knx_driver.read(ga, value_type=value_type)
    except Exception as exc:
        print(f"KNX read failed for GA {ga}: {type(exc).__name__}: {exc}")
        return None


async def execute_action(action_data: dict):
    """
    Execute a device action via CommandPipeline.
    CommandPipeline handles: Permission, Priority, Execution, StateManager update, EventBus publish, Audit.
    """
    action = ActionItem(**action_data)

    if _command_pipeline is None:
        raise HTTPException(status_code=500, detail="Command Pipeline not initialized")

    who = action_data.get("who", "api")
    priority_val = action_data.get("priority", CommandPriority.MANUAL)
    cmd = Command(
        device_id=action.device,
        action=action.action,
        value=action.value,
        reason=action.reason,
        who=who,
        priority=CommandPriority(priority_val) if isinstance(priority_val, int) else CommandPriority.MANUAL,
    )
    result = await _command_pipeline.execute(cmd)
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.rejection_reason or result.error or "Command failed"
        )
    
    device = get_device(action.device)
    return {
        "device": action.device,
        "name": device["name"],
        "action": action.action,
        "value": action.value,
        "state": result.result_state,
        "latency_ms": result.latency_ms,
        "reason": action.reason,
    }


async def scheduled_action_runner(task_id: str, command: ScheduleCommand, run_at: datetime):
    delay = (run_at - datetime.now()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    
    if task_id not in SCHEDULED_TASKS:
        return
        
    task_data = SCHEDULED_TASKS.pop(task_id, None)
    if task_data:
        try:
            await execute_action({
                "device": command.device,
                "action": command.action,
                "value": command.value,
                "reason": command.reason or f"Hẹn giờ (ID: {task_id})"
            })
            print(f"Executed scheduled task {task_id}")
        except Exception as e:
            print(f"Failed to execute scheduled task {task_id}: {e}")


def create_proposal(summary: str, actions: list[dict], require_confirm: bool = True):
    if not actions:
        raise HTTPException(status_code=400, detail="Proposal không có action nào")

    proposal_id = secrets.token_hex(3).upper()

    PENDING_PROPOSALS[proposal_id] = {
        "proposal_id": proposal_id,
        "summary": summary,
        "actions": actions,
        "require_confirm": require_confirm,
        "status": "pending"
    }

    return PENDING_PROPOSALS[proposal_id]


def build_environment_actions(command: EnvironmentProposalCommand):
    actions = []
    summary_parts = []

    if command.sun_percent is not None:
        sun = command.sun_percent
        summary_parts.append(f"ánh sáng ngoài trời {sun}%")

        actions.append({
            "device": "g1_den_tran",
            "action": "on",
            "reason": f"Bật G1 Đèn Trần để mô phỏng ánh sáng ngoài trời {sun}%"
        })

        actions.append({
            "device": "g1_den_tran",
            "action": "brightness",
            "value": sun,
            "reason": f"Dim G1 Đèn Trần ở mức {sun}%"
        })

        if sun >= 80:
            actions += [
                {"device": "den_led_day", "action": "off", "reason": "Ngoài trời rất sáng, tắt LED dây"},
                {"device": "den_tron", "action": "off", "reason": "Ngoài trời rất sáng, tắt đèn chính"},
                {"device": "den_d", "action": "off", "reason": "Ngoài trời rất sáng, tắt đèn phụ"}
            ]
        elif sun >= 50:
            actions += [
                {"device": "den_led_day", "action": "off", "reason": "Ngoài trời đủ sáng, tắt LED dây"},
                {"device": "den_tron", "action": "off", "reason": "Ngoài trời đủ sáng, tắt đèn chính"},
                {"device": "den_d", "action": "off", "reason": "Ngoài trời đủ sáng, tắt đèn phụ"}
            ]
        elif sun >= 25:
            actions += [
                {"device": "den_led_day", "action": "on", "reason": "Ánh sáng yếu, bật LED dây bù sáng nhẹ"},
                {"device": "den_tron", "action": "off", "reason": "Chưa quá tối, tắt đèn chính"},
                {"device": "den_d", "action": "off", "reason": "Chưa quá tối, tắt đèn phụ"}
            ]
        else:
            actions += [
                {"device": "den_led_day", "action": "on", "reason": "Trời tối, bật LED dây"},
                {"device": "den_tron", "action": "on", "reason": "Trời tối, bật đèn chính"},
                {"device": "den_d", "action": "on", "reason": "Trời tối, bật đèn phụ"}
            ]

    if command.rain_expected is not None:
        if command.rain_expected:
            summary_parts.append("có mưa")
            actions.append({
                "device": "den_e",
                "action": "on",
                "reason": "Dự báo có mưa, bật Đèn E mô phỏng mưa/đóng cửa/tắt tưới"
            })
        else:
            summary_parts.append("không mưa")
            actions.append({
                "device": "den_e",
                "action": "off",
                "reason": "Không mưa, tắt Đèn E"
            })

    if command.outside_temp is not None:
        temp = command.outside_temp
        summary_parts.append(f"nhiệt độ ngoài trời {temp}°C")

        if temp >= 32:
            actions += [
                {"device": "den_f", "action": "on", "reason": f"Nhiệt độ {temp}°C, bật Đèn F mô phỏng điều hòa"},
                {"device": "den_g", "action": "off", "reason": "Trời quá nóng, không ưu tiên thông gió"},
                {"device": "den_h", "action": "off", "reason": "Không phải thời tiết mát"}
            ]
        elif temp >= 26:
            actions += [
                {"device": "den_f", "action": "off", "reason": "Chưa cần điều hòa"},
                {"device": "den_g", "action": "on", "reason": f"Nhiệt độ {temp}°C, bật Đèn G mô phỏng thông gió/fresh air"},
                {"device": "den_h", "action": "off", "reason": "Không phải thời tiết mát"}
            ]
        else:
            actions += [
                {"device": "den_f", "action": "off", "reason": "Thời tiết mát, tắt mô phỏng điều hòa"},
                {"device": "den_g", "action": "off", "reason": "Thời tiết mát, tắt mô phỏng thông gió"},
                {"device": "den_h", "action": "on", "reason": f"Nhiệt độ {temp}°C, bật Đèn H mô phỏng thời tiết mát"}
            ]

    if not summary_parts:
        raise HTTPException(status_code=400, detail="Thiếu dữ liệu môi trường để lập phương án")

    summary = "Mô phỏng theo môi trường: " + ", ".join(summary_parts)

    if command.note:
        summary += f". Ghi chú: {command.note}"

    return summary, actions


@app.get("/health")
async def health():
    """Basic health check (backward compat)."""
    return {
        "ok": True,
        "version": "3.0.0",
        "knx_gateway_ip": KNX_GATEWAY_IP,
        "knx_gateway_port": KNX_GATEWAY_PORT,
        "knx_connected": xknx_instance is not None,
        "devices": device_registry.count() or len(DEVICES),
        "pending_proposals": len(PENDING_PROPOSALS)
    }


@app.get("/health/detail")
async def health_detail():
    """Full system health metrics for Health Monitor dashboard."""
    if _health_service is None:
        return {"error": "Health service not initialized"}
    return await _health_service.get_detail()


@app.get("/devices/{device_id}/state")
async def get_device_state(device_id: str):
    """
    Get current runtime state from StateManager (RAM).
    Much faster than reading from DB or polling KNX Bus.
    """
    s = state_manager.get(device_id)
    if s is None:
        device = device_registry.get(device_id)
        if device is None:
            raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
        return {
            "device_id": device_id,
            "state": "UNKNOWN",
            "message": "No state received from KNX bus yet"
        }
    return s.to_dict()


@app.get("/devices/states")
async def get_all_states():
    """Get all device states from StateManager."""
    return {did: s.to_dict() for did, s in state_manager.get_all().items()}


# ── Automation Engine Endpoints ──────────────────────────────────

class AutomationRuleCommand(BaseModel):
    rule_id: Optional[str] = None
    name: str
    enabled: bool = True
    priority: int = 50
    trigger_type: str = "device_state"
    trigger_device_id: Optional[str] = None
    trigger_state: Optional[str] = None
    trigger_operator: str = "=="
    condition: Optional[dict] = None
    actions: list[dict]
    cooldown_seconds: float = 5.0


@app.get("/automation/rules")
async def get_automation_rules():
    """Get all automation rules."""
    if _automation_engine is None:
        return {"rules": []}
    return {"rules": _automation_engine.get_all_rules_from_db()}


@app.post("/automation/rules")
async def create_automation_rule(cmd: AutomationRuleCommand):
    """Create a new automation rule."""
    import uuid
    rule_id = cmd.rule_id or str(uuid.uuid4())[:8]
    condition_json = json.dumps(cmd.condition) if cmd.condition else None
    actions_json = json.dumps(cmd.actions)

    conn = sqlite3.connect(str(_SMARTHOME_DB))
    try:
        conn.execute("""
            INSERT OR REPLACE INTO automation_rules
            (rule_id, name, enabled, priority, trigger_type, trigger_device_id, trigger_state,
             trigger_operator, condition_json, actions_json, cooldown_seconds, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule_id, cmd.name, cmd.enabled, cmd.priority, cmd.trigger_type,
               cmd.trigger_device_id, cmd.trigger_state, cmd.trigger_operator,
               condition_json, actions_json, cmd.cooldown_seconds, time.time(), time.time()))
        conn.commit()
    finally:
        conn.close()

    # Reload rules into engine
    if _automation_engine:
        _automation_engine.load_rules()

    return {"ok": True, "rule_id": rule_id}


@app.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: str):
    """Delete an automation rule."""
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute("DELETE FROM automation_rules WHERE rule_id = ?", (rule_id,))
    conn.commit()
    conn.close()
    if _automation_engine:
        _automation_engine.load_rules()
    return {"ok": True, "deleted": rule_id}


@app.put("/automation/rules/{rule_id}/toggle")
async def toggle_automation_rule(rule_id: str):
    """Enable or disable a rule."""
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute(
        "UPDATE automation_rules SET enabled = NOT enabled, updated_at = ? WHERE rule_id = ?",
        (time.time(), rule_id)
    )
    conn.commit()
    conn.close()
    if _automation_engine:
        _automation_engine.load_rules()
    return {"ok": True}


# ── Audit Trail Endpoint ────────────────────────────────────────

@app.get("/audit")
async def get_audit_log(limit: int = 100, device_id: Optional[str] = None):
    """Get command audit trail."""
    try:
        async with aiosqlite.connect(str(_SMARTHOME_DB)) as db:
            db.row_factory = aiosqlite.Row
            if device_id:
                rows = await (await db.execute(
                    "SELECT * FROM command_audit WHERE device_id=? ORDER BY timestamp DESC LIMIT ?",
                    (device_id, limit)
                )).fetchall()
            else:
                rows = await (await db.execute(
                    "SELECT * FROM command_audit ORDER BY timestamp DESC LIMIT ?", (limit,)
                )).fetchall()
            return {"audit": [dict(r) for r in rows]}
    except Exception as e:
        return {"audit": [], "error": str(e)}


# ── Platform Management ────────────────────────────────────────────

@app.post("/platform/reload")
async def reload_platform():
    """Reload DeviceRegistry and AutomationRules from DB (no restart needed)."""
    n_devices = device_registry.reload()
    DEVICES.clear()
    DEVICES.update(load_devices())
    n_rules = _automation_engine.load_rules() if _automation_engine else 0
    return {
        "ok": True,
        "devices_loaded": n_devices,
        "rules_loaded": n_rules,
    }

@app.get("/platform/state-manager")
async def getstate_manager_snapshot():
    """Get a full snapshot of StateManager for debugging."""
    return state_manager.get_snapshot()

@app.get("/platform/event-bus")
async def get_event_bus_stats():
    """Get EventBus statistics."""
    return event_bus.get_stats()


# ══════════════════════════════════════════════════════════════════
# FLOOR PLAN / DIGITAL TWIN
# ══════════════════════════════════════════════════════════════════

def _init_floorplan_schema():
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS floor_plans (
            plan_id      TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            image_path   TEXT,
            image_width  INTEGER DEFAULT 1920,
            image_height INTEGER DEFAULT 1080,
            order_index  INTEGER DEFAULT 0,
            created_at   REAL
        );
        CREATE TABLE IF NOT EXISTS floor_plan_devices (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id    TEXT NOT NULL,
            device_id  TEXT NOT NULL,
            x_percent  REAL NOT NULL,
            y_percent  REAL NOT NULL,
            icon_type  TEXT DEFAULT 'light',
            label      TEXT,
            FOREIGN KEY (plan_id) REFERENCES floor_plans(plan_id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


@app.get("/floorplan/plans")
async def list_floor_plans():
    """List all floor plans."""
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM floor_plans ORDER BY order_index, name").fetchall()
    conn.close()
    return {"plans": [dict(r) for r in rows]}


@app.post("/floorplan/plans")
async def create_floor_plan(body: dict):
    """Create a new floor plan (without image — image upload is separate)."""
    plan_id = body.get("plan_id") or str(uuid.uuid4())[:8]
    name = body.get("name", "Floor Plan")
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute(
        "INSERT OR REPLACE INTO floor_plans (plan_id, name, image_path, image_width, image_height, order_index, created_at) VALUES (?,?,?,?,?,?,?)",
        (plan_id, name, body.get("image_path"), body.get("image_width", 1920),
         body.get("image_height", 1080), body.get("order_index", 0), time.time())
    )
    conn.commit()
    conn.close()
    return {"ok": True, "plan_id": plan_id}


@app.delete("/floorplan/plans/{plan_id}")
async def delete_floor_plan(plan_id: str):
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute("DELETE FROM floor_plans WHERE plan_id=?", (plan_id,))
    conn.execute("DELETE FROM floor_plan_devices WHERE plan_id=?", (plan_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/floorplan/plans/{plan_id}")
async def get_floor_plan(plan_id: str):
    """Get a floor plan with all device positions and their current states."""
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.row_factory = sqlite3.Row
    plan = conn.execute("SELECT * FROM floor_plans WHERE plan_id=?", (plan_id,)).fetchone()
    if not plan:
        conn.close()
        raise HTTPException(status_code=404, detail="Floor plan not found")
    devices = conn.execute(
        "SELECT * FROM floor_plan_devices WHERE plan_id=?", (plan_id,)
    ).fetchall()
    conn.close()

    # Enrich with current state from StateManager
    device_list = []
    for d in devices:
        dev = dict(d)
        state = state_manager.get(dev["device_id"])
        dev["current_state"] = state.to_dict() if state else {"state": "UNKNOWN"}
        # Get device metadata from registry
        reg_dev = device_registry.get(dev["device_id"])
        dev["device_name"] = reg_dev.name if reg_dev else dev["device_id"]
        dev["device_type"] = reg_dev.type if reg_dev else "light"
        device_list.append(dev)

    return {"plan": dict(plan), "devices": device_list}


@app.put("/floorplan/plans/{plan_id}/devices")
async def save_floor_plan_devices(plan_id: str, body: dict):
    """
    Save device layout for a floor plan (bulk replace).
    body: {"devices": [{"device_id": ..., "x_percent": ..., "y_percent": ..., "icon_type": ..., "label": ...}]}
    """
    devices = body.get("devices", [])
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute("DELETE FROM floor_plan_devices WHERE plan_id=?", (plan_id,))
    for d in devices:
        conn.execute(
            "INSERT INTO floor_plan_devices (plan_id, device_id, x_percent, y_percent, icon_type, label) VALUES (?,?,?,?,?,?)",
            (plan_id, d["device_id"], d.get("x_percent", 50), d.get("y_percent", 50),
             d.get("icon_type", "light"), d.get("label"))
        )
    conn.commit()
    conn.close()
    return {"ok": True, "saved": len(devices)}


@app.post("/floorplan/upload/{plan_id}")
async def upload_floor_plan_image(plan_id: str, file: UploadFile = File(...)):
    """Upload a floor plan image (PNG/JPG/SVG)."""
    import shutil
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png"
    if ext not in ("png", "jpg", "jpeg", "svg", "webp"):
        raise HTTPException(status_code=400, detail="Only PNG, JPG, SVG, WEBP allowed")

    filename = f"floorplan_{plan_id}.{ext}"
    dest = BASE_DIR / "uploads" / filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    image_path = f"/uploads/{filename}"
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute(
        "UPDATE floor_plans SET image_path=? WHERE plan_id=?", (image_path, plan_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "image_path": image_path}


# ══════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════

def _init_analytics_schema():
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analytics_daily (
            date          TEXT NOT NULL,
            device_id     TEXT NOT NULL,
            on_count      INTEGER DEFAULT 0,
            off_count     INTEGER DEFAULT 0,
            total_on_secs INTEGER DEFAULT 0,
            command_count INTEGER DEFAULT 0,
            ai_count      INTEGER DEFAULT 0,
            auto_count    INTEGER DEFAULT 0,
            manual_count  INTEGER DEFAULT 0,
            PRIMARY KEY (date, device_id)
        );
    """)
    conn.commit()
    conn.close()


@app.get("/analytics/summary")
async def analytics_summary(days: int = 30):
    """Overall summary for the past N days."""
    try:
        async with aiosqlite.connect(str(_SMARTHOME_DB)) as db:
            db.row_factory = aiosqlite.Row

            # Total commands from audit
            row = await (await db.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN result='SUCCESS' THEN 1 ELSE 0 END) as success "
                "FROM command_audit WHERE timestamp > ?",
                (time.time() - days * 86400,)
            )).fetchone()
            total_cmds = dict(row)

            # Commands by source
            rows = await (await db.execute(
                "SELECT who, COUNT(*) as cnt FROM command_audit WHERE timestamp > ? GROUP BY who ORDER BY cnt DESC LIMIT 10",
                (time.time() - days * 86400,)
            )).fetchall()
            by_source = [dict(r) for r in rows]

            # Most active devices
            rows = await (await db.execute(
                "SELECT device_id, COUNT(*) as cnt FROM command_audit WHERE timestamp > ? GROUP BY device_id ORDER BY cnt DESC LIMIT 10",
                (time.time() - days * 86400,)
            )).fetchall()
            top_devices = [dict(r) for r in rows]

            # Automation stats
            row2 = await (await db.execute(
                "SELECT COUNT(*) as total FROM command_audit WHERE who LIKE 'automation:%' AND timestamp > ?",
                (time.time() - days * 86400,)
            )).fetchone()
            auto_total = dict(row2)["total"]

            # Events by hour (last 7 days for heatmap)
            rows = await (await db.execute(
                """SELECT CAST(strftime('%H', datetime(timestamp, 'unixepoch', 'localtime')) AS INTEGER) as hour,
                          COUNT(*) as cnt
                   FROM device_history WHERE timestamp > ?
                   GROUP BY hour ORDER BY hour""",
                (time.time() - 7 * 86400,)
            )).fetchall()
            by_hour = [dict(r) for r in rows]

            return {
                "period_days": days,
                "commands": total_cmds,
                "automation_commands": auto_total,
                "by_source": by_source,
                "top_devices": top_devices,
                "by_hour": by_hour,
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/analytics/devices/{device_id}")
async def analytics_device(device_id: str, days: int = 30):
    """Stats for a specific device."""
    try:
        async with aiosqlite.connect(str(_SMARTHOME_DB)) as db:
            db.row_factory = aiosqlite.Row
            # History count
            rows = await (await db.execute(
                "SELECT action, state, COUNT(*) as cnt FROM device_history WHERE device_id=? AND timestamp>? GROUP BY action, state ORDER BY cnt DESC",
                (device_id, time.time() - days * 86400)
            )).fetchall()
            # Daily command count
            daily = await (await db.execute(
                """SELECT strftime('%Y-%m-%d', datetime(timestamp,'unixepoch','localtime')) as date,
                          COUNT(*) as cnt
                   FROM command_audit WHERE device_id=? AND timestamp>?
                   GROUP BY date ORDER BY date""",
                (device_id, time.time() - days * 86400)
            )).fetchall()
            return {
                "device_id": device_id,
                "period_days": days,
                "state_history": [dict(r) for r in rows],
                "daily_commands": [dict(r) for r in daily],
            }
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════
# AUTOMATION V2 ENDPOINTS (replace old v1 endpoints)
# ══════════════════════════════════════════════════════════════════

class AutomationRuleV2Command(BaseModel):
    rule_id: Optional[str] = None
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 50
    trigger: dict                           # {"type": "device_state", "device_id": ..., ...}
    conditions: Optional[dict] = None       # AND/OR/NOT tree
    actions: list[dict]                     # action list
    time_filter: Optional[dict] = None      # {"days": [...], "from": "07:00", "to": "22:00"}
    cooldown_seconds: float = 5.0
    max_runs_per_day: int = 0


def audit_log(who: str, command_id: str, device_id: str, action: str, old_value: str, new_value: str, priority: int, result: str, reason: str, latency_ms: int):
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute('''
        INSERT INTO command_audit (
            who, device_id, action, new_value, result, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        who, device_id, action, new_value, result, time.time()
    ))
    conn.commit()
    conn.close()

@app.get("/automation/rules/v2")
async def get_automation_rules_v2():
    """Get all automation rules (v2 schema with full conditions/actions)."""
    if _automation_engine is None:
        return {"rules": []}
    return {"rules": _automation_engine.get_all_rules_from_db()}


def validate_automation_rule_v2(cmd: AutomationRuleV2Command):
    if not cmd.name or not cmd.name.strip():
        raise HTTPException(status_code=400, detail="Rule name cannot be empty")
    
    if not cmd.trigger or "type" not in cmd.trigger:
        raise HTTPException(status_code=400, detail="Trigger is required")
        
    if not cmd.actions or len(cmd.actions) == 0:
        raise HTTPException(status_code=400, detail="At least one action is required")
        
    # Validate Trigger
    if cmd.trigger.get("type") == "device_state":
        dev_id = cmd.trigger.get("device_id")
        if dev_id and dev_id not in DEVICES:
            raise HTTPException(status_code=400, detail=f"Trigger device '{dev_id}' not found")
            
    # Validate Actions & Infinite Loop
    trigger_dev_id = cmd.trigger.get("device_id") if cmd.trigger.get("type") == "device_state" else None
    for act in cmd.actions:
        if act.get("type") == "control":
            dev_id = act.get("device_id")
            if dev_id and dev_id not in DEVICES:
                raise HTTPException(status_code=400, detail=f"Action device '{dev_id}' not found")
            if dev_id and dev_id == trigger_dev_id:
                raise HTTPException(status_code=400, detail=f"Rule cannot trigger and control the same device '{dev_id}' directly (infinite loop protection)")
        elif act.get("type") not in ["control", "activate_scene", "delay", "wait_for", "set_var", "notify", "repeat", "if_action"]:
            raise HTTPException(status_code=400, detail=f"Invalid action type '{act.get('type')}'")

@app.post("/automation/rules/v2")
async def create_automation_rule_v2(cmd: AutomationRuleV2Command, request: Request):
    """Create or update a rule (v2 schema)."""
    check_auth(request.headers.get("Authorization") or request.headers.get("x-knx-token"))
    validate_automation_rule_v2(cmd)
    
    rule_id = cmd.rule_id or str(uuid.uuid4())[:8]
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute("""
        INSERT OR REPLACE INTO automation_rules_v2
        (rule_id, name, description, enabled, priority, trigger_json, conditions_json,
         actions_json, time_filter_json, cooldown_seconds, max_runs_per_day, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        rule_id, cmd.name, cmd.description, cmd.enabled, cmd.priority,
        json.dumps(cmd.trigger),
        json.dumps(cmd.conditions) if cmd.conditions else None,
        json.dumps(cmd.actions),
        json.dumps(cmd.time_filter) if cmd.time_filter else None,
        cmd.cooldown_seconds, cmd.max_runs_per_day,
        time.time(), time.time()
    ))
    conn.commit()
    conn.close()
    
    # Audit log
    audit_log(
        who="admin", command_id=rule_id, device_id="AUTOMATION", action="CREATE_OR_UPDATE_RULE",
        old_value="", new_value=cmd.name, priority=50, result="SUCCESS", reason="Automation rule created or updated",
        latency_ms=0
    )
    
    if _automation_engine:
        _automation_engine.load_rules()
    return {"ok": True, "rule_id": rule_id}


@app.put("/automation/rules/v2/{rule_id}")
async def update_automation_rule_v2(rule_id: str, cmd: AutomationRuleV2Command):
    cmd.rule_id = rule_id
    return await create_automation_rule_v2(cmd)


@app.delete("/automation/rules/v2/{rule_id}")
async def delete_automation_rule_v2(rule_id: str, request: Request):
    check_auth(request.headers.get("Authorization") or request.headers.get("x-knx-token"))
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    conn.execute("DELETE FROM automation_rules_v2 WHERE rule_id=?", (rule_id,))
    conn.commit()
    conn.close()
    
    audit_log(
        who="admin", command_id=rule_id, device_id="AUTOMATION", action="DELETE_RULE",
        old_value=rule_id, new_value="", priority=50, result="SUCCESS", reason="Rule deleted", latency_ms=0
    )
    
    if _automation_engine:
        _automation_engine.load_rules()
    return {"ok": True, "deleted": rule_id}


@app.put("/automation/rules/v2/{rule_id}/toggle")
async def toggle_automation_rule_v2(rule_id: str, request: Request):
    check_auth(request.headers.get("Authorization") or request.headers.get("x-knx-token"))
    conn = sqlite3.connect(str(_SMARTHOME_DB))
    row = conn.execute("SELECT enabled FROM automation_rules_v2 WHERE rule_id=?", (rule_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Rule not found")
        
    new_status = not bool(row[0])
    conn.execute(
        "UPDATE automation_rules_v2 SET enabled=?, updated_at=? WHERE rule_id=?",
        (new_status, time.time(), rule_id)
    )
    conn.commit()
    conn.close()
    
    audit_log(
        who="admin", command_id=rule_id, device_id="AUTOMATION", action="TOGGLE_RULE",
        old_value=str(not new_status), new_value=str(new_status), priority=50, result="SUCCESS", reason="Rule toggled", latency_ms=0
    )
    
    if _automation_engine:
        _automation_engine.load_rules()
    return {"ok": True}


class RuleTestCommand(BaseModel):
    dry_run: bool = False

@app.post("/automation/rules/v2/{rule_id}/test")
async def test_automation_rule_v2(rule_id: str, request: Request, cmd: RuleTestCommand = None):
    """Manually trigger a rule (for testing)."""
    check_auth(request.headers.get("Authorization") or request.headers.get("x-knx-token"))
    if _automation_engine is None:
        raise HTTPException(status_code=503, detail="Automation engine not ready")
        
    dry_run = cmd.dry_run if cmd else False
    
    rule = next((r for r in _automation_engine._rules if r.rule_id == rule_id), None)
    if rule is None:
        # Try to load from DB
        conn = sqlite3.connect(str(_SMARTHOME_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM automation_rules_v2 WHERE rule_id=?", (rule_id,)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
        rule = RuleV2.from_row(dict(row))

    if not rule.enabled and not dry_run:
        raise HTTPException(status_code=400, detail="Cannot test a disabled rule unless in dry_run mode")

    original_cooldown = rule.cooldown_seconds
    rule.cooldown_seconds = 0  # Bypass cooldown for test
    
    audit_log(
        who="admin", command_id=rule_id, device_id="AUTOMATION", action="TEST_RULE",
        old_value="dry_run" if dry_run else "execute", new_value="", priority=50, result="SUCCESS", reason="Testing rule", latency_ms=0
    )
    
    try:
        if dry_run:
            from core.rule_evaluator import RuleEvaluator
            cond_eval = RuleEvaluator(state_manager)
            passed = cond_eval.evaluate(rule.conditions)
            return {
                "ok": True,
                "rule_id": rule_id,
                "message": "Dry Run Result",
                "condition_passed": passed,
                "would_execute": rule.actions if passed else []
            }
        else:
            await _automation_engine._fire_rule(rule, None)
            return {"ok": True, "rule_id": rule_id, "message": "Rule fired successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        rule.cooldown_seconds = original_cooldown


@app.post("/knx/reconnect")
async def knx_reconnect(x_knx_token: Optional[str] = Header(default=None)):
    check_auth(x_knx_token)
    await stop_knx()
    await asyncio.sleep(1)
    await start_knx()

    return {
        "ok": xknx_instance is not None,
        "knx_connected": xknx_instance is not None
    }


@app.get("/devices")
async def list_devices(x_knx_token: Optional[str] = Header(default=None)):
    check_auth(x_knx_token)
    return DEVICES


@app.post("/devices/add")
async def add_device(
    command: DeviceAddCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)

    if not command.confirmed:
        raise HTTPException(status_code=400, detail="Adding device requires confirmed=true")

    validate_device_id(command.device_id)
    validate_ga(command.onoff_ga, "onoff_ga")
    validate_ga(command.status_ga, "status_ga")
    validate_ga(command.brightness_ga, "brightness_ga")
    validate_ga(command.brightness_status_ga, "brightness_status_ga")
    validate_ga(command.color_ga, "color_ga")
    validate_ga(command.color_status_ga, "color_status_ga")

    if command.device_id in DEVICES:
        raise HTTPException(status_code=409, detail=f"Device already exists: {command.device_id}")

    if command.type != "light":
        raise HTTPException(status_code=400, detail="Currently only light devices are supported")

    if command.supports_brightness and not command.brightness_ga:
        raise HTTPException(status_code=400, detail="brightness_ga is required when supports_brightness=true")

    data = model_to_dict(command)
    data.pop("confirmed", None)
    device_id = data.pop("device_id")

    DEVICES[device_id] = data
    save_devices()

    # Emit event
    from core.event_bus import DomainEvent, EventType
    if 'event_bus' in globals() and event_bus:
        event_bus.publish(DomainEvent(
            event_type=EventType.DEVICE_ADDED,
            source="DeviceWizard",
            payload={"message": f"Added device {device_id}", "action": "reload_required"}
        ))

    return {
        "ok": True,
        "action": "device_added",
        "device_id": device_id,
        "device": DEVICES[device_id]
    }


@app.post("/devices/update")
async def update_device(
    command: DeviceUpdateCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)

    if not command.confirmed:
        raise HTTPException(status_code=400, detail="Updating device requires confirmed=true")

    validate_device_id(command.device_id)

    if command.device_id not in DEVICES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {command.device_id}")

    update_data = model_to_dict(command)
    update_data.pop("confirmed", None)
    device_id = update_data.pop("device_id")

    for ga_field in [
        "onoff_ga",
        "status_ga",
        "brightness_ga",
        "brightness_status_ga",
        "color_ga",
        "color_status_ga"
    ]:
        validate_ga(update_data.get(ga_field), ga_field)

    for key, value in update_data.items():
        if value is not None:
            DEVICES[device_id][key] = value

    save_devices()

    # Emit event
    from core.event_bus import DomainEvent, EventType
    if 'event_bus' in globals() and event_bus:
        event_bus.publish(DomainEvent(
            event_type=EventType.DEVICE_ADDED,
            source="DeviceWizard",
            payload={"message": f"Updated device {device_id}", "action": "reload_required"}
        ))

    return {
        "ok": True,
        "action": "device_updated",
        "device_id": device_id,
        "device": DEVICES[device_id]
    }


@app.post("/devices/disable")
async def disable_device(
    command: DeviceDisableCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)

    if not command.confirmed:
        raise HTTPException(status_code=400, detail="Disabling device requires confirmed=true")

    if command.device_id not in DEVICES:
        raise HTTPException(status_code=404, detail=f"Unknown device: {command.device_id}")

    DEVICES[command.device_id]["enabled"] = False
    save_devices()

    return {
        "ok": True,
        "action": "device_disabled",
        "device_id": command.device_id
    }

@app.get("/devices/export")
async def export_devices(current_user: dict = Depends(auth_utils.require_admin)):
    return DEVICES

@app.post("/devices/import")
async def import_devices(
    request: Request,
    current_user: dict = Depends(auth_utils.require_admin)
):
    try:
        global DEVICES
        payload = await request.json()
        
        mode = payload.get("mode", "skip") # 'skip', 'overwrite', 'rename'
        devices_to_import = payload.get("devices", [])
        
        imported_count = 0
        skipped_count = 0
        failed_count = 0
        
        start_time = time.time()
        
        db_path = BASE_DIR / "smarthome.db"
        import sqlite3
        import json
        
        # Determine existing device IDs
        if 'device_registry' in globals() and device_registry:
            existing_ids = set(device_registry.all_dict().keys())
        else:
            existing_ids = set(DEVICES.keys())

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            for dev in devices_to_import:
                original_device_id = dev.get("device_id")
                if not original_device_id: 
                    failed_count += 1
                    continue
                
                device_id = original_device_id
                
                if device_id in existing_ids:
                    if mode == "skip":
                        skipped_count += 1
                        continue
                    elif mode == "rename":
                        counter = 1
                        while f"{original_device_id}_{counter}" in existing_ids:
                            counter += 1
                        device_id = f"{original_device_id}_{counter}"
                    elif mode == "overwrite":
                        pass # keep device_id, will overwrite in DB
                
                # Backend GA Validation (Triggers Rollback if invalid)
                import re
                for ga_field in ["onoff_ga", "status_ga", "brightness_ga", "brightness_status_ga", "color_ga", "color_status_ga"]:
                    ga_val = dev.get(ga_field)
                    if ga_val:
                        if not re.match(r'^\d+/\d+/\d+$', str(ga_val)):
                            raise ValueError(f"Invalid KNX GA format for {device_id}: {ga_val}")
                        
                        # Duplicate GA check against registry
                        if 'device_registry' in globals() and device_registry:
                            existing_dev = device_registry.find_by_ga(ga_val)
                            if existing_dev and existing_dev.device_id != device_id:
                                raise ValueError(f"Duplicate GA {ga_val} found (already used by {existing_dev.device_id})")
                
                # Insert into DB
                cursor.execute('''
                    INSERT OR REPLACE INTO devices (
                        device_id, name, room, type, 
                        onoff_ga, status_ga, supports_brightness, 
                        brightness_ga, brightness_status_ga, 
                        color_ga, color_status_ga, 
                        role, aliases, safety_level, require_confirm, enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    device_id,
                    dev.get("name", "Unknown"),
                    dev.get("room"),
                    dev.get("type"),
                    dev.get("onoff_ga"),
                    dev.get("status_ga"),
                    dev.get("supports_brightness", False),
                    dev.get("brightness_ga"),
                    dev.get("brightness_status_ga"),
                    dev.get("color_ga"),
                    dev.get("color_status_ga"),
                    dev.get("role"),
                    json.dumps(dev.get("aliases", []), ensure_ascii=False),
                    dev.get("safety_level"),
                    dev.get("require_confirm", False),
                    dev.get("enabled", True)
                ))
                imported_count += 1
                existing_ids.add(device_id)
            
            # Write Audit Log
            duration_ms = int((time.time() - start_time) * 1000)
            cursor.execute('''
                INSERT INTO command_audit (
                    who, device_id, action, new_value, result, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                current_user.get("username", "Admin"),
                "SYSTEM",
                "BULK_IMPORT",
                json.dumps({"mode": mode}, ensure_ascii=False),
                f"Success: {imported_count}, Skipped: {skipped_count}, Failed: {failed_count}, Duration: {duration_ms}ms",
                time.time()
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
        # Reload Registry
        if 'device_registry' in globals() and device_registry:
            device_registry.reload()
            
            # Sync DEVICES dictionary for legacy code
            DEVICES.clear()
            DEVICES.update({d.device_id: d.to_dict() for d in device_registry.all()})
            
            # Write devices.json backup
            with open(BASE_DIR / "devices.json", "w", encoding="utf-8") as f:
                json.dump(DEVICES, f, indent=2, ensure_ascii=False)
        
        # Publish Event
        from core.event_bus import DomainEvent, EventType
        if 'event_bus' in globals() and event_bus:
            # Add DEVICE_REGISTRY_UPDATED if missing
            if not hasattr(EventType, "DEVICE_REGISTRY_UPDATED"):
                EventType.DEVICE_REGISTRY_UPDATED = "device.registry_updated"
                
            event_bus.publish(DomainEvent(
                event_type=EventType.DEVICE_REGISTRY_UPDATED,
                source="BulkImport",
                payload={
                    "imported": imported_count,
                    "skipped": skipped_count,
                    "failed": failed_count
                }
            ))
            
        return {
            "ok": True, 
            "imported": imported_count, 
            "skipped": skipped_count,
            "failed": failed_count,
            "message": f"{imported_count} devices imported successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/devices/{device_id}/status")
async def device_status(device_id: str, current_user: dict = Depends(auth_utils.get_current_user)):
    if device_id not in DEVICES:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Check history for latest state
    conn = sqlite3.connect(str(BASE_DIR / 'smarthome.db'))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT state, timestamp FROM device_history 
        WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1
    ''', (device_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"device_id": device_id, "state": row[0], "timestamp": row[1]}
    return {"device_id": device_id, "state": "UNKNOWN", "timestamp": 0}

@app.get("/devices/{device_id}/history")
async def device_history(device_id: str, current_user: dict = Depends(auth_utils.get_current_user)):
    conn = sqlite3.connect(str(BASE_DIR / 'smarthome.db'))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, action, state, timestamp FROM device_history 
        WHERE device_id = ? ORDER BY timestamp DESC LIMIT 50
    ''', (device_id,))
    rows = cursor.fetchall()
    conn.close()
    
    history = [{"id": r[0], "action": r[1], "state": r[2], "timestamp": r[3]} for r in rows]
    return {"device_id": device_id, "history": history}

@app.post("/light")
async def control_light(
    command: LightCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    action = ActionItem(
        device=command.device,
        action=command.action,
        value=command.value,
        reason="Direct light command"
    )

    result = await execute_action(model_to_dict(action))

    return {
        "ok": True,
        **result
    }


@app.post("/all-off")
async def all_off(x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    results = []

    for device_id, device in DEVICES.items():
        if device.get("enabled", True) and device.get("type") == "light" and device.get("onoff_ga"):
            result = await execute_action({
                "device": device_id,
                "action": "off",
                "reason": "Tắt toàn bộ mô hình"
            })
            results.append(result)

    return {
        "ok": True,
        "action": "all_off",
        "count": len(results),
        "results": results
    }


@app.post("/context")
async def context_control(
    command: ContextCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    if command.mode.lower() == "daylight":
        env = EnvironmentProposalCommand(sun_percent=command.sun_percent)
    elif command.mode.lower() == "weather":
        env = EnvironmentProposalCommand(
            outside_temp=command.outside_temp,
            rain_expected=command.rain_expected
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported context mode: {command.mode}")

    summary, actions = build_environment_actions(env)

    results = []
    for action in actions:
        results.append(await execute_action(action))

    return {
        "ok": True,
        "mode": command.mode,
        "summary": summary,
        "results": results
    }


@app.post("/proposal")
async def create_custom_proposal(
    command: ProposalCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    actions = []

    for action in command.actions:
        validate_action(action)
        actions.append(model_to_dict(action))

    proposal = create_proposal(
        summary=command.summary,
        actions=actions,
        require_confirm=command.require_confirm
    )

    return {
        "ok": True,
        "message": "Proposal created. Chưa điều khiển thiết bị.",
        "proposal": proposal
    }


@app.post("/proposal/environment")
async def create_environment_proposal(
    command: EnvironmentProposalCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    summary, actions = build_environment_actions(command)

    for action in actions:
        validate_action(ActionItem(**action))

    proposal = create_proposal(
        summary=summary,
        actions=actions,
        require_confirm=True
    )

    return {
        "ok": True,
        "message": "Environment proposal created. Chưa điều khiển thiết bị.",
        "proposal": proposal
    }


@app.get("/proposal/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    proposal = PENDING_PROPOSALS.get(proposal_id.upper())

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return {
        "ok": True,
        "proposal": proposal
    }


@app.post("/proposal/{proposal_id}/execute")
async def execute_proposal(
    proposal_id: str,
    command: ExecuteProposalCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    proposal_id = proposal_id.upper()
    proposal = PENDING_PROPOSALS.get(proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Proposal already {proposal['status']}")

    if proposal.get("require_confirm") and not command.confirm:
        raise HTTPException(status_code=400, detail="Execution requires confirm=true")

    results = []

    for action in proposal["actions"]:
        results.append(await execute_action(action))

    proposal["status"] = "executed"
    proposal["results"] = results

    return {
        "ok": True,
        "action": "proposal_executed",
        "proposal_id": proposal_id,
        "summary": proposal["summary"],
        "results": results
    }


@app.post("/proposal/{proposal_id}/cancel")
async def cancel_proposal(
    proposal_id: str,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)

    proposal_id = proposal_id.upper()
    proposal = PENDING_PROPOSALS.get(proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal["status"] = "cancelled"

    return {
        "ok": True,
        "action": "proposal_cancelled",
        "proposal_id": proposal_id
    }


# ============================================================
# Agent conversation layer
# Mục tiêu:
# - Nhận câu tự nhiên từ Zalo/OpenClaw
# - Tự phân loại lệnh
# - Lưu hành động chờ xác nhận
# - Khi người dùng nói "ok", tự execute hành động đang chờ
# ============================================================

import unicodedata as _unicodedata

AGENT_PENDING_BY_USER: dict[str, dict[str, Any]] = {}


class AgentCommand(BaseModel):
    text: str
    user_id: str = "zalo_an"


def _strip_accents(text: str) -> str:
    text = text.lower().strip()
    text = "".join(
        ch for ch in _unicodedata.normalize("NFD", text)
        if _unicodedata.category(ch) != "Mn"
    )
    text = text.replace("đ", "d")
    return text


def _is_confirm_text(text: str) -> bool:
    t = _strip_accents(text)
    confirm_words = [
        "ok", "oke", "dong y", "xac nhan", "co", "uh", "u", "yes",
        "thuc hien", "lam di", "chay di", "dung roi", "chap nhan"
    ]
    return t in confirm_words or any(t.startswith(w + " ") for w in confirm_words)


def _is_cancel_text(text: str) -> bool:
    t = _strip_accents(text)
    cancel_words = [
        "huy", "khong", "thoi", "bo qua", "cancel", "dung", "khong lam"
    ]
    return t in cancel_words or any(t.startswith(w + " ") for w in cancel_words)


def _device_alias_map() -> dict[str, str]:
    """
    Tạo map alias -> device_id từ devices.json.
    Có cả alias tiếng Việt có dấu và không dấu.
    """
    result = {}

    for device_id, device in DEVICES.items():
        if device.get("enabled", True) is False:
            continue

        aliases = []
        aliases.append(device_id)

        if device.get("name"):
            aliases.append(device["name"])

        for alias in device.get("aliases", []):
            aliases.append(alias)

        for alias in aliases:
            if not alias:
                continue
            result[_strip_accents(alias)] = device_id

    return result


def _find_device_from_text(text: str) -> Optional[str]:
    t = _strip_accents(text)
    alias_map = _device_alias_map()

    # Ưu tiên alias dài trước để tránh nhầm "đèn" chung chung
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if alias and alias in t:
            return alias_map[alias]

    return None


def _parse_light_action(text: str) -> Optional[dict[str, Any]]:
    """
    Parse lệnh kiểu:
    - bật đèn h
    - tắt led dây
    - bật đèn trần
    - dim đèn trần 70%
    """
    t = _strip_accents(text)

    device_id = _find_device_from_text(text)

    # Nếu có chữ đèn trần/ánh sáng ngoài trời mà chưa match thì ép về g1_den_tran
    if device_id is None:
        if "den tran" in t or "anh sang ngoai troi" in t or "g1" in t:
            device_id = "g1_den_tran"

    if device_id is None:
        return None

    # Dim / brightness
    if "dim" in t or "do sang" in t or "%" in t:
        m = re.search(r"(\d{1,3})\s*%?", t)
        if not m:
            return None

        value = int(m.group(1))
        value = max(0, min(100, value))

        return {
            "device": device_id,
            "action": "brightness",
            "value": value,
            "reason": f"Người dùng yêu cầu chỉnh độ sáng {value}%"
        }

    if "bat" in t or "mo" in t:
        return {
            "device": device_id,
            "action": "on",
            "reason": "Người dùng yêu cầu bật thiết bị"
        }

    if "tat" in t or "dong" in t:
        return {
            "device": device_id,
            "action": "off",
            "reason": "Người dùng yêu cầu tắt thiết bị"
        }

    return None


def _parse_all_off(text: str) -> bool:
    t = _strip_accents(text)

    # Nếu có chữ bật/mở thì chắc chắn không phải là lệnh tắt
    if "bat" in t or "mo" in t:
        return False

    # Các cụm từ liên quan đến mô phỏng
    if any(p in t for p in ["reset mo hinh", "tat che do mo phong", "dung mo phong", "tat mo phong"]):
        return True

    # Kiểm tra ý định tắt toàn bộ (bao gồm cả trường hợp gõ sai dấu hoặc thêm chữ "các")
    if "tat" in t:
        if any(k in t for k in ["het", "toan bo", "tat ca", "ta ca", "tat tan tat"]):
            return True

    return False


def _parse_environment(text: str) -> Optional[EnvironmentProposalCommand]:
    """
    Parse lệnh môi trường đơn giản:
    - mô phỏng trời nóng 34 độ không mưa
    - trời tối
    - trời rất sáng
    - nắng gắt
    - có mưa
    """
    t = _strip_accents(text)

    env_keywords = [
        "mo phong", "thoi tiet", "troi", "nong", "mat", "mua",
        "nang", "toi", "sang", "nhiet do", "toi uu", "moi truong"
    ]

    if not any(k in t for k in env_keywords):
        return None

    sun_percent = None
    outside_temp = None
    rain_expected = None

    # Nhiệt độ: 34 độ, 34 do, 34°C
    m = re.search(r"(\d{2}(?:\.\d+)?)\s*(do|°c|c)", t)
    if m:
        outside_temp = float(m.group(1))

    # Mưa
    if "khong mua" in t or "ko mua" in t or "khong co mua" in t:
        rain_expected = False
    elif "co mua" in t or "troi mua" in t or "mua" in t:
        rain_expected = True

    # Ánh sáng
    if "nang gat" in t or "rat sang" in t or "sang manh" in t:
        sun_percent = 90
    elif "du sang" in t or "troi sang" in t:
        sun_percent = 70
    elif "hoi toi" in t or "anh sang yeu" in t:
        sun_percent = 30
    elif "troi toi" in t or t == "toi" or "toi roi" in t:
        sun_percent = 10

    # Nếu nói trời nóng nhưng không nói nắng, mặc định có ánh sáng mạnh vừa phải
    if outside_temp is not None and outside_temp >= 32 and sun_percent is None:
        sun_percent = 85

    if sun_percent is None and outside_temp is None and rain_expected is None:
        return None

    return EnvironmentProposalCommand(
        sun_percent=sun_percent,
        outside_temp=outside_temp,
        rain_expected=rain_expected,
        note="parsed by /agent/command"
    )


def _parse_status_query(text: str) -> Optional[dict[str, Any]]:
    """
    Parse lệnh hỏi trạng thái:
    - trạng thái các đèn
    - kiểm tra thiết bị
    - đèn trần đang bật hay tắt
    """
    t = _strip_accents(text)
    
    status_keywords = ["trang thai", "dang bat hay tat", "kiem tra", "dang tat hay bat", "con bat khong"]
    has_status_intent = any(k in t for k in status_keywords)
    
    if not has_status_intent:
        return None
        
    all_keywords = ["tat ca", "trong nha", "cac den", "toan bo", "het"]
    if any(k in t for k in all_keywords):
        return {"type": "all"}
        
    device_id = _find_device_from_text(text)
    if device_id:
        return {"type": "single", "device": device_id}
        
    # Default to all if no specific device matched but asked for status generally
    return {"type": "all"}


def _make_pending(user_id: str, pending_type: str, summary: str, actions: list[dict[str, Any]]):
    pending_id = secrets.token_hex(3).upper()

    pending = {
        "pending_id": pending_id,
        "user_id": user_id,
        "type": pending_type,
        "summary": summary,
        "actions": actions,
        "status": "pending"
    }

    AGENT_PENDING_BY_USER[user_id] = pending
    return pending


async def _execute_pending(pending: dict[str, Any]):
    results = []

    if pending["type"] == "all_off":
        for device_id, device in DEVICES.items():
            if device.get("enabled", True) and device.get("type") == "light" and device.get("onoff_ga"):
                result = await execute_action({
                    "device": device_id,
                    "action": "off",
                    "reason": "Xác nhận tắt toàn bộ từ agent"
                })
                results.append(result)

    elif pending["type"] in ["light_action", "environment", "all_on"]:
        for action in pending["actions"]:
            result = await execute_action(action)
            results.append(result)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported pending type: {pending['type']}")

    pending["status"] = "executed"
    pending["results"] = results
    return results

def _doc_knx_parse_extracted_text(text: str) -> list[dict[str, Any]]:
    """
    Parse đơn giản nội dung extracted_text để tạo proposed_devices nháp.
    Không đoán group address, chỉ dùng thông tin có trong tài liệu.
    """
    blocks = re.split(r"\n\s*\n", text.strip())
    devices = []

    current_room = None

    for block in blocks:
        raw = block.strip()
        if not raw:
            continue

        raw_lines = [line.strip() for line in raw.splitlines() if line.strip()]
        raw_lower = raw.lower()
        raw_norm = _strip_accents(raw)

        for line in raw_lines:
            if line.endswith(":") and not re.search(r"\d+/\d+/\d+", line):
                current_room = line.rstrip(":").strip()

        ga_match = re.search(r"\b\d{1,2}/\d{1,2}/\d{1,3}\b", raw)
        dpt_match = re.search(r"\b(?:DPT\s*:\s*|DPT\s*)?(\d{1,3}\.\d{1,3})\b", raw, flags=re.IGNORECASE)

        if not ga_match and not dpt_match:
            continue

        group_address = ga_match.group(0) if ga_match else None
        dpt = dpt_match.group(1) if dpt_match else None

        name_line = raw_lines[0] if raw_lines else "Thiết bị chưa rõ tên"
        if name_line.endswith(":") and len(raw_lines) > 1:
            name_line = raw_lines[1]

        if "den" in raw_norm or "light" in raw_norm:
            device_type = "light"
        elif "rem" in raw_norm or "curtain" in raw_norm or "blind" in raw_norm:
            device_type = "curtain"
        elif "dieu hoa" in raw_norm or "ac" in raw_norm or "hvac" in raw_norm:
            device_type = "ac"
        elif "cam bien" in raw_norm or "sensor" in raw_norm:
            device_type = "sensor"
        else:
            device_type = "other"

        if "trang thai" in raw_norm or "status" in raw_norm:
            direction = "status"
        elif "doc" in raw_norm or "read" in raw_norm:
            direction = "read"
        else:
            direction = "write"

        status = "ready" if group_address and dpt else "missing_info"

        devices.append({
            "name": name_line,
            "type": device_type,
            "room": current_room,
            "functions": [
                {
                    "function": "status" if direction == "status" else "control",
                    "group_address": group_address,
                    "dpt": dpt,
                    "direction": direction
                }
            ],
            "status": status,
            "notes": "Tạo từ doc_knx parser. Chưa cập nhật devices.json."
        })

    return devices


def _doc_knx_handle_latest() -> dict[str, Any]:
    """
    Đọc proposal mới nhất trong knowledge/review,
    đọc extracted_text bên trong proposal,
    tạo proposed_devices nháp và lưu lại proposal.
    """
    from pathlib import Path
    import json

    review_dir = Path.home() / ".openclaw" / "workspace" / "knowledge" / "review"
    proposals = sorted(review_dir.glob("device_proposal_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not proposals:
        return {
            "ok": True,
            "executed": False,
            "need_confirm": False,
            "message": "Chưa tìm thấy proposal nào trong knowledge/review."
        }

    proposal_path = proposals[0]

    try:
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "ok": False,
            "executed": False,
            "need_confirm": False,
            "message": f"Không đọc được proposal mới nhất: {e}"
        }

    extracted_path_text = proposal.get("source", {}).get("extracted_text")

    if not extracted_path_text:
        return {
            "ok": True,
            "executed": False,
            "need_confirm": False,
            "message": f"Proposal {proposal_path.name} không có source.extracted_text."
        }

    extracted_path = Path(extracted_path_text)

    if not extracted_path.exists():
        return {
            "ok": True,
            "executed": False,
            "need_confirm": False,
            "message": f"Không tìm thấy extracted_text: {extracted_path}"
        }

    extracted_text = extracted_path.read_text(encoding="utf-8", errors="ignore")
    proposed_devices = _doc_knx_parse_extracted_text(extracted_text)

    proposal["status"] = "ai_reviewed"
    proposal["proposed_devices"] = proposed_devices
    proposal["doc_knx_reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")

    ready_count = sum(1 for d in proposed_devices if d.get("status") == "ready")
    missing_count = sum(1 for d in proposed_devices if d.get("status") == "missing_info")

    lines = []
    lines.append("Tôi đã đọc proposal mới nhất và file extracted_text.")
    lines.append("")
    lines.append(f"Proposal: {proposal_path.name}")
    lines.append(f"Tìm thấy {len(proposed_devices)} mục thiết bị/chức năng.")
    lines.append(f"- ready: {ready_count}")
    lines.append(f"- missing_info: {missing_count}")
    lines.append("")
    lines.append("Danh sách tìm được:")

    for i, dev in enumerate(proposed_devices, start=1):
        fn = dev.get("functions", [{}])[0]
        lines.append(
            f"{i}. {dev.get('name')} | type={dev.get('type')} | room={dev.get('room')} | "
            f"GA={fn.get('group_address')} | DPT={fn.get('dpt')} | direction={fn.get('direction')} | status={dev.get('status')}"
        )

    lines.append("")
    lines.append("Chưa cập nhật devices.json. Muốn ghi vào cấu hình phải xác nhận riêng.")

    return {
        "ok": True,
        "executed": False,
        "need_confirm": False,
        "message": "\n".join(lines),
        "proposal": str(proposal_path),
        "proposed_devices_count": len(proposed_devices)
    }

@app.post("/agent/command")
async def agent_command(
    command: AgentCommand,
    x_knx_token: Optional[str] = Header(default=None)
):
    """
    Endpoint chính cho bot Zalo/OpenClaw.

    Bot gửi mọi câu KNX vào đây:
    {
      "user_id": "zalo_an",
      "text": "bật đèn H"
    }

    Luồng xử lý:
    0. doc_knx: đọc proposal tài liệu KNX, không điều khiển thiết bị thật.
    1. Nếu có pending: ok thì execute, hủy thì cancel.
    2. Nếu không có pending mà user chỉ nói ok: báo không có gì chờ.
    3. Tắt toàn bộ đèn: tạo pending.
    4. Bật/tắt/dim một thiết bị safe_demo: chạy ngay nếu an toàn.
    5. Lệnh môi trường/mô phỏng: tạo pending.
    6. Không hiểu lệnh: trả hướng dẫn.
    """
    check_auth(x_knx_token)

    user_id = command.user_id or "zalo_an"
    text = command.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Missing text")

    normalized_text = _strip_accents(text)

    # 0. Lệnh đọc proposal tài liệu KNX.
    # Lệnh này KHÔNG điều khiển thiết bị thật và KHÔNG cập nhật devices.json.
    # Dùng trên Zalo:
    # doc_knx đọc proposal mới nhất
    if normalized_text.startswith("doc_knx"):
        return _doc_knx_handle_latest()

    # 0.1 Lệnh hỏi trạng thái
    status_query = _parse_status_query(text)
    if status_query:
        if status_query["type"] == "single":
            device = get_device(status_query["device"])
            if not device.get("status_ga"):
                return {
                    "ok": True,
                    "executed": True,
                    "need_confirm": False,
                    "message": f"Thiết bị {device['name']} chưa được cấu hình địa chỉ đọc trạng thái (status_ga)."
                }
            
            val = await read_knx_status(device["status_ga"], value_type="switch")
            is_on = getattr(val, "value", None) == 1 or str(val) == "Switch.ON"
            state_str = "đang BẬT" if is_on else "đang TẮT" if val is not None else "không rõ trạng thái"
            
            msg = f"Thiết bị {device['name']} {state_str}."
            if device.get("supports_brightness") and device.get("brightness_status_ga"):
                bright_val = await read_knx_status(device["brightness_status_ga"], value_type="percent")
                if bright_val is not None:
                    msg += f" Độ sáng hiện tại: {bright_val}%."
            
            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": msg
            }
        
        elif status_query["type"] == "all":
            valid_devices = []
            for dev_id, dev in DEVICES.items():
                if dev.get("enabled", True) and dev.get("status_ga"):
                    valid_devices.append(dev)
            
            if not valid_devices:
                return {
                    "ok": True,
                    "executed": True,
                    "need_confirm": False,
                    "message": "Không có thiết bị nào hỗ trợ đọc trạng thái (chưa được cấu hình status_ga)."
                }
                
            results = []
            for dev in valid_devices:
                try:
                    val = await read_knx_status(dev["status_ga"], value_type="switch")
                    results.append(val)
                except Exception as e:
                    results.append(e)
                await asyncio.sleep(0.15)  # Tránh nghẽn mạng KNX (Bus Congestion)
            
            lines = []
            for dev, val in zip(valid_devices, results):
                if isinstance(val, Exception) or val is None:
                    state_str = "Không rõ"
                else:
                    is_on = getattr(val, "value", None) == 1 or str(val) == "Switch.ON"
                    state_str = "BẬT" if is_on else "TẮT"
                lines.append(f"- {dev['name']}: {state_str}")
            
            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": "Trạng thái các thiết bị:\n" + "\n".join(lines)
            }

    # 1. Nếu đang có hành động chờ xác nhận
    pending = AGENT_PENDING_BY_USER.get(user_id)

    if pending and pending.get("status") == "pending":
        if _is_confirm_text(text):
            results = await _execute_pending(pending)
            AGENT_PENDING_BY_USER.pop(user_id, None)

            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": f"Đã thực hiện: {pending['summary']}",
                "pending": pending,
                "results": results
            }

        if _is_cancel_text(text):
            pending["status"] = "cancelled"
            AGENT_PENDING_BY_USER.pop(user_id, None)

            return {
                "ok": True,
                "executed": False,
                "need_confirm": False,
                "message": "Đã hủy hành động đang chờ xác nhận.",
                "pending": pending
            }

        return {
            "ok": True,
            "executed": False,
            "need_confirm": True,
            "message": f"Đang có hành động chờ xác nhận: {pending['summary']}. Trả lời 'ok' để thực hiện hoặc 'hủy' để bỏ qua.",
            "pending": pending
        }

    # 2. Không có pending mà người dùng chỉ nói ok
    if _is_confirm_text(text):
        return {
            "ok": True,
            "executed": False,
            "need_confirm": False,
            "message": "Hiện không có hành động nào đang chờ xác nhận."
        }

    # 3. Lệnh tắt toàn bộ
    if _parse_all_off(text):
        actions = []

        for device_id, device in DEVICES.items():
            if device.get("enabled", True) and device.get("type") == "light" and device.get("onoff_ga"):
                actions.append({
                    "device": device_id,
                    "action": "off",
                    "reason": "Tắt toàn bộ đèn mô phỏng"
                })

        pending = _make_pending(
            user_id=user_id,
            pending_type="all_off",
            summary="Tắt toàn bộ đèn mô phỏng",
            actions=actions
        )

        return {
            "ok": True,
            "executed": False,
            "need_confirm": True,
            "message": "Lệnh này sẽ tắt toàn bộ đèn. Bạn có xác nhận không?",
            "pending": pending
        }

    # 3.1 Lệnh bật toàn bộ (chỉ bật đèn thật, không bật đèn mô phỏng)
    t_norm = _strip_accents(text)
    import re
    if "bat" in t_norm and bool(re.search(r"\b(het|toan bo|tat ca|ta ca|tat tan tat)\b", t_norm)):
        actions = []

        for device_id, device in DEVICES.items():
            # Bật toàn bộ tất cả đèn (cả đèn thật và đèn test)
            if device.get("enabled", True) and device.get("type") == "light" and device.get("onoff_ga"):
                actions.append({
                    "device": device_id,
                    "action": "on",
                    "reason": "Bật toàn bộ hệ thống đèn"
                })

        if actions:
            pending = _make_pending(
                user_id=user_id,
                pending_type="all_on",
                summary="Bật toàn bộ hệ thống đèn",
                actions=actions
            )

            return {
                "ok": True,
                "executed": False,
                "need_confirm": True,
                "message": "Lệnh này sẽ bật toàn bộ hệ thống đèn (bao gồm cả đèn test). Bạn có xác nhận không?",
                "pending": pending
            }

    # 4. Lệnh bật/tắt/dim một thiết bị
    # Thiết bị safe_demo thì thực hiện ngay nếu không require_confirm.
    light_action = _parse_light_action(text)

    if light_action:
        validate_action(ActionItem(**light_action))

        device = get_device(light_action["device"])
        action_name = light_action["action"]

        is_safe_demo = device.get("safety_level", "safe_demo") == "safe_demo"
        require_confirm = bool(device.get("require_confirm", False))

        if is_safe_demo and not require_confirm:
            result = await execute_action(light_action)

            if action_name == "brightness":
                message = f"Đã chỉnh {device['name']} tới {light_action['value']}%."
            elif action_name == "on":
                message = f"Đã bật {device['name']}."
            else:
                message = f"Đã tắt {device['name']}."

            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": message,
                "result": result
            }

        # Thiết bị không thuộc safe_demo hoặc require_confirm=true thì hỏi xác nhận.
        if action_name == "brightness":
            summary = f"Chỉnh {device['name']} tới {light_action['value']}%"
            message = f"Tôi sẽ chỉnh {device['name']} tới {light_action['value']}%. Bạn xác nhận không?"
        elif action_name == "on":
            summary = f"Bật {device['name']}"
            message = f"Tôi sẽ bật {device['name']}. Bạn xác nhận không?"
        else:
            summary = f"Tắt {device['name']}"
            message = f"Tôi sẽ tắt {device['name']}. Bạn xác nhận không?"

        pending = _make_pending(
            user_id=user_id,
            pending_type="light_action",
            summary=summary,
            actions=[light_action]
        )

        return {
            "ok": True,
            "executed": False,
            "need_confirm": True,
            "message": message,
            "pending": pending
        }

    # 5. Lệnh môi trường / mô phỏng
    env = _parse_environment(text)

    if env:
        summary, actions = build_environment_actions(env)

        for action in actions:
            validate_action(ActionItem(**action))

        pending = _make_pending(
            user_id=user_id,
            pending_type="environment",
            summary=summary,
            actions=actions
        )

        action_lines = []
        for a in actions:
            dev = get_device(a["device"])

            if a["action"] == "brightness":
                action_lines.append(f"- {dev['name']}: dim {a.get('value')}%")
            elif a["action"] == "on":
                action_lines.append(f"- {dev['name']}: bật")
            elif a["action"] == "off":
                action_lines.append(f"- {dev['name']}: tắt")

        return {
            "ok": True,
            "executed": False,
            "need_confirm": True,
            "message": "Tôi đã lập phương án điều khiển theo ngữ cảnh. Bạn có muốn thực hiện không?",
            "summary": summary,
            "plan": action_lines,
            "pending": pending
        }

    # 5.5. Lệnh tóm tắt / kiểm tra lịch sử chat (Zalo History Skill)
    if any(kw in normalized_text for kw in ["tom tat", "ai nhan", "lich su", "co gi hot"]):
        import sqlite3
        import os
        db_path = str(DB_FILE)
        if not os.path.exists(db_path):
            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": "Hiện chưa có dữ liệu lịch sử chat nào được ghi nhận."
            }
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT sender_name, text FROM messages ORDER BY timestamp DESC LIMIT 20')
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return {
                    "ok": True,
                    "executed": True,
                    "need_confirm": False,
                    "message": "Không có tin nhắn nào trong lịch sử gần đây."
                }
            
            lines = []
            for row in reversed(rows):
                name = row[0] or "Unknown"
                msg_text = row[1] or ""
                lines.append(f"- {name}: {msg_text}")
                
            summary = "Dưới đây là các tin nhắn gần nhất trong Group:\n" + "\n".join(lines)
            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": summary
            }
        except Exception as e:
            return {
                "ok": True,
                "executed": True,
                "need_confirm": False,
                "message": f"Lỗi khi đọc lịch sử: {e}"
            }

    # 6. Không hiểu lệnh
    return {
        "ok": False,
        "executed": False,
        "need_confirm": False,
        "message": "Tôi chưa xác định được lệnh KNX cần thực hiện. Bạn hãy nói rõ thiết bị hoặc ngữ cảnh, ví dụ: 'bật đèn H', 'tắt hết đèn', 'mô phỏng trời nóng 34 độ không mưa', 'doc_knx đọc proposal mới nhất', hoặc 'tóm tắt lịch sử group'."
    }

# ===== DALI COLOR TEMPERATURE EXTENSION =====
# Added for G1 DALI ceiling light colour temperature control.
# ETS confirmed:
# 0/1/4 = Absolute colour temperature - Setting
# 0/1/5 = Colour temperature - Status

from pathlib import Path as _CTPath
import json as _ct_json
import os as _ct_os
import inspect as _ct_inspect
from fastapi import Header as _CTHeader, HTTPException as _CTHTTPException, Depends as _CTDepends
from pydantic import BaseModel as _CTBaseModel


class _ColorTemperatureRequest(_CTBaseModel):
    device: str
    value: int


def _ct_get_token():
    token = _ct_os.getenv("KNX_API_TOKEN", "")
    if token:
        return token

    env_path = _CTPath(__file__).with_name(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("KNX_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


async def _ct_require_token(x_knx_token: str = _CTHeader(default="")):
    expected = _ct_get_token()
    if expected and x_knx_token != expected:
        raise _CTHTTPException(status_code=401, detail="Invalid KNX token")
    return True


def _ct_load_devices():
    p = _CTPath(__file__).with_name("devices.json")
    return _ct_json.loads(p.read_text(encoding="utf-8"))


async def _ct_write_knx(group_address: str, value: int):
    fn = globals().get("write_knx")
    if fn is None:
        raise _CTHTTPException(status_code=500, detail="write_knx function not found")

    # Prefer keyword signature used by current bridge.
    try:
        return await fn(group_address, value, value_type="2byte_unsigned")
    except TypeError:
        # Fallback for positional signature.
        try:
            return await fn(group_address, value, "2byte_unsigned")
        except TypeError:
            raise _CTHTTPException(
                status_code=500,
                detail="write_knx signature does not support DPT 2-byte unsigned"
            )


@app.post("/light/color-temperature")
async def set_light_color_temperature(
    body: _ColorTemperatureRequest,
    _auth: bool = _CTDepends(_ct_require_token)
, current_user: dict = Depends(auth_utils.get_current_user)):
    devices = _ct_load_devices()

    if body.device not in devices:
        raise _CTHTTPException(status_code=404, detail=f"Unknown device: {body.device}")

    dev = devices[body.device]

    if not dev.get("supports_color_temperature"):
        raise _CTHTTPException(
            status_code=400,
            detail=f"Device {body.device} does not support color temperature"
        )

    kelvin = int(body.value)
    min_k = int(dev.get("color_temp_min", 1000))
    max_k = int(dev.get("color_temp_max", 10000))

    if kelvin < min_k or kelvin > max_k:
        raise _CTHTTPException(
            status_code=400,
            detail=f"Color temperature out of range: {kelvin}K. Allowed: {min_k}-{max_k}K"
        )

    ga = dev.get("color_temp_ga")
    if not ga:
        raise _CTHTTPException(status_code=400, detail="Missing color_temp_ga")

    await _ct_write_knx(ga, kelvin)

    return {
        "ok": True,
        "executed": True,
        "device": body.device,
        "action": "color_temperature",
        "value": kelvin,
        "unit": "K",
        "group_address": ga,
        "dpt": dev.get("color_temp_dpt", "7.600")
    }

# ===== END DALI COLOR TEMPERATURE EXTENSION =====


@app.post("/schedule")
async def create_schedule(
    command: ScheduleCommand,
    x_knx_token: Optional[str] = Header(default=None)
, current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)
    
    validate_action(ActionItem(device=command.device, action=command.action, value=command.value))
    
    task_id = secrets.token_hex(4).upper()
    run_at = datetime.now() + timedelta(seconds=command.delay_seconds)
    
    SCHEDULED_TASKS[task_id] = {
        "task_id": task_id,
        "device": command.device,
        "action": command.action,
        "value": command.value,
        "run_at": run_at.isoformat(),
        "reason": command.reason
    }
    
    asyncio.create_task(scheduled_action_runner(task_id, command, run_at))
    
    return {
        "ok": True,
        "action": "schedule_created",
        "task_id": task_id,
        "run_at": run_at.isoformat(),
        "schedule": SCHEDULED_TASKS[task_id]
    }


@app.get("/schedule")
async def list_schedules(x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)
    return {"ok": True, "schedules": list(SCHEDULED_TASKS.values())}


@app.delete("/schedule/{task_id}")
async def cancel_schedule(task_id: str, x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.get_current_user)):
    check_auth(x_knx_token)
    
    task_id = task_id.upper()
    if task_id in SCHEDULED_TASKS:
        del SCHEDULED_TASKS[task_id]
        return {"ok": True, "action": "schedule_cancelled", "task_id": task_id}
    else:
        raise HTTPException(status_code=404, detail="Schedule task not found")


# DOC_UPLOAD_ENDPOINT_START
from fastapi import UploadFile, File as _FastApiFile
from fastapi.responses import HTMLResponse as _HTMLResponse
from pathlib import Path as _DocPath
import subprocess as _doc_subprocess
import time as _doc_time
import re as _doc_re
import html as _doc_html

_DOC_UPLOAD_DIR = _DocPath("/home/an/.openclaw/workspace/knowledge/inbox/uploads")
_DOC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/doc-upload", response_class=_HTMLResponse)
async def doc_upload_page():
    return _HTMLResponse("""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>KNX Document Upload</title>
</head>
<body style="font-family:Arial;max-width:760px;margin:40px auto;">
<h2>Upload tài liệu KNX</h2>
<form action="/doc-upload" method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept=".xlsx,.xls,.csv,.pdf,.docx,.doc,.txt,.md,.html,.htm,.log" required>
  <button type="submit">Đọc file</button>
</form>
<p>Hỗ trợ: Excel, CSV, PDF, Word, TXT.</p>
<p>Sau khi đọc xong hệ thống chỉ tạo proposal, chưa ghi devices.json.</p>
</body>
</html>
""")

@app.post("/doc-upload", response_class=_HTMLResponse)
async def doc_upload_submit(file: UploadFile = _FastApiFile(...)):
    filename = file.filename or "uploaded_file"
    safe_name = _doc_re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._") or "uploaded_file"

    allowed = (".xlsx", ".xls", ".csv", ".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".htm", ".log")
    if not safe_name.lower().endswith(allowed):
        return _HTMLResponse("<pre>Không hỗ trợ loại file này.</pre>", status_code=400)

    data = await file.read()
    if len(data) > 30 * 1024 * 1024:
        return _HTMLResponse("<pre>File quá lớn. Giới hạn 30MB.</pre>", status_code=400)

    dst = _DOC_UPLOAD_DIR / (str(int(_doc_time.time())) + "_" + safe_name)
    dst.write_bytes(data)

    cmd = [
        "/home/an/knx-bridge/.venv/bin/python",
        "/home/an/knx-bridge/tools/document_to_knx_skill.py",
        str(dst)
    ]

    try:
        r = _doc_subprocess.run(
            cmd,
            cwd="/home/an/knx-bridge",
            text=True,
            capture_output=True,
            timeout=180
        )
    except Exception as e:
        return _HTMLResponse("<pre>Lỗi chạy tool:\n" + _doc_html.escape(str(e)) + "</pre>", status_code=500)

    output = "FILE: " + str(dst) + "\n\n"
    output += "STDOUT:\n" + r.stdout + "\n"
    output += "STDERR:\n" + r.stderr + "\n"

    if r.returncode != 0:
        return _HTMLResponse("<pre>" + _doc_html.escape(output) + "</pre>", status_code=500)

    try:
        review = _doc_knx_handle_latest()
        msg = review.get("message", str(review)) if isinstance(review, dict) else str(review)
        output += "\n\nDOC_KNX REVIEW:\n" + msg
    except Exception as e:
        output += "\n\nTạo proposal OK nhưng doc_knx lỗi:\n" + str(e)

    return _HTMLResponse("<pre>" + _doc_html.escape(output) + "</pre>")
# DOC_UPLOAD_ENDPOINT_END

import os as _voice_os
import tempfile as _voice_tempfile
import speech_recognition as _voice_sr
import httpx as _voice_httpx
import imageio_ffmpeg as _imageio_ffmpeg
import subprocess as _subprocess

class VoiceRequest(BaseModel):
    user_id: str
    voice_url: str

@app.post("/agent/voice")
async def handle_voice(request: VoiceRequest):
    """
    Endpoint nhận file âm thanh từ Zalo (đã được patch OpenClaw để forward),
    dịch thành văn bản (Speech-to-Text) và chuyển tiếp tới agent_command.
    """
    try:
        # Download audio file
        async with _voice_httpx.AsyncClient() as client:
            resp = await client.get(request.voice_url)
            resp.raise_for_status()
            audio_data = resp.content

        groq_api_key = _voice_os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            return {"message": "Voice: Lỗi cấu hình GROQ_API_KEY bị thiếu trên hệ thống."}

        with _voice_tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_in:
            tmp_in.write(audio_data)
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path + ".wav"

        try:
            # Convert to wav using direct ffmpeg call since Zalo gives raw .aac which Groq might reject
            _subprocess.run([
                _imageio_ffmpeg.get_ffmpeg_exe(),
                "-y", "-i", tmp_in_path,
                "-ar", "16000", "-ac", "1",
                tmp_out_path
            ], check=True, stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)

            with open(tmp_out_path, "rb") as f_wav:
                wav_data = f_wav.read()

            async with _voice_httpx.AsyncClient() as client:
                files = {'file': ('audio.wav', wav_data, 'audio/wav')}
                data = {
                    'model': 'whisper-large-v3-turbo',
                    'language': 'vi'
                }
                headers = {
                    'Authorization': f'Bearer {groq_api_key}'
                }
                resp = await client.post(
                    'https://api.groq.com/openai/v1/audio/transcriptions',
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=30.0
                )
                if resp.status_code != 200:
                    return {"message": f"Voice: Lỗi Groq API {resp.status_code} - {resp.text}"}
                resp.raise_for_status()
                result = resp.json()
                text = result.get('text', '')
        finally:
            if _voice_os.path.exists(tmp_in_path):
                _voice_os.remove(tmp_in_path)
            if _voice_os.path.exists(tmp_out_path):
                _voice_os.remove(tmp_out_path)

        if not text:
            return {"message": "Voice: Không nghe rõ giọng nói."}

        # Bộ lọc sửa lỗi phát âm/nhận diện sai cơ bản (để bù đắp cho việc không có AI LLM)
        original_text = text
        text = text.lower()
        corrections = {
            "bạch": "bật", "bậc": "bật", "bặt": "bật", "mở": "bật", "vật": "bật",
            "tắc": "tắt", "cắt": "tắt", "bắc": "tắt",
            "sim": "scene", "xin": "scene", "sin": "scene", "sen": "scene", "xim": "scene", "chim": "scene"
        }
        words = text.split()
        for i, w in enumerate(words):
            if w in corrections:
                words[i] = corrections[w]
        corrected_text = " ".join(words)

        # Trả về kết quả text thô để OpenClaw dùng Groq Llama-3 suy luận (Agent Mức 3)
        return {
            "message": "Voice OK",
            "transcribed_text": corrected_text,
            "original_text": original_text
        }

    except _voice_sr.UnknownValueError:
        return {"message": "Voice: Không thể nhận diện được giọng nói."}
    except _voice_sr.RequestError as e:
        return {"message": f"Voice: Lỗi dịch vụ Google Speech: {e}"}
    except Exception as e:
        import traceback
        return {"message": f"Lỗi xử lý Voice: {e}\n{traceback.format_exc()}"}

@app.post("/zalo_group_log")
async def handle_zalo_group_log(request: ZaloGroupLogCommand):
    try:
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (group_id, group_name, sender_id, sender_name, text, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            request.group_id,
            request.group_name,
            request.sender_id,
            request.sender_name,
            request.text,
            request.timestamp
        ))
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        print(f"Error saving group log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat-logs")
async def get_chat_logs(limit: int = 100):
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, group_id, group_name, sender_id, sender_name, text, timestamp 
            FROM messages 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard")
async def get_dashboard():
    dashboard_path = BASE_DIR / "chat_dashboard.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not found")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/api/ai/context")
async def get_ai_context():
    """
    Endpoint dành riêng cho OpenClaw để kéo (pull) ngữ cảnh ngôi nhà 
    (trạng thái thiết bị, lịch sử sự kiện) trước khi trả lời.
    """
    if not _context_builder:
        return {"error": "Context Builder not initialized"}
    
    import json
    # build_context() returns a json string, so we load it to return as JSON response
    return json.loads(_context_builder.build_context())

@app.post("/api/ask-ai")
async def ask_ai(request: AskAICommand):
    try:
        # AI will automatically pull context via /api/ai/context endpoint 
        # using the rule defined in IDENTITY.md
        
        # Pass the message to openclaw CLI to use the agent
        cmd = [
            "openclaw", "agent", 
            "--session-key", "agent:main:dashboard_v2", 
            "--message", request.text, 
            "--json"
        ]
        
        # Run process synchronously since openclaw handles its own timeouts
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            return {"reply": f"Lỗi AI: {result.stderr}"}
            
        try:
            # Parse OpenClaw output
            data = json.loads(result.stdout)
            reply = data.get("result", {}).get("meta", {}).get("finalAssistantVisibleText", "AI không trả lời được.")
            return {"reply": reply}
        except json.JSONDecodeError:
            return {"reply": f"Lỗi định dạng AI: {result.stdout}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SqlQueryCommand(BaseModel):
    query: str

@app.get("/api/database/tables")
async def get_tables(x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)
    db_path = BASE_DIR / "smarthome.db"
    if not db_path.exists():
        return {"tables": []}
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        result = []
        for table in tables:
            cursor.execute(f"SELECT count(*) FROM {table}")
            count = cursor.fetchone()[0]
            result.append({"name": table, "rows": count})
            
        conn.close()
        return {"tables": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/database/snapshot")
async def create_snapshot(current_user: dict = Depends(auth_utils.require_admin)):
    import shutil
    db_path = BASE_DIR / "smarthome.db"
    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_filename = f"smarthome.db.bak_{timestamp}"
    snapshot_path = backup_dir / snapshot_filename
    
    try:
        shutil.copy2(db_path, snapshot_path)
        return {"ok": True, "snapshot": snapshot_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")

@app.post("/api/database/query")
async def execute_query(command: SqlQueryCommand, x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)
    db_path = BASE_DIR / "smarthome.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(command.query)
        
        if command.query.strip().upper().startswith("SELECT") or command.query.strip().upper().startswith("PRAGMA"):
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            data = [dict(row) for row in rows]
            conn.close()
            return {"columns": columns, "data": data}
        else:
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return {"affected_rows": affected, "message": "Query executed successfully."}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class RestartCommand(BaseModel):
    service: str

@app.post("/api/system/restart")
async def restart_service(command: RestartCommand, x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)
    if command.service not in ["knx-bridge", "knx-frontend", "ngrok", "openclaw"]:
        raise HTTPException(status_code=400, detail="Invalid service name")
        
    try:
        # Since we are running under systemd user mode
        cmd = ["systemctl", "--user", "restart", command.service]
        subprocess.Popen(cmd) # run asynchronously to not block response
        return {"ok": True, "message": f"Restarting {command.service}..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/config")
async def get_config(current_user: dict = Depends(auth_utils.require_admin)):
    env_path = BASE_DIR / ".env"
    configs = []
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    configs.append({"key": key.strip(), "value": val.strip().strip("'").strip('"')})
    return {"configs": configs}

@app.post("/api/system/config")
async def update_config(payload: dict, current_user: dict = Depends(auth_utils.require_admin)):
    env_path = BASE_DIR / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()
            
    updated = False
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in payload:
                lines[i] = f"{key}={payload[key]}\n"
                updated = True
                del payload[key]
                
    # Add remaining new keys
    for key, val in payload.items():
        if key != "x_knx_token":
            lines.append(f"{key}={val}\n")
            updated = True
            
    with open(env_path, "w") as f:
        f.writelines(lines)
        
    # Reload environment variables into python process
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    return {"ok": True, "message": "Configuration updated successfully"}

from fastapi.responses import FileResponse
import zipfile

@app.get("/api/system/backup")
async def system_backup(x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.require_admin)):
    # check_auth(x_knx_token) # Disable auth for direct download for now
    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = backup_dir / f"knx_backup_{timestamp}.zip"
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if (BASE_DIR / "smarthome.db").exists():
                zipf.write(BASE_DIR / "smarthome.db", "smarthome.db")
            if (BASE_DIR / "devices.json").exists():
                zipf.write(BASE_DIR / "devices.json", "devices.json")
            if (BASE_DIR / ".env").exists():
                zipf.write(BASE_DIR / ".env", ".env")
        
        return FileResponse(
            path=zip_filename, 
            filename=f"knx_backup_{timestamp}.zip",
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File
import shutil

@app.post("/api/system/restore")
async def system_restore(
    file: UploadFile = File(...),
    current_user: dict = Depends(auth_utils.require_admin)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    upload_path = BASE_DIR / "temp_restore.zip"
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract specific files
        with zipfile.ZipFile(upload_path, "r") as zf:
            files_in_zip = zf.namelist()
            if "smarthome.db" in files_in_zip:
                zf.extract("smarthome.db", path=BASE_DIR)
            if ".env" in files_in_zip:
                zf.extract(".env", path=BASE_DIR)

        upload_path.unlink()

        # Reload environment variables
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Schedule a restart after a short delay
        subprocess.Popen(["bash", "-c", "sleep 2 && systemctl --user restart knx-bridge"])

        return {"ok": True, "message": "Restore successful. System will restart."}

    except Exception as e:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@app.get("/api/system/logs")
async def system_logs(service: str = "knx-bridge", lines: int = 50, x_knx_token: Optional[str] = Header(default=None), current_user: dict = Depends(auth_utils.require_admin)):
    check_auth(x_knx_token)
    if service not in ["knx-bridge", "knx-frontend", "ngrok", "openclaw"]:
        raise HTTPException(status_code=400, detail="Invalid service name")
        
    try:
        cmd = ["journalctl", "--user", "-u", service, "-n", str(lines), "--no-pager"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"logs": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

# AUTHENTICATION API
# ---------------------------------------------------------

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    import sqlite3
    from datetime import timedelta
    conn = sqlite3.connect('smarthome.db')
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
    conn.close()

    if not user or not auth_utils.verify_password(req.password, user['password_hash']):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        payload={"sub": user["username"], "role": user["role"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth_utils.get_current_user)):
    user_info = dict(current_user)
    if 'password_hash' in user_info:
        del user_info['password_hash']
    return user_info

@app.get("/api/users")
async def get_users(current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT id, username, role, created_at FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "Member"

@app.post("/api/users")
async def create_user(req: CreateUserRequest, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    try:
        pw_hash = auth_utils.get_password_hash(req.password)
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (req.username, pw_hash, req.role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    conn.close()
    return {"status": "success", "message": "User created"}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    conn = sqlite3.connect('smarthome.db')
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "User deleted"}

from pydantic import BaseModel
from typing import List, Optional, Any

class SceneAction(BaseModel):
    device: str
    action: str
    value: Optional[Any] = None
    delay_seconds: Optional[float] = 0.0
    condition_json: Optional[str] = None
    retry_count: Optional[int] = 0
    timeout_seconds: Optional[float] = 30.0
    comment: Optional[str] = None
    enabled: Optional[bool] = True

class ScenePayload(BaseModel):
    name: str
    description: Optional[str] = ""
    actions: List[SceneAction]

@app.get("/api/scenes")
async def get_scenes(current_user: dict = Depends(auth_utils.get_current_user)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    conn.row_factory = sqlite3.Row
    scenes_db = conn.execute("SELECT * FROM scenes").fetchall()
    
    result = {}
    for s in scenes_db:
        scene_id = str(s['id'])
        actions_db = conn.execute("SELECT * FROM scene_actions WHERE scene_id=?", (s['id'],)).fetchall()
        actions = []
        for a in actions_db:
            actions.append({
                "device": a["device_id"],
                "action": a["action"],
                "value": a["value"],
                "delay_seconds": a["delay_seconds"],
                "condition_json": a["condition_json"],
                "retry_count": a["retry_count"],
                "timeout_seconds": a["timeout_seconds"],
                "comment": a["comment"],
                "enabled": bool(a["enabled"]) if a["enabled"] is not None else True
            })
        result[scene_id] = {
            "name": s["name"],
            "description": s["description"],
            "actions": actions
        }
    conn.close()
    return result

@app.post("/api/scenes")
async def create_scene(payload: ScenePayload, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3, json, time
    conn = sqlite3.connect('smarthome.db')
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO scenes (name, description) VALUES (?, ?)", (payload.name, payload.description))
        scene_id = cursor.lastrowid
        
        actions_for_version = []
        for a in payload.actions:
            val_str = str(a.value) if a.value is not None else None
            cursor.execute("""
                INSERT INTO scene_actions 
                (scene_id, device_id, action, value, delay_seconds, condition_json, retry_count, timeout_seconds, comment, enabled) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scene_id, a.device, a.action, val_str, a.delay_seconds or 0.0, 
                a.condition_json, a.retry_count or 0, a.timeout_seconds or 30.0, a.comment, int(a.enabled) if a.enabled is not None else 1
            ))
            actions_for_version.append(a.dict())
            
        cursor.execute("INSERT INTO scene_versions (scene_id, actions_json, updated_at) VALUES (?, ?, ?)",
                       (scene_id, json.dumps(actions_for_version), time.time()))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"status": "success", "id": scene_id}

@app.put("/api/scenes/{scene_id}")
async def update_scene(scene_id: int, payload: ScenePayload, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3, json, time
    conn = sqlite3.connect('smarthome.db')
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE scenes SET name=?, description=? WHERE id=?", (payload.name, payload.description, scene_id))
        cursor.execute("DELETE FROM scene_actions WHERE scene_id=?", (scene_id,))
        
        actions_for_version = []
        for a in payload.actions:
            val_str = str(a.value) if a.value is not None else None
            cursor.execute("""
                INSERT INTO scene_actions 
                (scene_id, device_id, action, value, delay_seconds, condition_json, retry_count, timeout_seconds, comment, enabled) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scene_id, a.device, a.action, val_str, a.delay_seconds or 0.0, 
                a.condition_json, a.retry_count or 0, a.timeout_seconds or 30.0, a.comment, int(a.enabled) if a.enabled is not None else 1
            ))
            actions_for_version.append(a.dict())
            
        cursor.execute("INSERT INTO scene_versions (scene_id, actions_json, updated_at) VALUES (?, ?, ?)",
                       (scene_id, json.dumps(actions_for_version), time.time()))
                       
        # Keep only last 10 versions
        cursor.execute("""
            DELETE FROM scene_versions WHERE scene_id=? AND id NOT IN (
                SELECT id FROM scene_versions WHERE scene_id=? ORDER BY updated_at DESC LIMIT 10
            )
        """, (scene_id, scene_id))
        
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"status": "success"}

@app.delete("/api/scenes/{scene_id}")
async def delete_scene(scene_id: int, current_user: dict = Depends(auth_utils.require_admin)):
    import sqlite3
    conn = sqlite3.connect('smarthome.db')
    conn.execute("DELETE FROM scenes WHERE id=?", (scene_id,))
    # versions and actions will be CASCADE deleted
    conn.commit()
    conn.close()
    return {"status": "success"}
    
@app.get("/api/scenes/{scene_id}/versions")
async def get_scene_versions(scene_id: int, current_user: dict = Depends(auth_utils.get_current_user)):
    import sqlite3, json
    conn = sqlite3.connect('smarthome.db')
    conn.row_factory = sqlite3.Row
    versions_db = conn.execute("SELECT * FROM scene_versions WHERE scene_id=? ORDER BY updated_at DESC", (scene_id,)).fetchall()
    conn.close()
    
    result = []
    for v in versions_db:
        result.append({
            "id": v["id"],
            "scene_id": v["scene_id"],
            "actions": json.loads(v["actions_json"]),
            "updated_at": v["updated_at"]
        })
    return result

class KNXWriteRequest(BaseModel):
    address: str
    value: Any
    value_type: Optional[str] = None

@app.post("/api/knx/write")
async def api_knx_write(req: KNXWriteRequest, current_user: dict = Depends(auth_utils.require_admin)):
    global _knx_driver
    if not _knx_driver or not _knx_driver.is_connected:
        raise HTTPException(status_code=503, detail="KNX not connected")
    try:
        await _knx_driver.write(req.address, req.value, value_type=req.value_type)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class KNXReadRequest(BaseModel):
    address: str
    value_type: Optional[str] = None

@app.post("/api/knx/read")
async def api_knx_read(req: KNXReadRequest, current_user: dict = Depends(auth_utils.require_admin)):
    global _knx_driver
    if not _knx_driver or not _knx_driver.is_connected:
        raise HTTPException(status_code=503, detail="KNX not connected")
    try:
        result = await _knx_driver.read(req.address, value_type=req.value_type)
        return {"status": "success", "value": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
