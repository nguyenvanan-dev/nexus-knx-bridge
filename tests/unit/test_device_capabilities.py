import pytest
import sqlite3
import json
from pathlib import Path
from unittest.mock import MagicMock

# Intercept sqlite3 connect to redirect any smarthome.db access to a temp file
# This prevents app.py import from touching the real production database
original_connect = sqlite3.connect
def mock_sqlite3_connect(database, *args, **kwargs):
    if Path(str(database)).name == "smarthome.db":
        return original_connect("test_temp_unit_run.db", *args, **kwargs)
    return original_connect(database, *args, **kwargs)

sqlite3.connect = mock_sqlite3_connect

# Initialize a dummy test database for import time
conn = sqlite3.connect("test_temp_unit_run.db")
c = conn.cursor()
c.execute("""
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
        enabled BOOLEAN,
        knx_config_payload TEXT
    )
""")
conn.commit()
conn.close()

import app
from core.device_registry import DeviceRegistry, Device

def test_registry_capabilities_parsing_and_indexing(tmp_path):
    temp_db_file = tmp_path / "test_smarthome_registry.db"
    conn = sqlite3.connect(str(temp_db_file))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE devices (
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
            enabled BOOLEAN,
            knx_config_payload TEXT
        )
    """)

    # 1. Device with capabilities payload
    dimmer_payload = {
        "capabilities": {
            "switch": {"write_ga": "1/1/1", "status_ga": "1/1/2"},
            "brightness": {"write_ga": "1/1/3", "status_ga": "1/1/4", "dpt": "5.001", "min": 0, "max": 100}
        }
    }
    c.execute("""
        INSERT INTO devices (device_id, name, room, type, onoff_ga, status_ga, supports_brightness, brightness_ga, brightness_status_ga, enabled, knx_config_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("test_dimmer", "Test Dimmer", "living_room", "dimmer", "1/1/1", "1/1/2", 1, "1/1/3", "1/1/4", 1, json.dumps(dimmer_payload)))

    # 2. Device with invalid JSON payload
    c.execute("""
        INSERT INTO devices (device_id, name, room, type, enabled, knx_config_payload)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("test_invalid_json", "Test Invalid", "kitchen", "light", 1, "{invalid json}"))

    # 3. Device with DALI color temperature capability
    dali_payload = {
        "capabilities": {
            "switch": {"write_ga": "3/1/1", "status_ga": "3/1/2"},
            "color_temperature": {"write_ga": "3/1/3", "status_ga": "3/1/4", "min": 2000, "max": 8000, "dpt": "7.600"}
        }
    }
    c.execute("""
        INSERT INTO devices (device_id, name, room, type, enabled, knx_config_payload)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("test_dali", "Test Dali", "kitchen", "light", 1, json.dumps(dali_payload)))

    conn.commit()
    conn.close()

    registry = DeviceRegistry(temp_db_file)
    count = registry.reload()
    assert count == 3

    # Test dimmer capabilities parsing & indexing
    dimmer = registry.get("test_dimmer")
    assert dimmer is not None
    assert "brightness" in dimmer.capabilities
    assert dimmer.capabilities["brightness"]["write_ga"] == "1/1/3"
    assert "1/1/3" in dimmer.all_gas()
    assert registry.find_by_ga("1/1/3") == dimmer

    # Test invalid json fallback (no crash)
    invalid_dev = registry.get("test_invalid_json")
    assert invalid_dev is not None
    assert invalid_dev.capabilities == {}

    # Test to_dict contains capabilities
    dimmer_dict = dimmer.to_dict()
    assert "capabilities" in dimmer_dict
    assert dimmer_dict["capabilities"]["switch"]["write_ga"] == "1/1/1"


def test_normalize_device_capabilities():
    # Test flat fields to capabilities mapping
    device_data = {
        "onoff_ga": "1/1/1",
        "status_ga": "1/1/2",
        "supports_brightness": True,
        "brightness_ga": "1/1/3",
        "brightness_status_ga": "1/1/4",
        "color_rgb_ga": "1/1/5",
        "color_status_ga": "1/1/6",
        "color_temp_ga": "2/1/1",
        "color_temp_status_ga": "2/1/2",
        "color_temp_min": 2000,
        "color_temp_max": 8000,
        "temperature_set_ga": "3/1/1",
        "temperature_status_ga": "3/1/2",
        "fan_speed_ga": "3/1/3",
        "mode_ga": "3/1/4",
        "stop_ga": "4/1/1",
        "position_set_ga": "4/1/2",
        "position_status_ga": "4/1/3",
    }

    norm = app.normalize_device_capabilities(device_data)
    caps = norm["capabilities"]

    assert caps["switch"]["write_ga"] == "1/1/1"
    assert caps["brightness"]["write_ga"] == "1/1/3"
    assert caps["rgb"]["write_ga"] == "1/1/5"
    assert caps["color_temperature"]["write_ga"] == "2/1/1"
    assert caps["color_temperature"]["min"] == 2000
    assert caps["color_temperature"]["max"] == 8000
    assert caps["temperature_setpoint"]["write_ga"] == "3/1/1"
    assert caps["fan_speed"]["write_ga"] == "3/1/3"
    assert caps["mode"]["write_ga"] == "3/1/4"
    assert caps["stop"]["write_ga"] == "4/1/1"
    assert caps["position"]["write_ga"] == "4/1/2"
    assert caps["sensor_value"]["status_ga"] == "1/1/2"


@pytest.mark.asyncio
async def test_color_temperature_endpoint_logic(monkeypatch):
    # Setup mock registry
    dali_dev = Device(
        device_id="test_dali",
        name="Test Dali",
        type="light",
        capabilities={
            "color_temperature": {
                "write_ga": "3/1/3",
                "status_ga": "3/1/4",
                "min": 2000,
                "max": 8000,
                "dpt": "7.600"
            }
        }
    )
    non_dali_dev = Device(
        device_id="test_non_dali",
        name="Test Non Dali",
        type="light",
        capabilities={}
    )

    mock_registry = MagicMock()
    mock_registry.get.side_effect = lambda device_id: {
        "test_dali": dali_dev,
        "test_non_dali": non_dali_dev
    }.get(device_id)

    monkeypatch.setattr(app, "device_registry", mock_registry)

    # Mock KNX write function
    written_signals = []
    async def mock_ct_write_knx(ga, value):
        written_signals.append((ga, value))

    monkeypatch.setattr(app, "_ct_write_knx", mock_ct_write_knx)

    from app import _ColorTemperatureRequest

    # 1. Valid color temperature command
    body_valid = _ColorTemperatureRequest(device="test_dali", value=3000)
    res = await app.set_light_color_temperature(body=body_valid)
    assert res["ok"] is True
    assert res["value"] == 3000
    assert res["group_address"] == "3/1/3"
    assert written_signals == [("3/1/3", 3000)]

    # 2. Color temperature out of range (allowed: 2000-8000)
    body_invalid = _ColorTemperatureRequest(device="test_dali", value=9000)
    with pytest.raises(Exception) as excinfo:
        await app.set_light_color_temperature(body=body_invalid)
    assert "Color temperature out of range" in str(excinfo.value.detail)

    # 3. Device does not support color temperature
    body_no_support = _ColorTemperatureRequest(device="test_non_dali", value=3000)
    with pytest.raises(Exception) as excinfo:
        await app.set_light_color_temperature(body=body_no_support)
    assert "does not support color temperature" in str(excinfo.value.detail)

# Cleanup test run database at session exit
def pytest_sessionfinish(session, exitstatus):
    temp_db = Path("test_temp_run.db")
    if temp_db.exists():
        temp_db.unlink()
