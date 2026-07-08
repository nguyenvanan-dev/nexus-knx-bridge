import re

with open("app.py", "r") as f:
    code = f.read()

pattern1 = re.compile(r'(async def import_devices\([\s\S]*?\):\n\s+try:\n)', re.DOTALL)
replacement1 = r"""\1        global DEVICES\n"""
code = re.sub(pattern1, replacement1, code)

pattern2 = re.compile(r'\s+global DEVICES\n')
# We need to only remove the second one.
code = code.replace("            global DEVICES\n", "")

with open("app.py", "w") as f:
    f.write(code)
