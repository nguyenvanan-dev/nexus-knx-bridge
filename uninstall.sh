#!/usr/bin/env bash
set -euo pipefail

PURGE=false
if [ "${1:-}" = "--purge" ]; then
    PURGE=true
fi

echo "=================================================="
echo "          KNX Bridge Uninstaller                  "
echo "=================================================="

echo "Stopping and disabling systemd user services..."
systemctl --user stop knx-frontend.service knx-bridge.service 2>/dev/null || true
systemctl --user disable knx-frontend.service knx-bridge.service 2>/dev/null || true

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
rm -f "$SYSTEMD_USER_DIR/knx-bridge.service" "$SYSTEMD_USER_DIR/knx-frontend.service"
systemctl --user daemon-reload || true

if [ "$PURGE" = true ]; then
    echo "Purging configuration and virtualenv (.venv, config.json)..."
    rm -rf .venv config.json
    echo "Data purged."
else
    echo "Systemd services uninstalled. Source code and database files preserved."
fi

echo "Uninstallation complete."
echo "=================================================="
