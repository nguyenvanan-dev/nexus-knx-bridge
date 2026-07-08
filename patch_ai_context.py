import re

with open("core/ai_context.py", "r") as f:
    code = f.read()

# Add house mode logic
if "house_mode" not in code:
    code = code.replace(
        '"time": time.strftime("%Y-%m-%d %H:%M:%S"),',
        '"time": time.strftime("%Y-%m-%d %H:%M:%S"),\n            "house_mode": self._get_house_mode(),'
    )
    
    house_mode_func = """
    def _get_house_mode(self) -> str:
        # Currently defaults to 'Home'. In the future, this could be driven by a virtual device 'sys_house_mode'
        # in StateManager.
        sys_state = self._state.get_state("sys_house_mode")
        if sys_state:
            return sys_state
        return "Home"
"""
    
    code = code.replace("    def _get_device_snapshot(self)", house_mode_func + "\n    def _get_device_snapshot(self)")

with open("core/ai_context.py", "w") as f:
    f.write(code)
