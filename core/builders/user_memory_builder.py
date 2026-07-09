from typing import List, Dict
from datetime import datetime, timedelta
from core.repositories.memory_repository import MemoryRepository

class UserMemoryBuilder:
    def __init__(self, memory_repo: MemoryRepository):
        self._memory_repo = memory_repo

    def build(self, user_id: str) -> List[Dict]:
        """Builds user memory ordered by confidence and importance."""
        raw_memories = self._memory_repo.get_user_memory(user_id)
        
        # Sprint 11: Memory Confidence Decay
        # If memory is older than 30 days, reduce confidence.
        # If confidence drops below 0.3, exclude it from context to save tokens.
        
        processed_memories = []
        now = datetime.now()
        
        for mem in raw_memories:
            updated_at_str = mem.get("updated_at")
            confidence = mem.get("confidence", 1.0)
            
            if updated_at_str:
                try:
                    updated_at = datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S")
                    days_old = (now - updated_at).days
                    
                    # Decay: -0.1 for every 10 days
                    decay = (days_old // 10) * 0.1
                    confidence = max(0.0, confidence - decay)
                except Exception:
                    pass
            
            if confidence >= 0.3:
                # Store the calculated confidence
                mem_copy = dict(mem)
                mem_copy["calculated_confidence"] = confidence
                processed_memories.append(mem_copy)
                
        return processed_memories
