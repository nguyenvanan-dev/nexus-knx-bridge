import json
import sqlite3
from pathlib import Path
import os
import shutil

BASE_DIR = Path("/home/an/knx-bridge")
DEVICES_FILE = BASE_DIR / "devices.json"
DB_FILE = BASE_DIR / "smarthome.db"

def init_devices_table(cursor):
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

def run_migration():
    if not DEVICES_FILE.exists():
        print(f"File {DEVICES_FILE} does not exist.")
        return

    with open(DEVICES_FILE, "r", encoding="utf-8") as f:
        devices = json.load(f)

    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    
    init_devices_table(cursor)

    for device_id, data in devices.items():
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
        print(f"Migrated device: {device_id}")

    conn.commit()
    conn.close()
    
    # Backup the original file
    shutil.copy(DEVICES_FILE, str(DEVICES_FILE) + ".bak")
    print(f"Done! Original devices.json backed up to devices.json.bak")

if __name__ == "__main__":
    run_migration()
