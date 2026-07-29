import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from services.zalouser_service import ZaloUserService


def make_service(tmp_path, runner=None):
    openclaw_dir = tmp_path / ".openclaw"
    openclaw_dir.mkdir()
    (openclaw_dir / "openclaw.json").write_text(
        json.dumps(
            {
                "channels": {
                    "zalouser": {
                        "enabled": True,
                        "groupPolicy": "allowlist",
                    }
                },
                "plugins": {"entries": {"zalouser": {"enabled": True}}},
            }
        ),
        encoding="utf-8",
    )
    return ZaloUserService(
        openclaw_dir=openclaw_dir,
        project_root=tmp_path,
        runner=runner or (lambda *args, **kwargs: None),
    )


def test_status_does_not_expose_credentials(tmp_path):
    service = make_service(tmp_path)
    credentials = service.credentials_path
    credentials.parent.mkdir(parents=True)
    credentials.write_text(
        json.dumps({"cookie": "private-cookie", "imei": "private-imei"}),
        encoding="utf-8",
    )

    status = service.get_status()

    assert status["credential_present"] is True
    serialized = json.dumps(status)
    assert "private-cookie" not in serialized
    assert "private-imei" not in serialized


def test_update_config_uses_stable_group_ids(tmp_path):
    service = make_service(tmp_path)

    result = service.update_config(
        enabled=True,
        group_policy="allowlist",
        group_ids=["group-2", "group-1", "group-1"],
        history_limit=75,
        require_mention=False,
    )

    config = json.loads(service.config_path.read_text(encoding="utf-8"))
    channel = config["channels"]["zalouser"]
    assert sorted(channel["groups"]) == ["group-1", "group-2"]
    assert channel["groups"]["group-1"]["requireMention"] is False
    assert channel["historyLimit"] == 75
    assert result["restart_required"] is True


def test_probe_returns_only_safe_runtime_fields(tmp_path):
    payload = {
        "channelAccounts": {
            "zalouser": [
                {
                    "configured": True,
                    "running": True,
                    "lastError": None,
                    "secret": "must-not-leak",
                }
            ]
        }
    }

    def runner(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    service = make_service(tmp_path, runner=runner)
    result = service.probe()

    assert result == {
        "attempted": True,
        "ok": True,
        "running": True,
        "configured": True,
        "error": "",
    }
    assert "must-not-leak" not in json.dumps(result)


def test_list_groups_normalizes_cli_output(tmp_path):
    def runner(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                [
                    {"id": "group-1", "name": "Family"},
                    {"groupId": "group-2", "displayName": "Work"},
                ]
            ),
            stderr="",
        )

    service = make_service(tmp_path, runner=runner)

    assert service.list_groups() == [
        {"id": "group-1", "name": "Family"},
        {"id": "group-2", "name": "Work"},
    ]


def test_login_output_exposes_qr_as_data_url(tmp_path):
    service = make_service(tmp_path)
    qr_path = tmp_path / "zalouser-login.png"
    qr_path.write_bytes(b"\x89PNG\r\n\x1a\nqr-test")
    process = SimpleNamespace(
        stdout=StringIO(f"Scan QR image: {qr_path}\n"),
        wait=lambda: 1,
    )

    service._read_login_output(process)

    state = service._login_public_state()
    assert state["state"] == "waiting_scan"
    assert state["qr_data_url"].startswith("data:image/png;base64,")
