import re

with open("app.py", "r") as f:
    code = f.read()

old_import = """@app.post("/devices/import")
async def import_devices(
    request: Request,
    current_user: dict = Depends(auth_utils.require_admin)
):
    try:
        data = await request.json()
        global DEVICES
        DEVICES.update(data)
        save_devices()
        return {"ok": True, "message": "Devices imported successfully"}"""

new_import = """@app.post("/devices/import")
async def import_devices(
    request: Request,
    current_user: dict = Depends(auth_utils.require_admin)
):
    try:
        payload = await request.json()
        global DEVICES
        
        mode = payload.get("mode", "merge") # 'merge' or 'overwrite'
        devices_to_import = payload.get("devices", [])
        
        imported_count = 0
        for dev in devices_to_import:
            device_id = dev.get("device_id")
            if not device_id: continue
            
            if mode == "overwrite" or device_id not in DEVICES:
                DEVICES[device_id] = {
                    k: v for k, v in dev.items() if k != "device_id"
                }
                imported_count += 1
                
        save_devices()
        
        # Publish event
        from core.event_bus import DomainEvent, EventType
        if 'event_bus' in globals() and event_bus:
            event_bus.publish(DomainEvent(
                type=EventType.SYSTEM_ALERT,
                source="DeviceImport",
                data={"message": f"Imported {imported_count} devices", "action": "reload_required"}
            ))
            
        return {"ok": True, "imported": imported_count, "message": f"{imported_count} devices imported successfully"}"""

code = code.replace(old_import, new_import)

# Also update add_device and update_device to emit events instead of requiring manual reload
# But wait, we can just let the frontend call /platform/reload

with open("app.py", "w") as f:
    f.write(code)
