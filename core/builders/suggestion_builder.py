from typing import Dict, Any, List

class SuggestionBuilder:
    def build(self, house_memory: Dict[str, Any], device_state: Dict[str, Any], time_str: str) -> List[str]:
        suggestions = []
        
        # 1. Weather based suggestions
        weather = house_memory.get("weather", {}).get("condition", "").lower()
        if "mưa" in weather or "rain" in weather:
            suggestions.append("Ngoài trời đang mưa. Anh có muốn em đóng toàn bộ cửa sổ không?")
            
        # 2. Time based suggestions
        try:
            # Assuming time_str is 'YYYY-MM-DD HH:MM:SS'
            hour = int(time_str.split(" ")[1].split(":")[0])
            if hour >= 22 or hour < 5:
                # Check if some lights are still on
                lights_on = False
                for dev_id, state in device_state.items():
                    if "light" in dev_id.lower() and state.get("state") == "on":
                        lights_on = True
                        break
                if lights_on:
                    suggestions.append("Đã khuya rồi, anh có muốn tắt bớt đèn không?")
        except Exception:
            pass
            
        return suggestions
