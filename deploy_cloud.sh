#!/bin/bash
# Helix Mythos — Google Cloud VM Deployment Script
# Runs on the cloud VM after SSH access

set -e

echo "======================================================"
echo " HELIX MYTHOS — CLOUD DEPLOYMENT"
echo "======================================================"

# Update system
sudo apt-get update -y && sudo apt-get upgrade -y

# Install Python 3.12
sudo apt-get install -y python3.12 python3.12-pip python3-pip python3-venv git wget curl

# Create helix directory
mkdir -p /home/helix && cd /home/helix

# Install Python packages (no camera/display packages for cloud)
pip3 install --break-system-packages \
    python-telegram-bot \
    feedparser \
    requests \
    beautifulsoup4 \
    lxml \
    scikit-learn \
    numpy \
    pandas \
    scipy \
    networkx \
    psutil \
    Pillow \
    ultralytics

echo "Packages installed."

# Create systemd service — auto-starts on boot, restarts on crash
sudo tee /etc/systemd/system/helixmythos.service > /dev/null << 'EOF'
[Unit]
Description=Helix Mythos Autonomous AI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/helix
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
Environment=PYTHONIOENCODING=utf-8
Environment=PYTHONUTF8=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable helixmythos
sudo systemctl start helixmythos

echo "======================================================"
echo " Helix Mythos is NOW RUNNING on the cloud!"
echo " It will restart automatically if it ever crashes."
echo " It survives reboots."
echo " Check Telegram for the boot message."
echo "======================================================"
