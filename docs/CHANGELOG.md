# Project Timeline (Changelog)

This document tracks the high-level phases and milestones of the project.

## v1.0.0-rc.1 - Release Candidate

- Added secure first-run installer and isolated Setup Wizard.
- Added dynamic AI providers, multiple models, default model selection, and
  masked provider credentials.
- Added OpenClaw skill/plugin credential management.
- Added Telegram/Zalo configuration and pairing visibility.
- Added secure ETS `.knxproj` parse, review, dry-run, and proposal workflow.
- Removed `devices.json` from runtime configuration paths.
- Added end-to-end setup simulation using temporary DB/config/runtime files.
- Updated frontend dependencies and reduced `npm audit` findings to zero.
- Added GitHub Actions for backend tests, frontend audit/build, and gitleaks.
- Project-owner acceptance confirmed for Zalo E2E on 2026-07-15, Telegram E2E
  on 2026-07-17, and physical KNX plus Raspberry Pi reboot on 2026-07-20.

## Phase A: Foundation & Architecture
- Setup FastAPI backend and `xknx` tunneling.
- Basic REST endpoints for device control.
- Integration of `devices.json` mapping.

## Phase B: Intelligence & Integrations
- OpenClaw AI Gateway integration.
- Telegram and Zalo adapter setup.
- Initial AI context endpoints (`/api/ai/context`).
- Legacy fragmented databases (`knx.db`, `chat_history.db`).

## Phase C: Optimization & Hardening
- Consolidated KNX/device configuration into `smarthome.db`; retained
  `data/chat_history.db` for Zalo/group conversation history.
- SQLite WAL mode and connection pooling implemented.
- Asynchronous EventBus and background queue processing introduced.
- Refactored `IDENTITY.md` to remove PII-based authorization.
- Shifted all RBAC to OpenClaw Gateway `ownerAllowFrom`.

## Phase D: Production Deployment
- **Sprint 10:** Target Raspberry Pi deployment.
- Systemd service integration for `knx-bridge`.
- Resolved `uvicorn` port conflicts.
- Physical KNX actuation, Telegram/Zalo E2E and reboot verification accepted by
  the project owner.

## v1.0 Release Candidate
- Added a portable OpenClaw KNX AI Agent workspace template.
- Added safe workspace bootstrap that preserves existing custom files.
- Clarified that Zalo and Telegram are conversational KNX Agent channels.
- Separated the optional 9router provider gateway from the OpenClaw runtime.
