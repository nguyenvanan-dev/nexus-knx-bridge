import os
import json
import re
import shutil
import tempfile
import urllib.parse
from typing import Dict, Any, Optional

CONFIG_FILE = os.environ.get("CONFIG_FILE_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json"))
CONFIG_BACKUP = f"{CONFIG_FILE}.bak"

RUNTIME_ENV_KEYS = {
    "knx": {
        "gateway_host": "KNX_GATEWAY_IP",
        "gateway_port": "KNX_GATEWAY_PORT",
        "individual_address": "KNX_INDIVIDUAL_ADDRESS",
    },
    "telegram": {
        "bot_token": "TELEGRAM_BOT_TOKEN",
        "chat_id": "TELEGRAM_CHAT_ID",
    },
    "zalo": {
        "bot_token": "ZALO_BOT_TOKEN",
        "webhook_url": "ZALO_WEBHOOK_URL",
        "webhook_secret": "ZALO_WEBHOOK_SECRET",
    },
}

AI_ENV_KEYS = {
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "base_url": "OPENAI_BASE_URL",
        "model": "OPENAI_MODEL",
    },
    "groq": {
        "api_key": "GROQ_API_KEY",
        "base_url": "GROQ_BASE_URL",
        "model": "GROQ_MODEL",
    },
    "gemini": {
        "api_key": "GEMINI_API_KEY",
        "model": "GEMINI_MODEL",
    },
    "google": {
        "api_key": "GOOGLE_API_KEY",
        "model": "GOOGLE_MODEL",
    },
    "9router": {
        "api_key": "NINE_ROUTER_API_KEY",
        "base_url": "NINE_ROUTER_BASE_URL",
        "model": "NINE_ROUTER_MODEL",
    },
}

# Whitelist schema & defaults
DEFAULT_CONFIG = {
    "system": {
        "timezone": "Asia/Ho_Chi_Minh",
        "language": "vi",
        "installation_name": "KNX Smart Home",
        "setup_complete": False
    },
    "knx": {
        "gateway_host": "127.0.0.1",
        "gateway_port": 3671,
        "connection_type": "TUNNELING",
        "individual_address": "1.1.250"
    },
    "ai": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "api_key": ""
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": "",
        "allow_from": []
    },
    "zalo": {
        "enabled": False,
        "bot_token": "",
        "webhook_url": "",
        "webhook_secret": "",
        "integration_mode": "webhook",
        "allow_from": []
    },
    "openclaw": {
        "enabled": False,
        "runtime_path": "",
        "workspace_path": "",
        "provider": "",
        "model": "",
        "base_url": ""
    },
    "remote_access": {
        "tailscale_enabled": False,
        "tailscale_hostname": ""
    },
    "frontend": {
        "backend_url": "http://127.0.0.1:5055",
        "public_host": "",
        "secure_cookies": False,
        "frontend_port": 3000,
        "backend_port": 5055
    }
}

SECRET_FIELDS = {
    "ai": ["api_key"],
    "telegram": ["bot_token"],
    "zalo": ["bot_token", "webhook_url", "webhook_secret"]
}

class ConfigService:
    def __init__(
        self,
        config_path: str = CONFIG_FILE,
        env_path: Optional[str] = None,
    ):
        self.config_path = str(config_path)
        self.env_path = str(
            env_path or os.path.join(os.path.dirname(self.config_path), ".env")
        )
        self.ensure_config_exists()

    def ensure_config_exists(self):
        if not os.path.exists(self.config_path):
            self.save_config(DEFAULT_CONFIG, backup=False)

    def load_raw_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return DEFAULT_CONFIG.copy()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge missing default keys
            merged = DEFAULT_CONFIG.copy()
            for cat, val in data.items():
                if cat in merged and isinstance(val, dict):
                    merged[cat] = {**merged[cat], **val}
                elif cat in merged:
                    merged[cat] = val
            return merged
        except Exception:
            return DEFAULT_CONFIG.copy()

    def get_public_config(self) -> Dict[str, Any]:
        raw = self.load_raw_config()
        public = {}
        for cat, fields in raw.items():
            if not isinstance(fields, dict):
                public[cat] = fields
                continue
            public[cat] = {}
            cat_secrets = SECRET_FIELDS.get(cat, [])
            for key, val in fields.items():
                if key in cat_secrets:
                    val_str = str(val or "")
                    configured = bool(val_str)
                    public[cat][key] = {
                        "configured": configured,
                        "masked_hint": ""
                    }
                else:
                    public[cat][key] = val
        return public

    def validate_category_config(self, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if category not in DEFAULT_CONFIG:
            raise ValueError(f"Category '{category}' không hợp lệ.")

        allowed_keys = set(DEFAULT_CONFIG[category].keys())
        validated = {}

        for k, v in data.items():
            if k not in allowed_keys and k != "clear_secrets":
                raise ValueError(f"Khóa '{k}' không nằm trong whitelist của {category}.")

        # Specific validations
        if category == "knx":
            if "gateway_port" in data:
                try:
                    port = int(data["gateway_port"])
                    if not (1 <= port <= 65535):
                        raise ValueError()
                    validated["gateway_port"] = port
                except Exception:
                    raise ValueError("Port KNX Gateway phải từ 1 đến 65535.")
            if "gateway_host" in data and data["gateway_host"]:
                host = str(data["gateway_host"]).strip()
                validated["gateway_host"] = host
            if "connection_type" in data:
                conn_type = str(data["connection_type"]).upper()
                if conn_type not in ["TUNNELING", "ROUTING", "AUTOMATIC"]:
                    raise ValueError("connection_type phải là TUNNELING, ROUTING hoặc AUTOMATIC.")
                validated["connection_type"] = conn_type

        elif category == "ai":
            if "base_url" in data and data["base_url"]:
                url = str(data["base_url"]).strip()
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise ValueError("base_url AI phải bắt đầu bằng http:// hoặc https://")
                validated["base_url"] = url

        elif category == "telegram":
            if "bot_token" in data and data["bot_token"] and data["bot_token"] != "__CLEAR__":
                token = str(data["bot_token"]).strip()
                # Basic token format check: digits:alphanumeric
                if not re.match(r"^\d+:[A-Za-z0-9_-]+$", token):
                    raise ValueError("Format Telegram Bot Token không hợp lệ (ví dụ: 123456:ABC-DEF...).")
                validated["bot_token"] = token
            elif "bot_token" in data:
                validated["bot_token"] = data["bot_token"]
            if "allow_from" in data:
                validated["allow_from"] = self._validate_allow_list(data["allow_from"])

        elif category == "zalo":
            for secret_field in ("bot_token", "webhook_secret"):
                if secret_field in data:
                    validated[secret_field] = data[secret_field]
            if "webhook_url" in data and data["webhook_url"] and data["webhook_url"] != "__CLEAR__":
                url = str(data["webhook_url"]).strip()
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise ValueError("Webhook URL của Zalo phải là URL hợp lệ.")
                validated["webhook_url"] = url
            elif "webhook_url" in data:
                validated["webhook_url"] = data["webhook_url"]
            if "allow_from" in data:
                validated["allow_from"] = self._validate_allow_list(data["allow_from"])

        elif category == "openclaw":
            if "runtime_path" in data and data["runtime_path"]:
                runtime_path = os.path.abspath(
                    os.path.expanduser(str(data["runtime_path"]).strip())
                )
                if not os.path.isfile(runtime_path) or not os.access(runtime_path, os.X_OK):
                    raise ValueError("runtime_path phải là file thực thi đang tồn tại.")
                validated["runtime_path"] = runtime_path
            if "workspace_path" in data and data["workspace_path"]:
                workspace = os.path.abspath(
                    os.path.expanduser(str(data["workspace_path"]).strip())
                )
                if not workspace.startswith(os.path.expanduser("~") + os.sep):
                    raise ValueError("workspace_path phải nằm trong thư mục home của người dùng.")
                validated["workspace_path"] = workspace
            if "base_url" in data and data["base_url"]:
                url = str(data["base_url"]).strip()
                if not url.startswith(("http://", "https://")):
                    raise ValueError("OpenClaw base_url phải bắt đầu bằng http:// hoặc https://")
                validated["base_url"] = url

        elif category == "frontend":
            if "backend_url" in data and data["backend_url"]:
                url = str(data["backend_url"]).strip()
                if not url.startswith(("http://", "https://")):
                    raise ValueError("Backend URL phải bắt đầu bằng http:// hoặc https://")
                validated["backend_url"] = url
            for field in ("frontend_port", "backend_port"):
                if field in data:
                    try:
                        port = int(data[field])
                        if not 1 <= port <= 65535:
                            raise ValueError()
                    except (TypeError, ValueError):
                        raise ValueError(f"{field} phải từ 1 đến 65535.")
                    validated[field] = port

        for k, v in data.items():
            if k not in validated and k != "clear_secrets":
                validated[k] = v

        return validated

    @staticmethod
    def _validate_allow_list(value: Any) -> list:
        if value is None:
            return []
        items = value if isinstance(value, list) else str(value).split(",")
        result = []
        for item in items:
            cleaned = str(item).strip()
            if cleaned and cleaned not in result:
                result.append(cleaned)
        if len(result) > 100:
            raise ValueError("Allow-list không được vượt quá 100 mục.")
        return result

    def update_category_config(self, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        current = self.load_raw_config()
        if category not in current:
            raise ValueError(f"Category '{category}' không tồn tại.")

        validated_data = self.validate_category_config(category, data)
        cat_secrets = SECRET_FIELDS.get(category, [])
        clear_secrets = data.get("clear_secrets", [])
        if isinstance(clear_secrets, str):
            clear_secrets = [clear_secrets]

        target_cat = current[category]
        if category == "ai":
            previous_provider = str(target_cat.get("provider", "")).lower()
            next_provider = str(
                validated_data.get("provider", previous_provider)
            ).lower()
            if next_provider != previous_provider and not data.get("api_key"):
                target_cat["api_key"] = ""

        for k, v in validated_data.items():
            if k == "clear_secrets":
                continue
            if k in cat_secrets:
                # If clear is requested or value is explicitly __CLEAR__
                if k in clear_secrets or v == "__CLEAR__":
                    target_cat[k] = ""
                # If empty string provided, preserve existing secret!
                elif v == "" or v is None:
                    pass
                else:
                    target_cat[k] = str(v).strip()
            else:
                target_cat[k] = v

        current[category] = target_cat
        self.save_config(current)
        self._sync_runtime_env(category, target_cat)
        if (
            category == "ai"
            and ("api_key" in clear_secrets or data.get("api_key") == "__CLEAR__")
        ):
            provider = str(target_cat.get("provider", "")).lower()
            env_key = AI_ENV_KEYS.get(provider, {}).get("api_key")
            if env_key:
                self._clear_runtime_env_key(env_key)
        return self.get_public_config()[category]

    def _clear_runtime_env_key(self, env_key: str) -> None:
        if not os.path.exists(self.env_path):
            os.environ.pop(env_key, None)
            return
        with open(self.env_path, "r", encoding="utf-8") as env_file:
            lines = env_file.read().splitlines()
        output = [
            line for line in lines
            if not (
                line.strip()
                and not line.lstrip().startswith("#")
                and line.split("=", 1)[0].strip() == env_key
            )
        ]
        self._atomic_write_env(output)
        os.environ.pop(env_key, None)

    def _sync_runtime_env(self, category: str, values: Dict[str, Any]):
        mapping = RUNTIME_ENV_KEYS.get(category, {})
        if category == "ai":
            mapping = AI_ENV_KEYS.get(str(values.get("provider", "")).lower(), {})
        updates = {
            env_key: str(values[field])
            for field, env_key in mapping.items()
            if field in values and values[field] not in (None, "")
        }
        if not updates:
            return

        env_lines = []
        if os.path.exists(self.env_path):
            with open(self.env_path, "r", encoding="utf-8") as env_file:
                env_lines = env_file.read().splitlines()

        seen = set()
        output = []
        for line in env_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in line:
                key = line.split("=", 1)[0].strip()
                if key in updates:
                    output.append(f"{key}={updates[key]}")
                    seen.add(key)
                    continue
            output.append(line)
        for key, value in updates.items():
            if key not in seen:
                output.append(f"{key}={value}")

        self._atomic_write_env(output)

        for key, value in updates.items():
            os.environ[key] = value

    def _atomic_write_env(self, output: list) -> None:
        env_dir = os.path.dirname(self.env_path)
        os.makedirs(env_dir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            dir=env_dir,
            prefix=".env_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as env_file:
                env_file.write("\n".join(output).rstrip() + "\n")
                env_file.flush()
                os.fsync(env_file.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.env_path)
            os.chmod(self.env_path, 0o600)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def save_config(self, config_data: Dict[str, Any], backup: bool = True):
        # Backup before write
        if backup and os.path.exists(self.config_path):
            shutil.copy2(self.config_path, f"{self.config_path}.bak")

        dirname = os.path.dirname(self.config_path)
        os.makedirs(dirname, exist_ok=True)

        # Atomic write
        fd, temp_path = tempfile.mkstemp(dir=dirname, prefix=".config_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.config_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

config_service = ConfigService()
