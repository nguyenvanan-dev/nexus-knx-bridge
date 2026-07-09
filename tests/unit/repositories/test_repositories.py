import pytest
import sqlite3
from core.repositories.conversation_repository import ConversationRepository
from core.repositories.memory_repository import MemoryRepository

def test_conversation_repository_crud(mock_db_path):
    repo = ConversationRepository(mock_db_path)
    session_id = "test_session_1"
    
    repo.save_message(session_id, "user", "Bật đèn")
    repo.save_message(session_id, "assistant", "Đã bật đèn")
    
    messages = repo.get_recent_messages(session_id, limit=10)
    assert len(messages) == 2
    assert messages[0]['role'] == "user"
    assert messages[1]['role'] == "assistant"

def test_memory_repository_crud(mock_db_path):
    repo = MemoryRepository(mock_db_path)
    user_id = "user_1"
    
    repo.save_preference(user_id, "light_color", "vàng")
    
    memories = repo.get_user_memory(user_id)
    assert len(memories) == 1
    assert memories[0]['key'] == "light_color"
    assert memories[0]['value'] == "vàng"
