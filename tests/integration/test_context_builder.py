import pytest
import asyncio
from core.ai_context import ContextBuilder
from pathlib import Path

def test_context_coordinator_flow(mock_db_path, mock_device_service):
    cb = ContextBuilder(mock_device_service, None, mock_db_path)
    session_id = "test_session_flow"
    
    async def run():
        cb.save_message(session_id, "user", "Bật đèn")
        context_str = cb.build_context(session_id, "Bật đèn")
        assert "Bật đèn" in context_str
    
    asyncio.run(run())
