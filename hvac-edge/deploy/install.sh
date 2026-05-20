#!/bin/bash
# hvac-edge/deploy/install.sh
set -e

INSTALL_DIR="/opt/hvac-edge"
CONFIG_DIR="/etc/hvac-edge"
DATA_DIR="/var/lib/hvac-edge"

echo "Installing hvac-edge..."

# Create user
id -u hvac &>/dev/null || useradd -r -s /bin/false hvac

# Create directories
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR/plans" "$CONFIG_DIR/models" "$DATA_DIR"

# Copy files
cp -r edge/ "$INSTALL_DIR/edge/"
cp pyproject.toml "$INSTALL_DIR/"

# Python venv
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"

# Config
cp deploy/edge_config.yaml "$CONFIG_DIR/edge_config.yaml"
chown -R hvac:hvac "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR"

# Systemd
cp deploy/systemd/hvac-edge.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hvac-edge

echo "Installation complete. Start with: systemctl start hvac-edge"
