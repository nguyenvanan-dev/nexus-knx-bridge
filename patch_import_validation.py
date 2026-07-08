import re

with open("app.py", "r") as f:
    code = f.read()

pattern = re.compile(r'(elif mode == "overwrite":\n\s+pass # keep device_id, will overwrite in DB\n)', re.DOTALL)

replacement = r"""\1
                # GA Validation
                for ga_field in ["onoff_ga", "status_ga", "brightness_ga", "brightness_status_ga", "color_ga", "color_status_ga"]:
                    ga_val = dev.get(ga_field)
                    if ga_val:
                        if not re.match(r'^\d+/\d+/\d+$', str(ga_val)):
                            raise ValueError(f"Invalid KNX GA format for {device_id}: {ga_val}")
"""

code = re.sub(pattern, replacement, code)

with open("app.py", "w") as f:
    f.write(code)
