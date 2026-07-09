import urllib.request
import json
import time

API_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer admin_mock_token"
}

def request(method, path, data=None):
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, method=method)
    for k, v in HEADERS.items():
        req.add_header(k, v)
        
    if data:
        req.data = json.dumps(data).encode("utf-8")
        
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read()
            return response.status, json.loads(res_data) if res_data else None
    except urllib.error.HTTPError as e:
        res_data = e.read()
        return e.code, json.loads(res_data) if res_data else None

def test_rule_validation():
    print("Testing Validation...")
    
    # 1. Empty name
    status, res = request("POST", "/automation/rules/v2", data={
        "name": "",
        "trigger": {"type": "device_state", "device_id": "test_motion"},
        "actions": [{"type": "control", "device_id": "test_light", "action": "on"}]
    })
    assert status == 400
    assert "Rule name cannot be empty" in res["detail"]

    # 2. Invalid Trigger Device
    status, res = request("POST", "/automation/rules/v2", data={
        "name": "Invalid trigger",
        "trigger": {"type": "device_state", "device_id": "non_existent_dev"},
        "actions": [{"type": "control", "device_id": "test_light", "action": "on"}]
    })
    assert status == 400
    assert "Trigger device 'non_existent_dev' not found" in res["detail"]

    # 3. Invalid Action Device
    status, res = request("POST", "/automation/rules/v2", data={
        "name": "Invalid action",
        "trigger": {"type": "time", "at": "12:00"},
        "actions": [{"type": "control", "device_id": "non_existent_dev", "action": "on"}]
    })
    assert status == 400
    assert "Action device 'non_existent_dev' not found" in res["detail"]

    # 4. Infinite loop protection
    # Assuming 'test_light' exists (we should mock a device)
    # But wait, we need to create devices for testing first!
    print("✓ Validation passed")

def setup_devices():
    # Insert mock devices to DeviceRegistry
    # We can just rely on the existing devices in DB, or create one if needed
    status, res = request("POST", "/devices/import", data={
        "devices": [
            {"device_id": "test_motion", "name": "Motion", "type": "sensor", "status_ga": "9/9/1"},
            {"device_id": "test_light", "name": "Light", "type": "light", "onoff_ga": "9/9/2"}
        ]
    })
    if status != 200:
        print("Failed to setup devices:", res)

def test_crud():
    print("Testing CRUD...")
    rule_id = "test_rule_1"
    
    # Create
    status, res = request("POST", "/automation/rules/v2", data={
        "rule_id": rule_id,
        "name": "Test Rule",
        "trigger": {"type": "device_state", "device_id": "test_motion", "state": "ON"},
        "actions": [{"type": "control", "device_id": "test_light", "action": "on"}]
    })
    assert status == 200, res
    
    # Toggle
    status, res = request("PUT", f"/automation/rules/v2/{rule_id}/toggle")
    assert status == 200, res
    
    # Dry Run
    status, res = request("POST", f"/automation/rules/v2/{rule_id}/test", data={"dry_run": True})
    assert status == 200, res
    
    # Delete
    status, res = request("DELETE", f"/automation/rules/v2/{rule_id}")
    assert status == 200, res
    print("✓ CRUD passed")

if __name__ == "__main__":
    setup_devices()
    test_rule_validation()
    test_crud()
    print("ALL SPRINT 8 TESTS PASSED!")
