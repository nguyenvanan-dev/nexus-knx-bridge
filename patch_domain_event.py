import re
with open("app.py", "r") as f:
    code = f.read()

code = code.replace("type=EventType.DEVICE_ADDED", "event_type=EventType.DEVICE_ADDED")
code = code.replace("type=EventType.DEVICE_REGISTRY_UPDATED", "event_type=EventType.DEVICE_REGISTRY_UPDATED")

with open("app.py", "w") as f:
    f.write(code)
