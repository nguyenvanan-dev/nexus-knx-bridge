# KNX Bridge Project State

This document records the release state of the repository. Repository evidence
and automated checks take precedence if this document becomes stale.

## Release

- Version: v1.0 release candidate
- Target: Linux on ARM64 or x86_64
- Runtime: FastAPI backend, Next.js frontend, SQLite, OpenClaw integrations
- Canonical device and scene storage: SQLite
- Legacy `devices.json` and `scenes.json` runtime paths: retired
- OpenClaw KNX AI Agent workspace template: implemented
- Zalo and Telegram: primary conversational channels for the KNX Agent
- 9router: optional AI provider router, not an agent runtime

## Implemented

- Admin authentication and first-run bootstrap
- Ten-step Setup Wizard
- KNX/IP gateway configuration and socket check
- Dynamic AI providers, models and masked credentials
- OpenClaw runtime/workspace/skill configuration
- Telegram bot configuration and pairing metadata
- Zalo bot/webhook configuration
- Zalo Personal QR login, logout, group selection and history settings
- Tailscale status
- Device management and dynamic KNX capabilities
- ETS `.knxproj` parse, review, dry-run and guarded apply
- Scene, automation, diagnostics, health and backup administration
- Installer, uninstaller, installation checker and GitHub Actions CI

## Verification

- Python dependency check: pass
- Backend tests: 57 passed
- Frontend lint: pass
- Frontend production build: pass
- `npm audit --audit-level=high --omit=dev`: no vulnerabilities
- Installer preflight: pass
- Tracked working tree and reachable Git history secret scan: no known matches

## Owner Acceptance Still Required

The following checks intentionally require the owner and real infrastructure:

- Physical KNX writes for each installed actuator/device type
- Telegram delivery and pairing with the production bot
- Zalo Bot webhook delivery
- Zalo Personal group read/reply behavior with the selected account
- Backup restore on a disposable copy before relying on disaster recovery

These are deployment acceptance checks, not automated CI operations.

## Safety

- Never test real KNX writes from CI.
- Never apply a real ETS proposal without administrator confirmation.
- Never commit `.env`, databases, OpenClaw credentials, config files or vaults.
- Do not restart 9router/OpenClaw automatically from tests.
