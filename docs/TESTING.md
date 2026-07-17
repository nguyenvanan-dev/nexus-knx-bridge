# Testing & Verification

## 1. Automated Tests
- **Unit Tests:** `tests/unit/` - Status: **PASSED**
- **Integration Tests:** `tests/integration/` - Status: **PASSED**
- **Stress Tests:** `tests/performance/stress_test.py` - Handled locally.

## 2. Manual Verification Checklist (Phase D)
The following steps are required to finalize Phase D (Production Physical Deployment).

- [x] **Backend API:** `curl localhost:5055/health` -> OK (13 devices).
- [x] **Database:** SQLite WAL mode active, no locked DB errors.
- [x] **Systemd:** `knx-bridge.service` survives restart and binds to port 5055.
- [ ] **KNX Physical Test:** Trigger a physical switch via REST API.
- [ ] **Telegram E2E Test:** Send command via Telegram -> AI -> API -> Physical Device.
- [ ] **Zalo E2E Test:** Send command via Zalo -> AI -> API -> Physical Device.
- [ ] **System Reboot Test:** Reboot Raspberry Pi and verify both backend and OpenClaw start automatically.
