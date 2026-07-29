import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional


class ZaloUserService:
    def __init__(
        self,
        openclaw_dir: Optional[Path] = None,
        project_root: Optional[Path] = None,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    ):
        self.openclaw_dir = Path(openclaw_dir or Path.home() / ".openclaw")
        self.project_root = Path(
            project_root or Path(__file__).resolve().parent.parent
        )
        self.config_path = self.openclaw_dir / "openclaw.json"
        self.credentials_path = (
            self.openclaw_dir / "credentials" / "zalouser" / "credentials.json"
        )
        self.chat_db_path = self.project_root / "data" / "chat_history.db"
        self.runner = runner
        self.popen_factory = popen_factory
        self._login_lock = threading.Lock()
        self._login_process = None
        self._login_state = {
            "state": "idle",
            "message": "",
            "qr_data_url": "",
            "started_at": None,
        }

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _atomic_write_config(self, config: dict) -> None:
        self.openclaw_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.openclaw_dir / f".openclaw_zalouser_{os.getpid()}.tmp"
        backup_path = self.openclaw_dir / "openclaw.json.bak"
        try:
            if self.config_path.is_file():
                shutil.copy2(self.config_path, backup_path)
                os.chmod(backup_path, 0o600)
            temp_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.config_path)
            os.chmod(self.config_path, 0o600)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _chat_metrics(self) -> dict:
        result = {
            "message_count": 0,
            "group_count": 0,
            "last_message_at": None,
        }
        if not self.chat_db_path.exists():
            return result
        try:
            with sqlite3.connect(str(self.chat_db_path)) as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(*), COUNT(DISTINCT group_id), MAX(timestamp)
                    FROM messages
                    """
                ).fetchone()
            result["message_count"] = int(row[0] or 0)
            result["group_count"] = int(row[1] or 0)
            if row[2]:
                timestamp = float(row[2])
                if timestamp > 10_000_000_000:
                    timestamp /= 1_000_000
                result["last_message_at"] = timestamp
        except (sqlite3.Error, OSError, TypeError, ValueError):
            pass
        return result

    def _login_public_state(self) -> dict:
        with self._login_lock:
            state = dict(self._login_state)
            process = self._login_process
            if process is not None and process.poll() is not None:
                if state["state"] not in {"connected", "error"}:
                    state["state"] = (
                        "connected" if process.returncode == 0 else "error"
                    )
                self._login_process = None
                self._login_state.update(state)
            return state

    def get_status(self, probe: bool = False) -> dict:
        config = self._load_config()
        channel = config.get("channels", {}).get("zalouser", {})
        status = {
            "enabled": bool(channel.get("enabled", False)),
            "credential_present": self.credentials_path.is_file(),
            "credential_updated_at": (
                self.credentials_path.stat().st_mtime
                if self.credentials_path.is_file()
                else None
            ),
            "account_id": str(channel.get("defaultAccount", "default")),
            "group_policy": str(channel.get("groupPolicy", "allowlist")),
            "history_limit": int(channel.get("historyLimit", 50) or 50),
            "groups": [
                {
                    "id": str(group_id),
                    "enabled": bool(group_config.get("enabled", True)),
                    "require_mention": bool(
                        group_config.get("requireMention", True)
                    ),
                }
                for group_id, group_config in channel.get("groups", {}).items()
                if isinstance(group_config, dict)
            ],
            "login": self._login_public_state(),
            **self._chat_metrics(),
        }
        status["probe"] = {
            "attempted": False,
            "ok": None,
            "running": None,
            "error": "",
        }
        if probe:
            status["probe"] = self.probe()
        return status

    def probe(self) -> dict:
        try:
            result = self.runner(
                [
                    "openclaw",
                    "channels",
                    "status",
                    "--channel",
                    "zalouser",
                    "--json",
                    "--timeout",
                    "5000",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode != 0:
                return {
                    "attempted": True,
                    "ok": False,
                    "running": False,
                    "error": "OpenClaw status probe failed.",
                }
            payload = json.loads(result.stdout)
            account_rows = payload.get("channelAccounts", {}).get(
                "zalouser", []
            )
            account = account_rows[0] if account_rows else {}
            running = bool(account.get("running", False))
            configured = bool(account.get("configured", False))
            return {
                "attempted": True,
                "ok": running and configured,
                "running": running,
                "configured": configured,
                "error": str(account.get("lastError") or ""),
            }
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return {
                "attempted": True,
                "ok": False,
                "running": False,
                "error": "Unable to query OpenClaw Zalo Personal status.",
            }

    def list_groups(self, query: str = "", limit: int = 100) -> list[dict]:
        command = [
            "openclaw",
            "directory",
            "groups",
            "list",
            "--channel",
            "zalouser",
            "--account",
            "default",
            "--json",
            "--limit",
            str(max(1, min(int(limit), 200))),
        ]
        if query.strip():
            command.extend(["--query", query.strip()])
        result = self.runner(
            command,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError("Không thể đọc danh sách group từ OpenClaw.")
        payload = json.loads(result.stdout)
        rows = payload if isinstance(payload, list) else payload.get("groups", [])
        groups = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            group_id = row.get("id") or row.get("groupId") or row.get("threadId")
            if not group_id:
                continue
            groups.append(
                {
                    "id": str(group_id),
                    "name": str(
                        row.get("name") or row.get("displayName") or group_id
                    ),
                }
            )
        return groups

    def update_config(
        self,
        enabled: bool,
        group_policy: str,
        group_ids: list[str],
        history_limit: int,
        require_mention: bool,
    ) -> dict:
        if group_policy not in {"allowlist", "open", "disabled"}:
            raise ValueError("Group policy không hợp lệ.")
        history_limit = max(0, min(int(history_limit), 500))
        clean_ids = sorted(
            {
                str(group_id).strip()
                for group_id in group_ids
                if str(group_id).strip()
            }
        )
        config = self._load_config()
        if not config:
            raise RuntimeError("OpenClaw config không tồn tại hoặc không hợp lệ.")
        channel = config.setdefault("channels", {}).setdefault("zalouser", {})
        channel["enabled"] = bool(enabled)
        channel["groupPolicy"] = group_policy
        channel["historyLimit"] = history_limit
        channel["groups"] = {
            group_id: {
                "enabled": True,
                "requireMention": bool(require_mention),
            }
            for group_id in clean_ids
        }
        config.setdefault("plugins", {}).setdefault("entries", {}).setdefault(
            "zalouser", {}
        )["enabled"] = bool(enabled)
        self._atomic_write_config(config)
        return {
            "enabled": bool(enabled),
            "group_policy": group_policy,
            "history_limit": history_limit,
            "group_count": len(clean_ids),
            "restart_required": True,
        }

    def _read_login_output(self, process) -> None:
        qr_pattern = re.compile(r"Scan QR image:\s*(.+)$")
        messages = []
        try:
            for raw_line in iter(process.stdout.readline, ""):
                line = raw_line.strip()
                if not line:
                    continue
                messages.append(line)
                match = qr_pattern.search(line)
                if match:
                    qr_path = Path(match.group(1).strip().strip("'\""))
                    if qr_path.is_file():
                        encoded = base64.b64encode(qr_path.read_bytes()).decode()
                        with self._login_lock:
                            self._login_state.update(
                                {
                                    "state": "waiting_scan",
                                    "message": "Quét QR bằng ứng dụng Zalo.",
                                    "qr_data_url": (
                                        f"data:image/png;base64,{encoded}"
                                    ),
                                }
                            )
            return_code = process.wait()
            with self._login_lock:
                if return_code == 0:
                    self._login_state.update(
                        {
                            "state": "connected",
                            "message": "Đăng nhập Zalo Personal thành công.",
                            "qr_data_url": "",
                        }
                    )
                elif self._login_state["state"] != "waiting_scan":
                    self._login_state.update(
                        {
                            "state": "error",
                            "message": (
                                messages[-1]
                                if messages
                                else "Đăng nhập Zalo Personal thất bại."
                            ),
                            "qr_data_url": "",
                        }
                    )
        except Exception:
            with self._login_lock:
                self._login_state.update(
                    {
                        "state": "error",
                        "message": "Không thể xử lý phiên đăng nhập Zalo.",
                        "qr_data_url": "",
                    }
                )

    def start_login(self) -> dict:
        with self._login_lock:
            if self._login_process and self._login_process.poll() is None:
                return dict(self._login_state)
            self._login_state = {
                "state": "starting",
                "message": "Đang tạo QR đăng nhập...",
                "qr_data_url": "",
                "started_at": time.time(),
            }
            process = self.popen_factory(
                [
                    "openclaw",
                    "channels",
                    "login",
                    "--channel",
                    "zalouser",
                    "--account",
                    "default",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._login_process = process
        thread = threading.Thread(
            target=self._read_login_output,
            args=(process,),
            daemon=True,
        )
        thread.start()
        return self._login_public_state()

    def logout(self) -> dict:
        result = self.runner(
            [
                "openclaw",
                "channels",
                "logout",
                "--channel",
                "zalouser",
                "--account",
                "default",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError("Không thể đăng xuất Zalo Personal.")
        with self._login_lock:
            self._login_state = {
                "state": "idle",
                "message": "Đã đăng xuất Zalo Personal.",
                "qr_data_url": "",
                "started_at": None,
            }
        return {"ok": True, "message": "Đã đăng xuất Zalo Personal."}


zalouser_service = ZaloUserService()
