#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./scripts/install.sh)"
  exit 1
fi

PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
USER_NAME=$(logname || echo $SUDO_USER || echo $USER)

echo "Installing KNX AI Bridge from: $PROJECT_DIR"
echo "Running as user: $USER_NAME"

SERVICE_FILE="/etc/systemd/system/knx-bridge.service"

echo "Generating knx-bridge.service..."
cat <<EOF > $SERVICE_FILE
[Unit]
Description=KNX AI Bridge (OpenClaw)
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 5055
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/var/log/knx-bridge.log
StandardError=append:/var/log/knx-bridge.log

[Install]
WantedBy=multi-user.target
EOF

echo "Creating log file and setting permissions..."
touch /var/log/knx-bridge.log
chown $USER_NAME:$USER_NAME /var/log/knx-bridge.log

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling knx-bridge service to start on boot..."
systemctl enable knx-bridge

echo "Starting knx-bridge service..."
systemctl start knx-bridge

echo "Installation complete. Check status with: systemctl status knx-bridge"

