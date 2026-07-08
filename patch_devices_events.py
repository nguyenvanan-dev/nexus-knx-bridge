import re

with open("app.py", "r") as f:
    code = f.read()

# For add_device
old_add = """    DEVICES[device_id] = data
    save_devices()

    return {"""

new_add = """    DEVICES[device_id] = data
    save_devices()

    # Emit event
    from core.event_bus import DomainEvent, EventType
    if 'event_bus' in globals() and event_bus:
        event_bus.publish(DomainEvent(
            type=EventType.SYSTEM_ALERT,
            source="DeviceWizard",
            data={"message": f"Added device {device_id}", "action": "reload_required"}
        ))

    return {"""

code = code.replace(old_add, new_add)

# For update_device
old_update = """    for key, value in update_data.items():
        if value is not None:
            DEVICES[device_id][key] = value

    save_devices()

    return {"""

new_update = """    for key, value in update_data.items():
        if value is not None:
            DEVICES[device_id][key] = value

    save_devices()

    # Emit event
    from core.event_bus import DomainEvent, EventType
    if 'event_bus' in globals() and event_bus:
        event_bus.publish(DomainEvent(
            type=EventType.SYSTEM_ALERT,
            source="DeviceWizard",
            data={"message": f"Updated device {device_id}", "action": "reload_required"}
        ))

    return {"""

code = code.replace(old_update, new_update)

with open("app.py", "w") as f:
    f.write(code)
