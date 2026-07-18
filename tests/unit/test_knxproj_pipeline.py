import sys
import json
import sqlite3
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tools.apply_device_proposal import _extract_any_ga, _validate_device

def test_extract_any_ga_with_null_fields():
    # Case 1: Device dict where fields are None
    dev = {
        "device_id": "test_device",
        "name": "Test Device",
        "type": "light",
        "onoff_ga": "1/1/1",
        "status_ga": None,
        "legacy_fields": None,
        "functions": None,
        "capabilities": None,
        "knx_config_payload": None,
        "aliases": None
    }
    
    gas = _extract_any_ga(dev)
    assert gas == ["1/1/1"]


def test_extract_any_ga_with_invalid_payload_json():
    # Case 2: knx_config_payload is an invalid JSON string
    dev = {
        "device_id": "test_device",
        "knx_config_payload": "{invalid json}",
        "capabilities": None
    }
    gas = _extract_any_ga(dev)
    assert gas == []


def test_extract_any_ga_with_empty_structures():
    # Case 3: capabilities and legacy_fields exist but are empty dicts or lists
    dev = {
        "device_id": "test_device",
        "name": "Test Device",
        "type": "light",
        "onoff_ga": "1/1/1",
        "legacy_fields": {},
        "functions": [],
        "capabilities": {},
        "knx_config_payload": {}
    }
    gas = _extract_any_ga(dev)
    assert gas == ["1/1/1"]


def test_extract_any_ga_from_sqlite_row_with_null_payload(tmp_path):
    # Case 4: Simulate row fetched from SQLite where knx_config_payload is NULL
    temp_db_file = tmp_path / "test_smarthome.db"
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
            aliases TEXT,
            require_confirm BOOLEAN,
            enabled BOOLEAN,
            knx_config_payload TEXT
        )
    """)
    
    # Insert device with NULL knx_config_payload, NULL aliases, and NULL status_ga
    c.execute("""
        INSERT INTO devices (
            device_id, name, room, type,
            onoff_ga, status_ga,
            supports_brightness, brightness_ga, brightness_status_ga,
            color_ga, color_status_ga,
            aliases, require_confirm, enabled,
            knx_config_payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "test_null_payload_dev", "Test Null Payload", "living_room", "light",
        "1/1/10", None,
        0, None, None,
        None, None,
        None, 0, 1,
        None
    ))
    conn.commit()
    
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT device_id, name, onoff_ga, status_ga, brightness_ga, brightness_status_ga, color_ga, color_status_ga, knx_config_payload FROM devices WHERE enabled = 1")
    row = cur.fetchone()
    assert row is not None
    
    row_dict = dict(row)
    # The knx_config_payload inside row_dict is None (NULL in DB)
    assert row_dict["knx_config_payload"] is None
    
    # Execute extraction
    gas = _extract_any_ga(row_dict)
    assert gas == ["1/1/10"]
    
    conn.close()
