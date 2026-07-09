#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./scripts/install.sh)"
  exit 1
fi

echo "Copying knx-bridge.service to /etc/systemd/system/"
cp /home/an/knx-bridge/scripts/knx-bridge.service /etc/systemd/system/

echo "Creating log file and setting permissions..."
touch /var/log/knx-bridge.log
chown an:an /var/log/knx-bridge.log

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling knx-bridge service to start on boot..."
systemctl enable knx-bridge

echo "Starting knx-bridge service..."
systemctl start knx-bridge

echo "Installation complete. Check status with: systemctl status knx-bridge"
