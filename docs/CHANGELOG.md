# Project Timeline (Changelog)

This document tracks the high-level phases and milestones of the project.

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
- Database unification into `smarthome.db`.
- SQLite WAL mode and connection pooling implemented.
- Asynchronous EventBus and background queue processing introduced.
- Refactored `IDENTITY.md` to remove PII-based authorization.
- Shifted all RBAC to OpenClaw Gateway `ownerAllowFrom`.

## Phase D: Production Deployment (CURRENT)
- **Sprint 10:** Target Raspberry Pi deployment (`10.1.10.105`).
- Systemd service integration for `knx-bridge`.
- Resolved `uvicorn` port conflicts.
- **Remaining:** End-to-end physical verification (KNX bus physical actuation via chat adapters).
