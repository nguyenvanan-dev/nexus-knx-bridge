from fastapi.testclient import TestClient

import app as app_module


class FakeZaloUserService:
    def __init__(self):
        self.saved = None
        self.logout_called = False

    def get_status(self, probe=False):
        return {
            "enabled": True,
            "credential_present": True,
            "groups": [{"id": "group-1", "require_mention": True}],
            "login": {"state": "idle", "qr_data_url": ""},
            "probe": {
                "attempted": probe,
                "ok": True if probe else None,
                "running": True if probe else None,
                "error": "",
            },
        }

    def list_groups(self, query="", limit=100):
        return [{"id": "group-1", "name": "Family"}]

    def update_config(self, **kwargs):
        self.saved = kwargs
        return {"restart_required": True, "group_count": len(kwargs["group_ids"])}

    def start_login(self):
        return {"state": "waiting_scan", "qr_data_url": "data:image/png;base64,test"}

    def logout(self):
        self.logout_called = True
        return {"ok": True, "message": "logged out"}


def test_zalouser_setup_endpoints_are_guarded_and_safe(monkeypatch):
    fake = FakeZaloUserService()
    monkeypatch.setenv("API_KEY", "zalouser-test-api-key")
    monkeypatch.setattr(app_module, "zalouser_service", fake)
    app_module.app.dependency_overrides[app_module.require_setup_access] = (
        lambda: {"username": "test-admin", "role": "Admin"}
    )
    try:
        client = TestClient(app_module.app)
        headers = {"X-API-KEY": "zalouser-test-api-key"}

        status = client.get("/api/setup/zalouser/status?probe=true")
        assert status.status_code == 200
        assert status.json()["probe"]["running"] is True

        groups = client.get("/api/setup/zalouser/groups?limit=20")
        assert groups.status_code == 200
        assert groups.json()["groups"][0]["id"] == "group-1"

        saved = client.post(
            "/api/setup/zalouser/config",
            headers=headers,
            json={
                "enabled": True,
                "group_policy": "allowlist",
                "group_ids": ["group-1"],
                "history_limit": 75,
                "require_mention": True,
            },
        )
        assert saved.status_code == 200
        assert fake.saved["group_ids"] == ["group-1"]

        login = client.post(
            "/api/setup/zalouser/login/start", headers=headers
        )
        assert login.status_code == 200
        assert login.json()["login"]["state"] == "waiting_scan"

        denied_logout = client.post(
            "/api/setup/zalouser/logout",
            json={"confirm": False},
            headers=headers,
        )
        assert denied_logout.status_code == 400
        assert fake.logout_called is False

        logout = client.post(
            "/api/setup/zalouser/logout",
            json={"confirm": True},
            headers=headers,
        )
        assert logout.status_code == 200
        assert fake.logout_called is True
    finally:
        app_module.app.dependency_overrides.clear()
