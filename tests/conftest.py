import pytest
import sqlite3
import os
from pathlib import Path

# Thư mục temp DB để chạy test không ảnh hưởng DB chính
TEST_DB_PATH = Path("test_smarthome.db")

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Khởi tạo schema DB tạm cho toàn bộ các Unit/Integration test."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        
    conn = sqlite3.connect(TEST_DB_PATH)
    c = conn.cursor()
    # Tạo schema ai_conversations
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            platform TEXT,
            message_id TEXT,
            reply_to_message_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    ''')
    # Tạo schema ai_memories
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            type TEXT,
            key TEXT,
            value TEXT,
            importance INTEGER DEFAULT 1,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'system',
            summary_version INTEGER,
            source_message_start TEXT,
            source_message_end TEXT,
            model TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    yield TEST_DB_PATH
    
    # Teardown
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

@pytest.fixture
def mock_db_path():
    return TEST_DB_PATH

@pytest.fixture
def mock_device_service():
    class MockService:
        def get_all_devices_with_state(self):
            return {
                "light_1": {"name": "Đèn 1", "state": "on", "type": "light"},
                "light_2": {"name": "Đèn 2", "state": "off", "type": "light"}
            }
        def get_house_mode(self):
            return "Evening"
    return MockService()
