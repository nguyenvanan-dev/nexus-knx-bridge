import json
import os
import sqlite3
import tempfile
from pathlib import Path
import pytest

from core.knxproj_parser import ETSParser
from core.proposal_schema import make_proposal_base
from tools.apply_device_proposal import _safe_device_id, _extract_any_ga, _validate_device


def test_parser_helpers():
    parser = ETSParser()
    # normalize_ga
    assert parser.normalize_ga("1/1/1") == "1/1/1"
    assert parser.normalize_ga("01/01/001") == "1/1/1"
    assert parser.normalize_ga(None) == ""

    # normalize_dpt
    assert parser.normalize_dpt("1.001") == "1.001"
    assert parser.normalize_dpt("DPST-1-1") == "1.001"
    assert parser.normalize_dpt("1") == "1.001"
    assert parser.normalize_dpt(None) == ""

    # infer_room_from_name_path
    assert parser.infer_room_from_name_path("Kitchen Light", "Main / Line") == "Kitchen"
    assert parser.infer_room_from_name_path("Some Device", "Area / Living Room Line") == "Living Room"
    assert parser.infer_room_from_name_path("Generic", "Area / Line") == "Common"

    # infer_device_type
    assert parser.infer_device_type(["1.001"], "Kitchen Light") == "light"
    assert parser.infer_device_type(["5.001"], "Dimmer Channel") == "dimmer"
    assert parser.infer_device_type(["7.600"], "Kelvin Light") == "color_light"
    assert parser.infer_device_type(["232.600"], "RGB Strip") == "rgbw"
    assert parser.infer_device_type(["1.008", "5.001"], "Curtain Position") == "blind"
    assert parser.infer_device_type(["9.001", "20.102"], "AC Controller") == "hvac"
    assert parser.infer_device_type(["9.001"], "Temperature Sensor") == "sensor"


def test_proposal_schema():
    prop = make_proposal_base("project.knxproj", "My Home", "3.9.0")
    assert prop["proposal_type"] == "knxproj_import"
    assert prop["source"]["file"] == "project.knxproj"
    assert prop["source"]["project_name"] == "My Home"
    assert isinstance(prop["summary"], dict)
    assert isinstance(prop["proposed_devices"], list)


def test_applier_helpers():
    dev = {
        "name": "Test Light",
        "type": "light",
        "room": "Bedroom",
        "legacy_fields": {
            "onoff_ga": "1/1/1",
            "status_ga": "1/1/2"
        }
    }
    # _safe_device_id
    assert _safe_device_id(dev) == "bedroom_light_test_light"

    # _extract_any_ga
    gas = _extract_any_ga(dev)
    assert "1/1/1" in gas
    assert "1/1/2" in gas

    # _validate_device
    valid, reason = _validate_device(dev)
    assert valid is True

    # invalid device
    invalid_dev = {"type": "light"}
    valid, reason = _validate_device(invalid_dev)
    assert valid is False


def test_apply_proposal_dry_run_and_confirm():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_smarthome.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE devices (
                device_id TEXT PRIMARY KEY,
                name TEXT,
                room TEXT,
                type TEXT,
                onoff_ga TEXT,
                status_ga TEXT,
                supports_brightness INTEGER,
                brightness_ga TEXT,
                brightness_status_ga TEXT,
                color_ga TEXT,
                color_status_ga TEXT,
                aliases TEXT,
                require_confirm INTEGER,
                enabled INTEGER,
                knx_config_payload TEXT
            )
        """)
        conn.commit()
        conn.close()

        import tools.apply_device_proposal
        original_db = tools.apply_device_proposal.DB_PATH
        tools.apply_device_proposal.DB_PATH = db_path

        proposal_file = Path(tmpdir) / "test_proposal.json"
        mock_proposal = {
            "proposal_type": "knxproj_import",
            "proposed_devices": [
                {
                    "device_id": "knx_test_light",
                    "name": "Test Light Zone",
                    "room": "Kitchen",
                    "type": "light",
                    "status": "ready",
                    "legacy_fields": {
                        "onoff_ga": "1/1/10",
                        "status_ga": "1/1/11"
                    },
                    "knx_config_payload": {
                        "capabilities": {
                            "onoff": {"write_ga": "1/1/10", "status_ga": "1/1/11", "dpt": "1.001"}
                        }
                    }
                }
            ]
        }
        proposal_file.write_text(json.dumps(mock_proposal))

        import sys
        from unittest.mock import patch

        test_args = ["tools/apply_device_proposal.py", str(proposal_file), "--dry-run"]
        with patch.object(sys, 'argv', test_args):
            try:
                tools.apply_device_proposal.main()
            except SystemExit as e:
                assert False, f"Dry-run exited unexpectedly: {e}"

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM devices")
        count = cursor.fetchone()[0]
        assert count == 0

        test_args = ["tools/apply_device_proposal.py", str(proposal_file), "--confirm"]
        with patch.object(sys, 'argv', test_args):
            try:
                tools.apply_device_proposal.main()
            except SystemExit as e:
                if e.code != 0:
                    assert False, f"Confirm exited with error: {e}"

        cursor.execute("SELECT * FROM devices WHERE device_id = 'knx_test_light'")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "Test Light Zone"
        assert row[2] == "Kitchen"
        assert row[3] == "light"
        assert row[4] == "1/1/10"
        assert row[5] == "1/1/11"

        conn.close()
        tools.apply_device_proposal.DB_PATH = original_db


def test_apply_api_endpoint_validation():
    from fastapi.testclient import TestClient
    import app as app_module

    app_module.app.dependency_overrides[app_module.auth_utils.oauth2_scheme] = lambda: "dummy_token"
    app_module.app.dependency_overrides[app_module.auth_utils.get_current_user] = lambda: {"username": "admin", "role": "Admin"}
    app_module.app.dependency_overrides[app_module.auth_utils.require_admin] = lambda: {"username": "admin", "role": "Admin"}
    client = TestClient(app_module.app)

    # 1. Path outside review directory
    res = client.post("/api/device-proposals/apply", json={
        "proposal_path": "/etc/passwd",
        "confirm": False
    }, headers={"X-API-KEY": "knx-secret-key-123", "Authorization": "Bearer dummy"})
    assert res.status_code == 200
    assert res.json()["status"] == "error"
    assert "Access denied" in res.json()["message"]

    # 2. Path inside review directory but doesn't exist
    res = client.post("/api/device-proposals/apply", json={
        "proposal_path": "~/.openclaw/workspace/knowledge/review/non_existent.json",
        "confirm": False
    }, headers={"X-API-KEY": "knx-secret-key-123", "Authorization": "Bearer dummy"})
    assert res.status_code == 200
    assert res.json()["status"] == "error"
    assert "Invalid proposal file" in res.json()["message"]

    app_module.app.dependency_overrides.clear()
