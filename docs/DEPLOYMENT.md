# Deployment Guide

## Supported Target

- Ubuntu, Debian or Raspberry Pi OS on ARM64/x86_64
- Python 3.10+
- Node.js 18+
- KNX/IP gateway for physical control
- OpenClaw when agent, skills or Telegram/Zalo integrations are enabled
- 9router when quota-aware AI provider routing and fallback are desired

The repository can be installed in any directory. Commands below assume the
current shell is already inside the cloned repository.

## Install

```bash
./install.sh --check-only
./install.sh
systemctl --user enable --now knx-bridge.service knx-frontend.service
./check_installation.sh
```

Open `http://<server-ip>:3000/setup` and complete the Setup Wizard. Retrieve the
first-run bootstrap token locally with:

```bash
grep '^SETUP_BOOTSTRAP_TOKEN=' .env
```

## Runtime Services

- `knx-bridge.service`: FastAPI backend on port 5055
- `knx-frontend.service`: Next.js frontend on port 3000
- `9router.service`: optional OpenAI-compatible gateway that routes across the
  user's configured AI providers and falls back when quota is exhausted
- OpenClaw gateway/runtime: optional agent runtime for skills and chat channels;
  it may use 9router's API or connect to another provider directly

The installer creates backend/frontend user services and refuses to create
duplicates when system-level services already exist.

When OpenClaw is already installed, the installer also creates only the missing
KNX AI Agent workspace files from `openclaw/workspace-template/`. Existing
workspace files and all credentials are preserved.

## Verification

```bash
./check_installation.sh
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
(cd frontend && npm ci && npm run lint && npm run build)
curl -I http://127.0.0.1:3000/
curl http://127.0.0.1:5055/api/setup/status
```

## Upgrade

1. Create a system backup from the administration UI.
2. Stop backend/frontend services.
3. Pull the reviewed release.
4. Install Python and frontend dependencies.
5. Run migrations only when the release notes explicitly require them.
6. Build frontend, run tests, then restart backend/frontend.

Do not reset or replace runtime `.env`, `config.json`, SQLite databases or
OpenClaw credentials during an upgrade.

## Rollback

Roll back to a known reviewed tag or commit rather than a hardcoded hash:

```bash
git log --oneline --decorate -20
git switch --detach <known-good-tag-or-commit>
systemctl --user restart knx-bridge.service knx-frontend.service
```

Restore a database backup only after confirming schema compatibility.
