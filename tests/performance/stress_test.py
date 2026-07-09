import asyncio
import time
from fastapi.testclient import TestClient
from app import app
import psutil
import os
import logging
import concurrent.futures

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def stress_test():
    logger.info("Starting Stress Test for KNX AI Bridge (Phase D)...")
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024
    logger.info(f"Memory before: {mem_before:.2f} MB")

    client = TestClient(app)
    
    start = time.time()
    
    def fetch_health():
        return client.get("/health")
        
    def fetch_reload():
        return client.post("/platform/reload", headers={"X-API-KEY": "knx-secret-key-123"})
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        # Test 1: 200 concurrent /health GET requests
        health_futures = [executor.submit(fetch_health) for _ in range(200)]
        health_results = [f.result() for f in concurrent.futures.as_completed(health_futures)]
        
        success = sum(1 for r in health_results if r.status_code == 200)
        logger.info(f"Test 1 (GET /health) - 200 requests: {success} succeeded.")
        
        # Test 2: 50 concurrent mutating requests (API Key required)
        reload_futures = [executor.submit(fetch_reload) for _ in range(50)]
        reload_results = [f.result() for f in concurrent.futures.as_completed(reload_futures)]
        
        success2 = sum(1 for r in reload_results if r.status_code == 200)
        logger.info(f"Test 2 (POST with API Key) - 50 requests: {success2} succeeded.")

    end = time.time()
    logger.info(f"Total time for 250 requests: {end - start:.2f}s")
        
    mem_after = process.memory_info().rss / 1024 / 1024
    logger.info(f"Memory after: {mem_after:.2f} MB")
    logger.info(f"Memory delta: {mem_after - mem_before:.2f} MB")
    
    if (mem_after - mem_before) > 50:
        logger.error("WARNING: Possible memory leak detected!")
    else:
        logger.info("Stress Test PASSED.")

if __name__ == "__main__":
    stress_test()
