# Deployment Status and Guide

## 1. Environment Details
- **Target Hardware:** Raspberry Pi (ARM64)
- **OS:** Ubuntu
- **IP Address:** `10.1.10.105`
- **Application Path:** `/home/an/knx-bridge`
- **Python Environment:** `.venv` (Python 3.12)

## 2. Services
### knx-bridge.service
- **Role:** Core FastAPI Backend.
- **Port:** `0.0.0.0:5055`
- **Status:** **Active (Running)**. The previous issue with orphaned `uvicorn` processes blocking the port was resolved.
- **Verification:** `curl http://localhost:5055/health` returns `status: ok` (13 devices).

### openclaw-gateway.service
- **Role:** AI Orchestration.
- **Status:** Currently running manually as a background process (PID `8661`).
- **TODO:** Needs to be daemonized into a proper `systemd` unit for reboot resilience.

## 3. Rollback Procedure
If the current deployment fails catastrophically, use the following rollback plan:

- **Latest Deployment:** `24b0a7b` (Phase D, current master).
- **Last Stable:** `7102b68` (Final production hardening pass).

**Commands:**
```bash
cd /home/an/knx-bridge
git checkout 7102b68
sudo systemctl restart knx-bridge
```

**Verification post-rollback:**
```bash
systemctl status knx-bridge
curl http://127.0.0.1:5055/health
```
