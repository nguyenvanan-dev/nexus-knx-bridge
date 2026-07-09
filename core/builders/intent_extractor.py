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
        For Sprint 11, we include implicit intent extraction (e.g. 'tối quá' -> brightness++)
        This simulates an LLM understanding the underlying user need.
        """
        intent = Intent(raw_text=query)
        q = query.lower()
        
        # 1. Implicit Intent Extraction (Semantic Simulation)
        if "tối quá" in q or "hơi tối" in q:
            intent.intent_type = "device_control"
            intent.device_type = "light"
            intent.action = "increase"
            intent.value = "brightness"
        elif "chói quá" in q or "sáng quá" in q:
            intent.intent_type = "device_control"
            intent.device_type = "light"
            intent.action = "decrease"
            intent.value = "brightness"
        elif "nóng quá" in q:
            intent.intent_type = "device_control"
            intent.device_type = "ac"
            intent.action = "decrease"
            intent.value = "temperature"
        elif "lạnh quá" in q:
            intent.intent_type = "device_control"
            intent.device_type = "ac"
            intent.action = "increase"
            intent.value = "temperature"
            
        # 2. Explicit Intent Extraction
        elif "bật" in q or "tắt" in q or "giảm" in q or "tăng" in q:
            intent.intent_type = "device_control"
            if "bật" in q: intent.action = "on"
            if "tắt" in q: intent.action = "off"
            
        # 3. Entity Extraction (Room / Device)
        if "phòng khách" in q:
            intent.room = "phòng khách"
        elif "phòng ngủ" in q:
            intent.room = "phòng ngủ"
            
        if "đèn" in q and not intent.device_type:
            intent.device_type = "light"
        elif "rèm" in q and not intent.device_type:
            intent.device_type = "curtain"
        elif "điều hòa" in q or "máy lạnh" in q and not intent.device_type:
            intent.device_type = "ac"
            
        return intent
