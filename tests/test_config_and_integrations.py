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
    assert (tmp_path / "test_config.json.bak").exists()

def test_openclaw_adapter(tmp_path):
    openclaw_dir = tmp_path / ".openclaw"
    workspace = openclaw_dir / "workspace"
    credentials = openclaw_dir / "credentials"
    project = tmp_path / "project"
    credentials.mkdir(parents=True)
    (project / "skills").mkdir(parents=True)
    (openclaw_dir / "openclaw.json").write_text(json.dumps({
        "agents": {"defaults": {
            "workspace": str(workspace),
            "model": "local/test-model",
        }},
        "models": {"providers": {
            "local": {"baseUrl": "http://127.0.0.1:1234/v1", "apiKey": "secret"}
        }},
        "channels": {
            "telegram": {"botToken": "secret", "allowFrom": ["owner"]}
        },
    }), encoding="utf-8")
    (credentials / "telegram-pairing.json").write_text(
        json.dumps({"requests": [{"id": "pending"}]}), encoding="utf-8"
    )
    oc_adapter = OpenClawConfigService(
        openclaw_dir=openclaw_dir,
        project_root=project,
    )
    status = oc_adapter.get_status()
    assert "runtime_installed" in status
    assert "service_status" in status
    assert "skills_symlink_valid" in status
    assert status["provider_metadata"]["provider"] == "local"
    assert status["provider_metadata"]["model"] == "local/test-model"
    assert status["provider_metadata"]["api_key_configured"] is True
    assert "secret" not in json.dumps(status)
    assert status["telegram_pairing"]["pending_pairing_requests"] == 1
    assert oc_adapter.update_runtime_safe(
        provider="local",
        model="new-model",
        workspace_path=str(workspace),
    )
    assert oc_adapter.ensure_skills_symlink()
    assert oc_adapter.update_channel_safe(
        "telegram", True, allow_from=["owner", "family"]
    )
    updated = json.loads((openclaw_dir / "openclaw.json").read_text())
    assert updated["agents"]["defaults"]["model"] == "local/new-model"
    assert updated["channels"]["telegram"]["allowFrom"] == ["owner", "family"]


def test_extended_setup_schema(tmp_path):
    cs = ConfigService(
        config_path=tmp_path / "config.json",
        env_path=tmp_path / ".env",
    )
    telegram = cs.update_category_config(
        "telegram", {"allow_from": "100, 200,100"}
    )
    assert telegram["allow_from"] == ["100", "200"]
    remote = cs.update_category_config(
        "remote_access", {"tailscale_enabled": True}
    )
    assert remote["tailscale_enabled"] is True
    frontend = cs.update_category_config(
        "frontend", {"backend_url": "http://127.0.0.1:5055", "frontend_port": 3000}
    )
    assert frontend["frontend_port"] == 3000
    runtime = tmp_path / "openclaw"
    runtime.write_text("#!/bin/sh\n", encoding="utf-8")
    runtime.chmod(0o700)
    openclaw = cs.update_category_config(
        "openclaw",
        {
            "runtime_path": str(runtime),
            "workspace_path": str(Path.home() / ".openclaw-test-workspace"),
        },
    )
    assert openclaw["runtime_path"] == str(runtime)
    with pytest.raises(ValueError, match="file thực thi"):
        cs.update_category_config(
            "openclaw", {"runtime_path": str(tmp_path / "missing")}
        )

def test_security_fail_closed():
    if API_KEY is not None:
        assert len(API_KEY) > 10
        assert API_KEY not in ["knx-secret-key-123", "secret", "change_me", "admin"]
    else:
        assert API_KEY is None
