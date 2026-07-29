# NEXUS KNX Bridge Project Documentation

## Product Purpose

NEXUS is primarily an OpenClaw KNX AI Agent accessed through Zalo and
Telegram. It uses tools and skills to understand natural-language requests,
read system state and safely control KNX devices. The web application is the
administration layer for setup, ETS import, devices, scenes, diagnostics,
credentials and runtime status.

## Current Architecture

```text
Zalo / Telegram -> OpenClaw KNX AI Agent -> Tools/Skills -> KNX Bridge -> KNX
Web Admin -----------------------------------------------> KNX Bridge / SQLite
AI provider -------------------------------> OpenClaw
AI providers -> optional 9router ----------> OpenClaw
```

OpenClaw runtime data and credentials remain in `$HOME/.openclaw`. The
repository includes only a secret-free workspace template and never
automatically overwrites customized agent files.

## Historical Milestones

### Milestone v0.7: Device Management
- Implemented bulk import of devices with robust transaction handling and conflict resolution.
- Enforced Domain-driven design with DeviceService acting as a facade for DeviceRegistry and StateManager.
- Enhanced automation engine V2 to resolve `notify_fn` and EventBus injection issues.
- Updated EventBus typing and usage for `DEVICE_REGISTRY_UPDATED`.
- Implemented duplicate group address check with automatic rollback during import.
- Documented and structured codebase for stable architecture freeze.

### Milestone v0.8: Automation CRUD
- Implemented Automation Rules CRUD with dual test modes (Dry Run, Execute)
- Enforced Validation against existing Device Registry and infinite loop protection
- Added backend Audit Logs for rule creation, deletion, testing, and toggling
- Updated frontend Dashboard UI to integrate seamlessly with the v2 API and support dual testing modes
