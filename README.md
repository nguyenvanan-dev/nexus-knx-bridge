# NEXUS KNX Bridge

NEXUS KNX Bridge is an OpenClaw-powered KNX AI Agent for Zalo and Telegram,
self-hosted on Raspberry Pi. Its primary purpose is natural-language control,
monitoring and operation of KNX smart homes. Tools and skills extend the
agent's KNX knowledge, while the FastAPI bridge, SQLite registry, ETS import
pipeline and Next.js web UI provide the control and administration layer.

```text
Zalo / Telegram -> OpenClaw KNX AI Agent -> Tools & Skills
                                              |
                                              v
Web Admin ------------------------------> KNX Bridge -> KNX/IP -> KNX devices
```

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
- OpenClaw agent runtime for Telegram/Zalo, skills and task orchestration
  (optional for KNX-only use)
- 9router AI provider gateway for quota-aware routing and fallback through one
  OpenAI-compatible API (optional; OpenClaw can also use a provider directly)

## Install

```bash
git clone https://github.com/nguyenvanan-dev/nexus-knx-bridge.git
cd nexus-knx-bridge
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
- OpenClaw KNX AI Agent workspace template for Zalo and Telegram
- Secure ETS project parsing, review, dry-run, and controlled proposal apply
- Dynamic AI providers with multiple models and masked credentials
- Direct provider API keys are supported; 9router is an optional
  OpenAI-compatible provider gateway for multi-provider quota fallback
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

Released under the [MIT License](LICENSE).
