#!/bin/bash
# ==============================================================================
# Oracle Cloud Ubuntu VM — Quick Setup Script for Job Scraper
# ==============================================================================

set -e

echo "=== [1/5] Updating system packages ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== [2/5] Installing Python, Git, and system utilities ==="
sudo apt-get install -y python3 python3-pip python3-venv git wget curl unzip libxi6 libgconf-2-4 libnss3 libasound2 libgbm1

echo "=== [3/5] Installing Google Chrome (Headless) ==="
if ! command -v google-chrome &> /dev/null; then
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb || true
    if [ -f google-chrome-stable_current_amd64.deb ]; then
        sudo apt-get install -y ./google-chrome-stable_current_amd64.deb || sudo apt-get --fix-broken install -y
        rm -f google-chrome-stable_current_amd64.deb
    else
        echo "Chrome deb download failed, trying chromium-browser..."
        sudo apt-get install -y chromium-browser chromium-chromedriver || true
    fi
else
    echo "Google Chrome already installed."
fi

echo "=== [4/5] Setting up Python virtual environment ==="
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Run seleniumbase to download matching chromedriver
sbase install chromedriver || true

echo "=== [5/5] Setup complete! ==="
echo ""
echo "Next steps:"
echo "1. Set your Discord webhook in config.py or export DISCORD_WEBHOOK_URL='...'"
echo "2. Test run: source .venv/bin/activate && python main.py --once"
echo "3. Run 24/7: Use systemd (see scraper.service) or run: nohup python main.py > scraper.log 2>&1 &"
