with open("app.py", "r") as f:
    code = f.read()

import re
code = re.sub(r'notify_fn=_notification_engine\.send_notification,\n\s*', '', code)

with open("app.py", "w") as f:
    f.write(code)
