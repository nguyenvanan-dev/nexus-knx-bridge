# Testing & Verification

## 1. Automated Tests
- **Unit Tests:** `tests/unit/` - Status: **PASSED**
- **Integration Tests:** `tests/integration/` - Status: **PASSED**
- **Stress Tests:** `tests/performance/stress_test.py` - Handled locally.

## 2. Manual Verification Checklist (Phase D)
The following steps are required to finalize Phase D (Production Physical Deployment).

- [x] **Backend API:** `curl localhost:5055/health` -> returns a healthy response.
- [x] **Workspace bootstrap:** Creates missing agent files and preserves custom files.
- [x] **Database:** SQLite WAL mode active, no locked DB errors.
- [x] **Systemd:** `knx-bridge.service` survives restart and binds to port 5055.
- [x] **KNX Physical Test:** Trigger a physical switch via REST API.
- [x] **Telegram E2E Test:** Send command via Telegram -> AI -> API -> Physical Device.
- [x] **Zalo E2E Test:** Send command via Zalo -> AI -> API -> Physical Device.
- [x] **System Reboot Test:** Reboot Raspberry Pi and verify both backend and OpenClaw start automatically.

The project owner confirmed the acceptance schedule as follows:

- **Zalo E2E:** completed on Wednesday, 2026-07-15.
- **Telegram E2E:** completed on Friday, 2026-07-17.
- **KNX Physical and System Reboot:** completed on Monday, 2026-07-20.

This release records that owner confirmation; it does not claim that fresh
hardware, messaging or reboot logs were generated during the release hardening
session.
