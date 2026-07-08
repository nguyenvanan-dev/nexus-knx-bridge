import re

with open("app.py", "r") as f:
    code = f.read()

# Let's find event_bus = EventBus() and add DeviceService and ContextBuilder right after
pattern = r'(event_bus = EventBus\(\)\n)'
replacement = r"""\1
from core.device_service import DeviceService
device_service = DeviceService(registry=device_registry, state_manager=state_manager)

_context_builder = ContextBuilder(device_service=device_service, event_bus=event_bus, db_path=_SMARTHOME_DB)
"""

code = re.sub(pattern, replacement, code)

with open("app.py", "w") as f:
    f.write(code)
