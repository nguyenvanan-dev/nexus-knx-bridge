with open("core/automation_engine_v2.py", "r") as f:
    code = f.read()

import re
code = re.sub(r'notify_fn=None,\n\s*', '', code)
code = re.sub(r'self\._notify_fn = notify_fn\n\s*', '', code)
code = re.sub(r'notify_fn=self\._notify_fn,\n\s*', '', code)

with open("core/automation_engine_v2.py", "w") as f:
    f.write(code)
