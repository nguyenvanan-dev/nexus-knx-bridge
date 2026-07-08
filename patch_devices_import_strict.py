import re

with open("app.py", "r") as f:
    code = f.read()

old_import = """@app.post("/devices/import")
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

new_import = """@app.post("/devices/import")
async def import_devices(
    request: Request,
    current_user: dict = Depends(auth_utils.require_admin)
):
    try:
        payload = await request.json()
        global DEVICES
        
        mode = payload.get("mode", "skip") # 'skip', 'overwrite', 'rename'
        devices_to_import = payload.get("devices", [])
        
        imported_count = 0
        for dev in devices_to_import:
            original_device_id = dev.get("device_id")
            if not original_device_id: continue
            
            device_id = original_device_id
            
            if device_id in DEVICES:
                if mode == "skip":
                    continue
                elif mode == "rename":
                    # Generate a unique name
                    counter = 1
                    while f"{original_device_id}_{counter}" in DEVICES:
                        counter += 1
                    device_id = f"{original_device_id}_{counter}"
                elif mode == "overwrite":
                    pass # device_id stays the same, will overwrite
            
            DEVICES[device_id] = {
                k: v for k, v in dev.items() if k != "device_id"
            }
            imported_count += 1
                
        save_devices()
        
        # Reload DeviceRegistry directly without full restart
        if 'device_registry' in globals():
            device_registry.reload()
            
        # Emit generic reload event for dashboard
        from core.event_bus import DomainEvent, EventType
        if 'event_bus' in globals() and event_bus:
            event_bus.publish(DomainEvent(
                type=EventType.SYSTEM_ALERT,
                source="DeviceImport",
                data={"message": f"Imported {imported_count} devices", "action": "reload_required"}
            ))
            
        return {"ok": True, "imported": imported_count, "message": f"{imported_count} devices imported successfully"}"""

if "mode = payload.get(\"mode\", \"merge\")" in code:
    code = code.replace(old_import, new_import)
else:
    print("Warning: could not find old import block. Proceeding manually.")

with open("app.py", "w") as f:
    f.write(code)
