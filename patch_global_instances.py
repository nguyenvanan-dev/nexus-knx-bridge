import re

with open("app.py", "r") as f:
    code = f.read()

# Let's insert the DeviceService instantiation somewhere.
# Before ContextBuilder would be ideal. I see that currently we have:
# _context_builder = None (maybe we don't have it at all?)
# Let's search where _state_manager is instantiated
if "_state_manager =" in code:
    print("Found _state_manager")
else:
    print("No _state_manager found")

