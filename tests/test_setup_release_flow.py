import json
import sqlite3

from fastapi.testclient import TestClient

import app as app_module
from services.config_service import ConfigService
from services.openclaw_config_service import OpenClawConfigService


def test_setup_wizard_end_to_end_without_external_side_effects(tmp_path, monkeypatch):
    config_service = ConfigService(
        config_path=tmp_path / "config.json",
        env_path=tmp_path / ".env",
    )
    openclaw_dir = tmp_path / ".openclaw"
    workspace = openclaw_dir / "workspace"
    (tmp_path / "skills").mkdir()
    openclaw_dir.mkdir()
    (openclaw_dir / "openclaw.json").write_text(
        json.dumps({
            "agents": {"defaults": {"workspace": str(workspace), "model": ""}},
            "models": {"providers": {}},
            "channels": {},
            "skills": {"entries": {}},
        }),
        encoding="utf-8",
    )
    openclaw_service = OpenClawConfigService(
        openclaw_dir=openclaw_dir,
        project_root=tmp_path,
    )
    database = tmp_path / "smarthome.db"
    with sqlite3.connect(database) as conn:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )

    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "config_service", config_service)
    monkeypatch.setattr(
        app_module, "openclaw_config_service", openclaw_service
    )
    monkeypatch.setenv("SETUP_BOOTSTRAP_TOKEN", "release-bootstrap-token")
    monkeypatch.setenv("API_KEY", "release-test-internal-api-key")

    try:
        client = TestClient(app_module.app)
        headers = {
            "X-Setup-Token": "release-bootstrap-token",
            "X-API-KEY": "release-test-internal-api-key",
        }
        admin = client.post(
            "/api/setup/bootstrap-admin",
            json={
                "username": "release-admin",
                "password": "ReleaseTestPassword123!",
            },
            headers=headers,
        )
        assert admin.status_code == 200

        categories = {
            "system": {
                "installation_name": "Release Test Home",
                "timezone": "Asia/Ho_Chi_Minh",
                "language": "vi",
            },
            "knx": {
                "gateway_host": "127.0.0.1",
                "gateway_port": 3671,
                "connection_type": "TUNNELING",
                "individual_address": "1.1.250",
            },
            "ai": {
                "provider": "release-provider",
                "model": "release-model",
                "base_url": "https://example.test/v1",
                "api_key": "release-test-api-key",
            },
            "telegram": {
                "enabled": False,
                "bot_token": "123456789:RELEASE_TEST_TOKEN",
                "chat_id": "release-chat",
                "allow_from": ["release-owner"],
            },
            "zalo": {
                "enabled": False,
                "bot_token": "release-zalo-token",
                "webhook_url": "https://example.test/zalo",
                "webhook_secret": "release-zalo-secret",
                "allow_from": ["release-owner"],
            },
            "remote_access": {
                "tailscale_enabled": False,
                "tailscale_hostname": "release-test",
            },
        }
        for category, payload in categories.items():
            response = client.post(
                f"/api/setup/{category}", json=payload, headers=headers
            )
            assert response.status_code == 200, response.text

        provider = client.put(
            "/api/setup/ai/providers/release-provider",
            json={
                "display_name": "Release Provider",
                "api_type": "openai_compatible",
                "base_url": "https://example.test/v1",
                "models": [{"id": "release-model"}],
                "default_model": "release-model",
                "timeout_seconds": 30,
                "api_key": "release-provider-secret",
            },
            headers=headers,
        )
        assert provider.status_code == 200
        assert "release-provider-secret" not in provider.text

        skill = client.put(
            "/api/setup/openclaw/skill-credentials/release-skill/apiKey",
            json={"value": "release-skill-secret"},
            headers=headers,
        )
        assert skill.status_code == 200
        assert "release-skill-secret" not in skill.text

        assert client.post(
            "/api/setup/test/ai",
            json={
                "provider": "release-provider",
                "base_url": "https://example.test/v1",
                "api_key": "",
            },
            headers=headers,
        ).json()["ok"]
        assert client.post(
            "/api/setup/test/telegram",
            json={"bot_token": "123456789:RELEASE_TEST_TOKEN"},
            headers=headers,
        ).json()["ok"]
        assert client.post(
            "/api/setup/test/zalo",
            json={"webhook_url": "https://example.test/zalo"},
            headers=headers,
        ).json()["ok"]

        complete = client.post("/api/setup/complete", headers=headers)
        assert complete.status_code == 200, complete.text

        public = config_service.get_public_config()
        assert public["system"]["setup_complete"] is True
        assert public["telegram"]["bot_token"]["configured"] is True
        assert public["zalo"]["webhook_secret"]["configured"] is True
        serialized = json.dumps(public)
        assert "release-test-api-key" not in serialized
        assert "release-zalo-secret" not in serialized
    finally:
        app_module.app.dependency_overrides.clear()
