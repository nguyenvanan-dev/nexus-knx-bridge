import json
import hashlib
import os
import shutil
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Any, Dict, Optional

HOME_DIR = Path.home()
OPENCLAW_DIR = HOME_DIR / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class OpenClawConfigService:
    def __init__(
        self,
        openclaw_dir: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        self.openclaw_dir = Path(openclaw_dir or OPENCLAW_DIR)
        self.home_dir = self.openclaw_dir.parent
        self.config_path = self.openclaw_dir / "openclaw.json"
        self.credentials_dir = self.openclaw_dir / "credentials"
        self.project_root = Path(project_root or PROJECT_ROOT)

    @staticmethod
    def _service_state(name: str) -> str:
        for command in (
            ["systemctl", "--user", "is-active", name],
            ["systemctl", "is-active", name],
        ):
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=2
                )
                state = result.stdout.strip()
                if result.returncode == 0:
                    return state or "active"
            except Exception:
                continue
        if name == "9router.service":
            try:
                process = subprocess.run(
                    ["pgrep", "-f", "(^|/)9router( |$)"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if process.returncode == 0 and process.stdout.strip():
                    return "active (process)"
            except Exception:
                pass
        return "inactive"

    def _load_config(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _pairing_status(self, channel: str, channel_config: Dict[str, Any]) -> Dict[str, Any]:
        allow_from = channel_config.get("allowFrom") or channel_config.get("groupAllowFrom") or []
        allow_count = len(allow_from) if isinstance(allow_from, list) else 0
        pairing_file = self.credentials_dir / f"{channel}-pairing.json"
        pending = 0
        if pairing_file.exists():
            try:
                pairing = json.loads(pairing_file.read_text(encoding="utf-8"))
                requests = pairing.get("requests", []) if isinstance(pairing, dict) else []
                pending = len(requests) if isinstance(requests, list) else 0
            except Exception:
                pass
        return {
            "configured": bool(channel_config),
            "enabled": bool(channel_config.get("enabled", channel == "telegram")),
            "token_configured": bool(channel_config.get("botToken")),
            "allow_count": allow_count,
            "pending_pairing_requests": pending,
            "credentials_file_present": pairing_file.exists(),
        }

    @staticmethod
    def _credential_identity(value: Any) -> Dict[str, Any]:
        secret = str(value or "")
        if not secret:
            return {
                "configured": False,
                "masked": "",
                "fingerprint": "",
            }
        prefix = secret[:4]
        suffix = secret[-4:] if len(secret) > 8 else ""
        return {
            "configured": True,
            "masked": f"{prefix}{'•' * 12}{suffix}",
            "fingerprint": hashlib.sha256(secret.encode()).hexdigest()[:8],
        }

    def get_status(self) -> Dict[str, Any]:
        executable = shutil.which("openclaw") or shutil.which("9router")
        config = self._load_config()
        workspace = Path(
            config.get("agents", {}).get("defaults", {}).get(
                "workspace", self.openclaw_dir / "workspace"
            )
        ).expanduser()
        skills_target = workspace / "skills"
        symlink_valid = False
        if skills_target.is_symlink():
            try:
                symlink_valid = (
                    skills_target.resolve() == (self.project_root / "skills").resolve()
                )
            except Exception:
                pass

        model_ref = str(
            config.get("agents", {}).get("defaults", {}).get("model", "")
        )
        provider = model_ref.split("/", 1)[0] if "/" in model_ref else ""
        provider_config = config.get("models", {}).get("providers", {}).get(provider, {})
        provider_statuses = []
        providers = config.get("models", {}).get("providers", {})
        if isinstance(providers, dict):
            for provider_name, details in sorted(providers.items()):
                details = details if isinstance(details, dict) else {}
                identity = self._credential_identity(details.get("apiKey"))
                provider_statuses.append({
                    "provider": provider_name,
                    "source": "~/.openclaw/openclaw.json",
                    "active": provider_name == provider,
                    "base_url_configured": bool(details.get("baseUrl")),
                    "models": [
                        str(item.get("id") or item.get("name") or "")
                        for item in details.get("models", [])
                        if isinstance(item, dict)
                    ],
                    **identity,
                })
        channels = config.get("channels", {})

        return {
            "runtime_installed": executable is not None,
            "executable_path": executable or "",
            "service_status": self._service_state("9router.service"),
            "workspace_path": str(workspace),
            "workspace_exists": workspace.exists(),
            "skills_symlink_valid": symlink_valid,
            "config_present": self.config_path.exists(),
            "provider_metadata": {
                "provider": provider or "none",
                "model": model_ref or "none",
                "configured": bool(model_ref),
                "base_url_configured": bool(
                    provider_config.get("baseUrl")
                    if isinstance(provider_config, dict)
                    else False
                ),
                "api_key_configured": bool(
                    provider_config.get("apiKey")
                    if isinstance(provider_config, dict)
                    else False
                ),
            },
            "provider_statuses": provider_statuses,
            "telegram_pairing": self._pairing_status(
                "telegram", channels.get("telegram", {})
            ),
            "zalo_pairing": self._pairing_status("zalo", channels.get("zalo", {})),
        }

    def ensure_skills_symlink(self) -> bool:
        workspace = Path(
            self._load_config()
            .get("agents", {})
            .get("defaults", {})
            .get("workspace", self.openclaw_dir / "workspace")
        ).expanduser()
        workspace_skills = workspace / "skills"
        repo_skills = self.project_root / "skills"
        if not repo_skills.exists():
            return False
        workspace.mkdir(parents=True, exist_ok=True)
        if workspace_skills.is_symlink():
            if workspace_skills.resolve() == repo_skills.resolve():
                return True
            workspace_skills.unlink()
        elif workspace_skills.exists():
            return False
        workspace_skills.symlink_to(repo_skills, target_is_directory=True)
        return True

    def update_runtime_safe(
        self,
        provider: str = "",
        model: str = "",
        base_url: str = "",
        workspace_path: str = "",
    ) -> bool:
        if not self.config_path.exists():
            return False
        config = self._load_config()
        if not config:
            return False
        defaults = config.setdefault("agents", {}).setdefault("defaults", {})
        if model:
            defaults["model"] = model if "/" in model or not provider else f"{provider}/{model}"
        if workspace_path:
            workspace = Path(workspace_path).expanduser().resolve()
            if self.home_dir not in workspace.parents and workspace != self.home_dir:
                return False
            defaults["workspace"] = str(workspace)
        if provider and base_url:
            providers = config.setdefault("models", {}).setdefault("providers", {})
            providers.setdefault(provider, {})["baseUrl"] = base_url

        self.openclaw_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.openclaw_dir / "openclaw.json.bak"
        shutil.copy2(self.config_path, backup_path)
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.openclaw_dir), prefix=".openclaw_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.config_path)
            os.chmod(self.config_path, 0o600)
            return True
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def update_provider_safe(self, provider: str, model: str) -> bool:
        return self.update_runtime_safe(provider=provider, model=model)

    def update_provider_credential_safe(
        self,
        provider: str,
        api_key: str,
        clear: bool = False,
    ) -> bool:
        provider = str(provider).strip().lower()
        if not provider or not self.config_path.exists():
            return False
        config = self._load_config()
        target = config.setdefault("models", {}).setdefault(
            "providers", {}
        ).setdefault(provider, {})
        if clear:
            target.pop("apiKey", None)
        elif api_key:
            target["apiKey"] = api_key
        else:
            return True
        self._atomic_write_config(config)
        return True

    @staticmethod
    def _provider_slug(value: str) -> str:
        slug = str(value or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", slug):
            raise ValueError(
                "Provider ID chỉ được chứa chữ thường, số, dấu chấm, gạch dưới hoặc gạch ngang."
            )
        return slug

    def list_provider_configs_safe(self) -> list:
        config = self._load_config()
        active_model = str(
            config.get("agents", {}).get("defaults", {}).get("model", "")
        )
        active_provider = active_model.split("/", 1)[0] if "/" in active_model else ""
        providers = config.get("models", {}).get("providers", {})
        if not isinstance(providers, dict):
            return []
        result = []
        for provider, raw in sorted(providers.items()):
            details = raw if isinstance(raw, dict) else {}
            models = []
            for item in details.get("models", []):
                if isinstance(item, str):
                    model_id = item.strip()
                    model_name = model_id
                elif isinstance(item, dict):
                    model_id = str(item.get("id") or item.get("name") or "").strip()
                    model_name = str(item.get("name") or model_id).strip()
                else:
                    continue
                if model_id and model_id not in [model["id"] for model in models]:
                    models.append({"id": model_id, "name": model_name})
            identity = self._credential_identity(details.get("apiKey"))
            result.append({
                "id": provider,
                "display_name": str(details.get("displayName") or provider),
                "api_type": str(details.get("apiType") or "openai_compatible"),
                "base_url": str(details.get("baseUrl") or ""),
                "models": models,
                "default_model": (
                    active_model.split("/", 1)[1]
                    if provider == active_provider and "/" in active_model
                    else ""
                ),
                "timeout_seconds": int(details.get("timeoutSeconds") or 60),
                "active": provider == active_provider,
                "source": "~/.openclaw/openclaw.json",
                **identity,
            })
        return result

    def upsert_provider_config_safe(
        self,
        provider: str,
        display_name: str = "",
        api_type: str = "openai_compatible",
        base_url: str = "",
        models: Optional[list] = None,
        default_model: str = "",
        timeout_seconds: int = 60,
        api_key: str = "",
        clear_api_key: bool = False,
    ) -> Dict[str, Any]:
        provider = self._provider_slug(provider)
        if api_type not in {"openai_compatible", "anthropic", "google", "local"}:
            raise ValueError("Kiểu API provider không hợp lệ.")
        if base_url and not str(base_url).startswith(("http://", "https://")):
            raise ValueError("Base URL phải bắt đầu bằng http:// hoặc https://.")
        try:
            timeout_seconds = int(timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Timeout phải là số nguyên.") from exc
        if not 1 <= timeout_seconds <= 600:
            raise ValueError("Timeout phải từ 1 đến 600 giây.")

        normalized_models = []
        for item in models or []:
            if isinstance(item, str):
                model_id = item.strip()
                model_name = model_id
            elif isinstance(item, dict):
                model_id = str(item.get("id") or "").strip()
                model_name = str(item.get("name") or model_id).strip()
            else:
                continue
            if not model_id or len(model_id) > 200:
                continue
            if model_id not in [model["id"] for model in normalized_models]:
                normalized_models.append({"id": model_id, "name": model_name})
        if default_model and default_model not in {
            model["id"] for model in normalized_models
        }:
            normalized_models.append({"id": default_model, "name": default_model})

        config = self._load_config()
        providers = config.setdefault("models", {}).setdefault("providers", {})
        target = providers.setdefault(provider, {})
        target.update({
            "displayName": str(display_name or provider).strip(),
            "apiType": api_type,
            "baseUrl": str(base_url).strip(),
            "models": normalized_models,
            "timeoutSeconds": timeout_seconds,
        })
        if clear_api_key:
            target.pop("apiKey", None)
        elif api_key:
            target["apiKey"] = str(api_key).strip()
        if default_model:
            config.setdefault("agents", {}).setdefault("defaults", {})[
                "model"
            ] = f"{provider}/{default_model}"
        self._atomic_write_config(config)
        return next(
            item for item in self.list_provider_configs_safe()
            if item["id"] == provider
        )

    def delete_provider_config_safe(self, provider: str) -> bool:
        provider = self._provider_slug(provider)
        config = self._load_config()
        providers = config.get("models", {}).get("providers", {})
        if not isinstance(providers, dict) or provider not in providers:
            return False
        active_model = str(
            config.get("agents", {}).get("defaults", {}).get("model", "")
        )
        if active_model.startswith(f"{provider}/"):
            raise ValueError("Không thể xóa provider đang được chọn làm mặc định.")
        del providers[provider]
        self._atomic_write_config(config)
        return True

    def _atomic_write_config(self, config: Dict[str, Any]) -> None:
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.openclaw_dir), prefix=".openclaw_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            shutil.copy2(self.config_path, self.openclaw_dir / "openclaw.json.bak")
            os.replace(temp_path, self.config_path)
            os.chmod(self.config_path, 0o600)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def update_channel_safe(
        self,
        channel: str,
        enabled: bool,
        token: str = "",
        webhook_url: str = "",
        webhook_secret: str = "",
        allow_from: Optional[list] = None,
    ) -> bool:
        if channel not in {"telegram", "zalo"} or not self.config_path.exists():
            return False
        config = self._load_config()
        target = config.setdefault("channels", {}).setdefault(channel, {})
        target["enabled"] = bool(enabled)
        if token:
            target["botToken"] = token
        if webhook_url:
            target["webhookUrl"] = webhook_url
        if webhook_secret:
            target["webhookSecret"] = webhook_secret
        if allow_from is not None:
            target["allowFrom"] = list(allow_from)
            target["groupAllowFrom"] = list(allow_from)
        plugins = config.setdefault("plugins", {}).setdefault("entries", {})
        plugins.setdefault(channel, {})["enabled"] = bool(enabled)

        fd, temp_path = tempfile.mkstemp(
            dir=str(self.openclaw_dir), prefix=".openclaw_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            shutil.copy2(self.config_path, self.openclaw_dir / "openclaw.json.bak")
            os.replace(temp_path, self.config_path)
            os.chmod(self.config_path, 0o600)
            return True
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise


openclaw_config_service = OpenClawConfigService()
