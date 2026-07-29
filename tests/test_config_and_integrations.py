import os
import json
import pytest
from pathlib import Path
from services.config_service import ConfigService
from services.openclaw_config_service import OpenClawConfigService
from core.security import APIKeyMiddleware, API_KEY

def test_config_service_baseline_and_masking(tmp_path):
    config_file = tmp_path / "test_config.json"
    env_file = tmp_path / ".env"
    cs = ConfigService(config_path=config_file, env_path=env_file)

    cfg = cs.load_raw_config()
    assert "system" in cfg
    assert "knx" in cfg
    assert cfg["system"]["installation_name"] == "KNX Smart Home"

    # Test Updating Valid Category
    res = cs.update_category_config("knx", {"gateway_host": "192.168.1.100", "gateway_port": 3671})
    assert res["gateway_host"] == "192.168.1.100"
    assert res["gateway_port"] == 3671

    # Test Updating Invalid Key (Schema Protection raises ValueError)
    with pytest.raises(ValueError, match="whitelist"):
        cs.update_category_config("knx", {"malicious_key": "hacked"})

    # Test Secret Masking
    cs.update_category_config("ai", {"api_key": "unit-test-ai-key-not-for-runtime"})
    cs.update_category_config("telegram", {"bot_token": "123456789:UNIT_TEST_TOKEN"})

    pub = cs.get_public_config()
    assert pub["ai"]["api_key"]["configured"] is True
    assert "sk-proj" not in str(pub["ai"]["api_key"])
    assert pub["ai"]["api_key"]["masked_hint"] == ""
    assert pub["telegram"]["bot_token"]["configured"] is True
    env_text = env_file.read_text(encoding="utf-8")
    assert "KNX_GATEWAY_IP=192.168.1.100" in env_text
    assert "OPENAI_API_KEY=unit-test-ai-key-not-for-runtime" in env_text
    assert env_file.stat().st_mode & 0o777 == 0o600

def test_openclaw_adapter(tmp_path):
    oc_adapter = OpenClawConfigService()
    status = oc_adapter.get_status()
    assert "runtime_installed" in status
    assert "service_status" in status
    assert "skills_symlink_valid" in status

def test_security_fail_closed():
    if API_KEY is not None:
        assert len(API_KEY) > 10
        assert API_KEY not in ["knx-secret-key-123", "secret", "change_me", "admin"]
    else:
        assert API_KEY is None
