# KNX Bridge

KNX Bridge is a self-hosted smart-home control platform for Raspberry Pi. It
combines a FastAPI backend, a Next.js administration UI, SQLite device
registry, ETS `.knxproj` import, OpenClaw skills, and Telegram/Zalo adapters.

## Release status

The software is a **v1.0 release candidate**. Automated installation, isolated
Setup Wizard, unit/integration tests, frontend production build, dependency
audit, and repository secret scan are verified. Physical KNX actuation and
live Telegram/Zalo delivery remain owner-operated acceptance tests.

## Requirements

- Linux on x86_64 or ARM64 (Ubuntu, Debian, Raspberry Pi OS)
- Python 3.10 or newer
- Node.js 18 or newer
- KNX/IP gateway for physical operation
- OpenClaw and 9router for AI/chat integrations (optional for KNX-only use)

## Install

```bash
git clone <PRIVATE_REPOSITORY_URL> knx-bridge
cd knx-bridge
./install.sh --check-only
./install.sh
systemctl --user enable --now knx-bridge.service knx-frontend.service
./check_installation.sh
```

Open `http://<server-ip>:3000/setup`. On first installation, retrieve the
bootstrap token locally:

```bash
grep '^SETUP_BOOTSTRAP_TOKEN=' .env
```

Never paste `.env`, API keys, pairing credentials, databases, or private
credential vaults into issues or commits.

## Main capabilities

- SQLite-backed KNX device registry and device management
- Secure ETS project parsing, review, dry-run, and controlled proposal apply
- Dynamic AI providers with multiple models and masked credentials
- OpenClaw runtime, workspace, skills, and skill credential management
- Telegram, Zalo Bot and Zalo Personal configuration, group allow-lists,
  pairing/login status and history controls
- Tailscale runtime status
- Backup/restore administration and service diagnostics

## Safe verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
cd frontend
npm ci
npm audit --audit-level=high
npm run build
```

Tests must not write to a live KNX bus, apply a real ETS proposal, or use the
production database.

## Documentation

- [Setup guide](docs/SETUP_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [OpenClaw integration](docs/OPENCLAW_INTEGRATION.md)
- [Known issues](docs/KNOWN_ISSUES.md)
- [Changelog](docs/CHANGELOG.md)

## License

This repository is currently private and distributed under the terms in
[LICENSE](LICENSE).
