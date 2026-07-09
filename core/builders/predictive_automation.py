from typing import Dict, Any, List

class PredictiveAutomationBuilder:
    def build(self, user_memory: Dict[str, Any], time_str: str) -> List[str]:
        suggestions = []
        
        # Simple implementation: read habits from user_memory
        # Format expected in user_memory (if dict): 
        # "habits": {"22:00": {"action": "bật đèn ngủ", "streak": 7}}
        
        if not isinstance(user_memory, dict):
            return suggestions
            
        habits = user_memory.get("habits", {})
        
        try:
            current_hour = time_str.split(" ")[1].split(":")[0] + ":00"
            if current_hour in habits:
                habit = habits[current_hour]
                if habit.get("streak", 0) >= 7:
                    action = habit.get("action", "")
                    suggestions.append(f"Em thấy anh thường {action} vào lúc {current_hour}. Anh có muốn em lưu thành Automation để tự động làm mỗi ngày không?")
        except Exception:
            pass
            
        return suggestions
