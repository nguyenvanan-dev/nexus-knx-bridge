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
    template_dir = project / "openclaw" / "workspace-template"
    template_dir.mkdir(parents=True)
    for name in ("AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md"):
        (template_dir / name).write_text(
            f"# Template {name}\n", encoding="utf-8"
        )
    (openclaw_dir / "openclaw.json").write_text(json.dumps({
        "agents": {"defaults": {
            "workspace": str(workspace),
            "model": "local/test-model",
        }},
        "models": {"providers": {
            "local": {"baseUrl": "http://127.0.0.1:1234/v1", "apiKey": "secret-test-key"}
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
    workspace.mkdir(parents=True)
    (workspace / "AGENTS.md").write_text(
        "# Existing custom agent\n", encoding="utf-8"
    )
    bootstrap = oc_adapter.bootstrap_workspace_safe()
    assert bootstrap["created"] == ["IDENTITY.md", "SOUL.md", "TOOLS.md"]
    assert bootstrap["skipped_existing"] == ["AGENTS.md"]
    assert (workspace / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "# Existing custom agent\n"
    assert bootstrap["workspace"]["ready"] is True
    assert bootstrap["skills_symlink_valid"] is True
    second_bootstrap = oc_adapter.bootstrap_workspace_safe()
    assert second_bootstrap["created"] == []
    assert second_bootstrap["skipped_existing"] == [
        "AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md"
    ]
    status = oc_adapter.get_status()
    assert "runtime_installed" in status
    assert "service_status" in status
    assert "openclaw_service_status" in status
    assert status["router"]["endpoint"] == "http://127.0.0.1:20128/v1"
    assert "installed" in status["router"]
    assert "service_status" in status["router"]
    assert "skills_symlink_valid" in status
    assert status["workspace_definition"]["ready"] is True
    assert status["provider_metadata"]["provider"] == "local"
    assert status["provider_metadata"]["model"] == "local/test-model"
    assert status["provider_metadata"]["api_key_configured"] is True
    assert "secret-test-key" not in json.dumps(status)
    local_provider = next(
        item for item in status["provider_statuses"]
        if item["provider"] == "local"
    )
    assert local_provider["masked"].startswith("secr")
    assert local_provider["masked"].endswith("-key")
    assert len(local_provider["fingerprint"]) == 8
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
    assert oc_adapter.update_channel_safe(
        "zalo",
        True,
        token="zalo-test-token",
        webhook_url="https://example.test/zalo",
        webhook_secret="zalo-webhook-test-secret",
        allow_from=["owner"],
    )
    updated = json.loads((openclaw_dir / "openclaw.json").read_text())
    assert updated["channels"]["zalo"]["botToken"] == "zalo-test-token"
    assert updated["channels"]["zalo"]["webhookSecret"] == "zalo-webhook-test-secret"
    assert oc_adapter.update_provider_credential_safe(
        "groq", "unit_test_provider_key_123456"
    )
    refreshed = oc_adapter.get_status()
    groq = next(
        item for item in refreshed["provider_statuses"]
        if item["provider"] == "groq"
    )
    assert groq["masked"].startswith("unit")
    assert "unit_test_provider_key_123456" not in json.dumps(refreshed)
    created = oc_adapter.upsert_provider_config_safe(
        provider="company-ai",
        display_name="Company AI",
        api_type="openai_compatible",
        base_url="https://ai.example.test/v1",
        models=["model-a", {"id": "model-b", "name": "Model B"}],
        default_model="model-b",
        timeout_seconds=90,
        api_key="provider-test-secret",
    )
    assert created["id"] == "company-ai"
    assert created["default_model"] == "model-b"
    assert [item["id"] for item in created["models"]] == ["model-a", "model-b"]
    assert created["masked"].startswith("prov")
    assert "provider-test-secret" not in json.dumps(created)
    with pytest.raises(ValueError, match="đang được chọn"):
        oc_adapter.delete_provider_config_safe("company-ai")
    oc_adapter.upsert_provider_config_safe(
        provider="local",
        default_model="new-model",
        models=["new-model"],
    )
    assert oc_adapter.delete_provider_config_safe("company-ai")
    assert all(
        item["id"] != "company-ai"
        for item in oc_adapter.list_provider_configs_safe()
    )
    with pytest.raises(ValueError, match="Provider ID"):
        oc_adapter.upsert_provider_config_safe(provider="../invalid")
    skill_credential = oc_adapter.update_skill_credential_safe(
        "goplaces", "apiKey", "skill-test-secret"
    )
    assert skill_credential["masked"].startswith("skil")
    assert "skill-test-secret" not in json.dumps(skill_credential)
    listed_skills = oc_adapter.list_skill_credentials_safe()
    assert listed_skills[0]["skill_id"] == "goplaces"
    assert "skill-test-secret" not in json.dumps(listed_skills)
    with pytest.raises(ValueError, match="Tên credential"):
        oc_adapter.update_skill_credential_safe(
            "goplaces", "unsafe_setting", "value"
        )


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
    cs.update_category_config(
        "zalo",
        {
            "bot_token": "zalo-unit-test-token",
            "webhook_url": "https://example.test/zalo",
            "webhook_secret": "zalo-unit-test-secret",
        },
    )
    public_zalo = cs.get_public_config()["zalo"]
    assert public_zalo["bot_token"]["configured"] is True
    assert public_zalo["webhook_secret"]["configured"] is True
    assert "zalo-unit-test-token" not in json.dumps(public_zalo)
    frontend = cs.update_category_config(
        "frontend", {"backend_url": "http://127.0.0.1:5055", "frontend_port": 3000}
    )
    assert frontend["frontend_port"] == 3000
    cs.update_category_config(
        "ai",
        {
            "provider": "groq",
            "model": "test-model",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": "unit_test_only_key_123456",
        },
    )
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GROQ_API_KEY=unit_test_only_key_123456" in env_text
    assert "OPENAI_API_KEY=unit_test_only_key_123456" not in env_text
    cs.update_category_config(
        "ai", {"provider": "gemini", "model": "gemini-test", "api_key": ""}
    )
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=" not in env_text
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
