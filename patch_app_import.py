import re
import os

with open("app.py", "r") as f:
    code = f.read()

# We need to replace the import_devices route entirely to use SQLite transaction.
old_import_route_pattern = re.compile(r'@app\.post\("/devices/import"\).*?return \{"ok": True.*?\}', re.DOTALL)

new_import_route = """@app.post("/devices/import")
async def import_devices(
    request: Request,
    current_user: dict = Depends(auth_utils.require_admin)
):
    try:
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
            global DEVICES
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
                type=EventType.DEVICE_REGISTRY_UPDATED,
                source="BulkImport",
                data={
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
        }"""

code = old_import_route_pattern.sub(new_import_route, code)

with open("app.py", "w") as f:
    f.write(code)
