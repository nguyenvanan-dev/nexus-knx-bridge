from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class Intent:
    intent_type: str = "unknown"  # e.g., device_control, query, weather
    room: Optional[str] = None
    device_type: Optional[str] = None
    action: Optional[str] = None
    value: Optional[str] = None
    raw_text: str = ""

class IntentExtractor:
    def extract(self, query: str) -> Intent:
        """
        Extracts semantic intent from a raw query.
        For Sprint 10, this is a simplified stub. In a real system, 
        this would call a local NLP model or use heuristics.
        """
        intent = Intent(raw_text=query)
        q = query.lower()
        
        if "bật" in q or "tắt" in q or "giảm" in q or "tăng" in q:
            intent.intent_type = "device_control"
        if "phòng khách" in q:
            intent.room = "phòng khách"
        elif "phòng ngủ" in q:
            intent.room = "phòng ngủ"
            
        if "đèn" in q:
            intent.device_type = "light"
        elif "rèm" in q:
            intent.device_type = "curtain"
            
        return intent
