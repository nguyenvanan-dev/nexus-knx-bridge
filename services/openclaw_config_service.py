import os
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

HOME_DIR = Path.home()
OPENCLAW_DIR = HOME_DIR / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class OpenClawConfigService:
    def __init__(self):
        pass

    def _is_path_safe(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return HOME_DIR in resolved.parents or resolved == HOME_DIR
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        executable = shutil.which("openclaw") or shutil.which("9router")
        runtime_installed = executable is not None

        service_status = "unknown"
        try:
            res = subprocess.run(
                ["systemctl", "is-active", "9router.service"],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0:
                service_status = "active"
            else:
                service_status = res.stdout.strip() or "inactive"
        except Exception:
            service_status = "not_found"

        workspace_path = str(OPENCLAW_DIR / "workspace")
        workspace_exists = (OPENCLAW_DIR / "workspace").exists()

        # Check skill symlink
        skills_target = OPENCLAW_DIR / "workspace" / "skills"
        symlink_valid = False
        if skills_target.is_symlink():
            try:
                target = skills_target.readlink()
                symlink_valid = (target.resolve() == (PROJECT_ROOT / "skills").resolve())
            except Exception:
                symlink_valid = False

        # Read config safe metadata (provider/model ONLY, NO KEYS)
        provider_info = {"provider": "none", "model": "none", "configured": False}
        telegram_pairing = {"paired": False, "mode": "none"}
        zalo_pairing = {"paired": False, "mode": "none"}

        if OPENCLAW_CONFIG.exists():
            try:
                with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

                # Check provider (safe fields only)
                if "ai" in cfg and isinstance(cfg["ai"], dict):
                    provider_info["provider"] = cfg["ai"].get("provider", "unknown")
                    provider_info["model"] = cfg["ai"].get("model", "unknown")
                    provider_info["configured"] = bool(cfg["ai"].get("provider"))
                elif "llm" in cfg and isinstance(cfg["llm"], dict):
                    provider_info["provider"] = cfg["llm"].get("provider", "unknown")
                    provider_info["model"] = cfg["llm"].get("model", "unknown")
                    provider_info["configured"] = True

                # Check Telegram / Zalo pairing safely
                if "telegram" in cfg and isinstance(cfg["telegram"], dict):
                    telegram_pairing["paired"] = bool(cfg["telegram"].get("bot_name") or cfg["telegram"].get("enabled"))
                    telegram_pairing["mode"] = cfg["telegram"].get("mode", "bot")
                if "zalo" in cfg and isinstance(cfg["zalo"], dict):
                    zalo_pairing["paired"] = bool(cfg["zalo"].get("enabled"))
                    zalo_pairing["mode"] = cfg["zalo"].get("mode", "webhook")
            except Exception:
                pass

        return {
            "runtime_installed": runtime_installed,
            "executable_path": executable or "",
            "service_status": service_status,
            "workspace_path": workspace_path,
            "workspace_exists": workspace_exists,
            "skills_symlink_valid": symlink_valid,
            "provider_metadata": provider_info,
            "telegram_pairing": telegram_pairing,
            "zalo_pairing": zalo_pairing
        }

    def ensure_skills_symlink(self) -> bool:
        workspace_skills = OPENCLAW_DIR / "workspace" / "skills"
        repo_skills = PROJECT_ROOT / "skills"

        if not repo_skills.exists():
            return False

        os.makedirs(OPENCLAW_DIR / "workspace", exist_ok=True)

        if workspace_skills.is_symlink() or workspace_skills.exists():
            if workspace_skills.is_symlink() and workspace_skills.readlink().resolve() == repo_skills.resolve():
                return True
            if workspace_skills.is_symlink():
                workspace_skills.unlink()
            elif workspace_skills.is_dir():
                return False

        try:
            workspace_skills.symlink_to(repo_skills, target_is_directory=True)
            return True
        except Exception:
            return False

    def update_provider_safe(self, provider: str, model: str) -> bool:
        if not OPENCLAW_CONFIG.exists():
            return False

        backup_path = OPENCLAW_DIR / "openclaw.json.bak"
        try:
            shutil.copy2(OPENCLAW_CONFIG, backup_path)
            with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            if "ai" not in cfg or not isinstance(cfg["ai"], dict):
                cfg["ai"] = {}

            cfg["ai"]["provider"] = provider
            cfg["ai"]["model"] = model

            # Atomic write
            fd, temp_path = tempfile.mkstemp(dir=str(OPENCLAW_DIR), prefix=".openclaw_", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, OPENCLAW_CONFIG)
            return True
        except Exception:
            return False

openclaw_config_service = OpenClawConfigService()
