#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "          KNX Bridge Automated Installer          "
echo "=================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 1. Check Dependencies
echo "[1/6] Checking system requirements..."
command -v python3 >/dev/null 2>&1 || { echo "Python3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required but not installed."; exit 1; }

PYTHON_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VER and Node $(node -v)"

# 2. Setup Python Virtual Environment
echo "[2/6] Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# 3. Setup Frontend Dependencies & Build
echo "[3/6] Installing frontend dependencies & building production bundle..."
if [ -d "frontend" ]; then
    (cd frontend && npm install && npm run build)
fi

# 4. Prepare Centralized Configuration Baseline
echo "[4/6] Initializing secure configuration baseline..."
python3 -c '
from services.config_service import config_service
cfg = config_service.load_raw_config()
print("Config baseline initialized OK")
'
chmod 600 config.json 2>/dev/null || true

# 5. Generate Systemd User Services
echo "[5/6] Generating Systemd user service files..."
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

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "ERROR: $PROJECT_DIR/.env is required before services can be installed."
    exit 1
fi

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

echo "[6/6] Installation completed successfully!"
echo "To start services:"
echo "  systemctl --user enable --now knx-bridge.service knx-frontend.service"
echo "=================================================="
