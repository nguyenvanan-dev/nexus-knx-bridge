#!/usr/bin/env bash
set -euo pipefail

CHECK_ONLY=false
if [ "${1:-}" = "--check-only" ]; then
    CHECK_ONLY=true
elif [ "$#" -gt 0 ]; then
    echo "Usage: $0 [--check-only]"
    exit 2
fi

echo "=================================================="
echo "          KNX Bridge Automated Installer          "
echo "=================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 1. Check Dependencies
echo "[1/7] Checking system requirements..."
command -v python3 >/dev/null 2>&1 || { echo "Python3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required but not installed."; exit 1; }

PYTHON_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VER and Node $(node -v)"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
    echo "Python >= 3.10 is required."
    exit 1
}
NODE_MAJOR=$(node -p 'Number(process.versions.node.split(".")[0])')
if [ "$NODE_MAJOR" -lt 18 ]; then
    echo "Node.js >= 18 is required."
    exit 1
fi

for required in requirements.txt frontend/package.json app.py; do
    [ -e "$required" ] || { echo "Required project file is missing: $required"; exit 1; }
done

if $CHECK_ONLY; then
    echo "Preflight check PASSED. No files, packages, or services were changed."
    exit 0
fi

# Create a secure first-run environment without embedding credentials in Git.
if [ ! -f "$PROJECT_DIR/.env" ]; then
    command -v openssl >/dev/null 2>&1 || {
        echo "OpenSSL is required to create first-run security keys."
        exit 1
    }
    umask 077
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    KNX_API_TOKEN=$(openssl rand -hex 32)
    API_KEY=$(openssl rand -hex 32)
    SETUP_BOOTSTRAP_TOKEN=$(openssl rand -hex 24)
    cat > "$PROJECT_DIR/.env" << ENV_EOF
JWT_SECRET_KEY=$JWT_SECRET_KEY
KNX_API_TOKEN=$KNX_API_TOKEN
API_KEY=$API_KEY
SETUP_BOOTSTRAP_TOKEN=$SETUP_BOOTSTRAP_TOKEN
BACKEND_URL=http://127.0.0.1:5055
KNX_GATEWAY_IP=127.0.0.1
KNX_GATEWAY_PORT=3671
ENV_EOF
    chmod 600 "$PROJECT_DIR/.env"
    echo "Created secure .env (0600). Use SETUP_BOOTSTRAP_TOKEN for first-run setup."
fi

# 2. Setup Python Virtual Environment
echo "[2/7] Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# 3. Setup Frontend Dependencies & Build
echo "[3/7] Installing frontend dependencies & building production bundle..."
if [ -d "frontend" ]; then
    (cd frontend && npm install && npm run build)
fi

# 4. Prepare Centralized Configuration Baseline
echo "[4/7] Initializing secure configuration baseline..."
python3 -c '
from services.config_service import config_service
cfg = config_service.load_raw_config()
print("Config baseline initialized OK")
'
chmod 600 config.json 2>/dev/null || true

# 5. Bootstrap OpenClaw workspace when OpenClaw is already present.
echo "[5/7] Checking optional OpenClaw workspace..."
if command -v openclaw >/dev/null 2>&1 || [ -d "$HOME/.openclaw" ]; then
    python3 -c '
from services.openclaw_config_service import openclaw_config_service
result = openclaw_config_service.bootstrap_workspace_safe()
print("OpenClaw workspace ready. Created:", ", ".join(result["created"]) or "none")
print("Existing files preserved:", ", ".join(result["skipped_existing"]) or "none")
'
else
    echo "OpenClaw is not installed; workspace bootstrap skipped (optional)."
fi

# 6. Generate Systemd User Services
echo "[6/7] Generating Systemd user service files..."
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

for service in knx-bridge.service knx-frontend.service; do
    if systemctl cat "$service" >/dev/null 2>&1; then
        echo "ERROR: A system-level $service already exists."
        echo "Refusing to create a duplicate user service. Remove or migrate the"
        echo "existing service explicitly, then run this installer again."
        exit 1
    fi
done

cat << SERVICE_EOF > "$SYSTEMD_USER_DIR/knx-bridge.service"
[Unit]
Description=KNX Bridge Backend Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 5055
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
SERVICE_EOF

cat << SERVICE_EOF > "$SYSTEMD_USER_DIR/knx-frontend.service"
[Unit]
Description=KNX Bridge Frontend Service
After=network.target knx-bridge.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR/frontend
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$(which npm) start
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
SERVICE_EOF

systemctl --user daemon-reload || true

echo "[7/7] Installation completed successfully!"
echo "To start services:"
echo "  systemctl --user enable --now knx-bridge.service knx-frontend.service"
echo "=================================================="
