import pytest
from core.background_queue import BackgroundQueue

def test_background_queue_workers():
    queue = BackgroundQueue(None, None)
    assert queue is not None
