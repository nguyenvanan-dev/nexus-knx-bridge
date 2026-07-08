import urllib.request
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000"

def post_json(path, data):
    req = urllib.request.Request(API_URL + path, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json', 'X-Admin-Token': 'test-admin', 'Authorization': 'Bearer dummy'})
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def get_json(path):
    req = urllib.request.Request(API_URL + path, headers={'X-Admin-Token': 'test-admin', 'Authorization': 'Bearer dummy'})
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def run_tests():
    logger.info("Waiting for server to start...")
    time.sleep(2)
    
    logger.info("=== 1. Test Skip Mode (Duplicate ID) ===")
    base_dev = [{"device_id": "test_light_1", "name": "Light 1", "type": "light", "onoff_ga": "1/1/1"}]
    status, data = post_json("/devices/import", {"mode": "skip", "devices": base_dev})
    assert status == 200, f"Failed base import: {data}"
    
    status, data = post_json("/devices/import", {"mode": "skip", "devices": base_dev})
    assert data["skipped"] == 1, "Expected 1 skipped device"
    
    logger.info("=== 2. Test Overwrite Mode ===")
    modified_dev = [{"device_id": "test_light_1", "name": "Light 1 Modified", "type": "light", "onoff_ga": "1/1/1"}]
    status, data = post_json("/devices/import", {"mode": "overwrite", "devices": modified_dev})
    assert data["imported"] == 1, "Expected 1 overwritten device"
    
    status, context = get_json("/api/ai/context")
    assert context["devices"].get("test_light_1") is not None, "Device missing from Context"
    
    logger.info("=== 3. Test Rename Mode ===")
    status, data = post_json("/devices/import", {"mode": "rename", "devices": modified_dev})
    if status == 500 or status == 400:
        logger.info("Rename failed as expected due to Duplicate GA!")
    else:
        logger.error(f"Rename should have failed due to duplicate GA! Output: {data}")
        
    logger.info("=== 4. Test Duplicate GA Rollback ===")
    bad_batch = [
        {"device_id": "test_light_2", "name": "Light 2", "type": "light", "onoff_ga": "2/2/2"},
        {"device_id": "test_light_3", "name": "Light 3", "type": "light", "onoff_ga": "1/1/1"}
    ]
    status, data = post_json("/devices/import", {"mode": "skip", "devices": bad_batch})
    assert status == 500 or status == 400, "Should have failed due to duplicate GA"
    
    status, context = get_json("/api/ai/context")
    assert "test_light_2" not in context["devices"], "Rollback failed! test_light_2 was inserted!"
    logger.info("Rollback successful!")
    
    logger.info("=== 5. Test AI Context ===")
    assert "test_light_1" in context["devices"], "AI Context doesn't see test_light_1"
    logger.info("AI Context sees the imported devices.")
    
    logger.info("=== 6. Test 500 devices import ===")
    huge_batch = [{"device_id": f"bulk_light_{i}", "name": f"Bulk {i}", "onoff_ga": f"10/1/{i}"} for i in range(500)]
    status, data = post_json("/devices/import", {"mode": "skip", "devices": huge_batch})
    assert status == 200
    assert data["imported"] == 500, f"Expected 500 imported, got {data['imported']}"
    logger.info("500 devices imported successfully!")

    logger.info("ALL TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
