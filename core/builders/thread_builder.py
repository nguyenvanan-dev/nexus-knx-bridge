from typing import List, Dict, Any

class ConversationThreadBuilder:
    """Strategy Interface for building a conversation thread."""
    def build(self, messages: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError

class SimpleThreadBuilder(ConversationThreadBuilder):
    def build(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Sprint 11 Implementation: 
        Tracks the active context/topic from recent messages to handle 
        follow-up requests (e.g., "bật đèn phòng khách" -> "tắt nó đi").
        Returns a structured working memory dict instead of just list.
        """
        working_memory = {
            "recent_messages": messages,
            "active_topic": {
                "last_room": None,
                "last_device": None
            }
        }
        
        # Scan from oldest to newest to find the latest entities
        for msg in reversed(messages):
            content = msg.get("content", "").lower()
            if "phòng khách" in content:
                working_memory["active_topic"]["last_room"] = "phòng khách"
            elif "phòng ngủ" in content:
                working_memory["active_topic"]["last_room"] = "phòng ngủ"
                
            if "đèn" in content:
                working_memory["active_topic"]["last_device"] = "light"
            elif "rèm" in content:
                working_memory["active_topic"]["last_device"] = "curtain"
            elif "điều hòa" in content or "máy lạnh" in content:
                working_memory["active_topic"]["last_device"] = "ac"
                
        return working_memory
