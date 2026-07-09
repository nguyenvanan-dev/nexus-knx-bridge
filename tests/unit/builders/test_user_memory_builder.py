import pytest
from datetime import datetime, timedelta
from core.builders.user_memory_builder import UserMemoryBuilder

class MockMemoryRepository:
    def __init__(self, memories):
        self.memories = memories
    def get_user_memory(self, user_id: str):
        return self.memories

def test_memory_confidence_decay():
    now = datetime.now()
    # 20 days ago -> decay by 0.2
    # 40 days ago -> decay by 0.4
    
    m20 = (now - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
    m40 = (now - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")
    
    memories = [
        {"key": "pref1", "value": "a", "confidence": 1.0, "updated_at": m20},
        {"key": "pref2", "value": "b", "confidence": 0.6, "updated_at": m40}, # 0.6 - 0.4 = 0.2 < 0.3 -> filtered
        {"key": "pref3", "value": "c", "confidence": 1.0, "updated_at": None}, # no decay
    ]
    
    repo = MockMemoryRepository(memories)
    builder = UserMemoryBuilder(repo)
    result = builder.build("user1")
    
    assert len(result) == 2
    assert result[0]["key"] == "pref1"
    assert result[0]["calculated_confidence"] == 0.8
    assert result[1]["key"] == "pref3"
    assert result[1]["calculated_confidence"] == 1.0
