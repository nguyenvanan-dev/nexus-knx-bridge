import re

with open("app.py", "r") as f:
    code = f.read()

pattern = re.compile(r'(if not re.match\(r\'\^\\d\+/\\d\+/\\d\+\$\', str\(ga_val\)\):\n\s+raise ValueError\(f"Invalid KNX GA format for \{device_id\}: \{ga_val\}"\)\n)', re.DOTALL)

replacement = r"""\1                        
                        # Duplicate GA check against registry
                        if 'device_registry' in globals() and device_registry:
                            existing_dev = device_registry.find_by_ga(ga_val)
                            if existing_dev and existing_dev.device_id != device_id:
                                raise ValueError(f"Duplicate GA {ga_val} found (already used by {existing_dev.device_id})")
"""

code = re.sub(pattern, replacement, code)

with open("app.py", "w") as f:
    f.write(code)
