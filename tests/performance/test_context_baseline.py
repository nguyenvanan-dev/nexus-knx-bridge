import pytest
import time
from core.ai_context import ContextBuilder

def test_context_baseline(mock_db_path, mock_device_service):
    cb = ContextBuilder(mock_device_service, None, mock_db_path)
    start = time.time()
    cb.build_context("perf_session", "Hello")
    end = time.time()
    latency_ms = (end - start) * 1000
    print(f"\nBaseline Latency: {latency_ms:.2f} ms")
    assert True
