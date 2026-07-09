from typing import List, Dict
from core.repositories.memory_repository import MemoryRepository

class UserMemoryBuilder:
    def __init__(self, memory_repo: MemoryRepository):
        self._memory_repo = memory_repo

    def build(self, user_id: str) -> List[Dict]:
        """Builds user memory ordered by confidence and importance."""
        return self._memory_repo.get_user_memory(user_id)
