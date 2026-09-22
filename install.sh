#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "[*] Installing DuckShrink_PSP dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-tk python3-zstandard xdotool curl

echo "[*] Setting up installation directories..."
sudo mkdir -p /opt/duckshrink

echo "[*] Downloading DuckShrink_PSP script from GitHub..."
sudo curl -s -o /opt/duckshrink/duckshrink_psp.py https://raw.githubusercontent.com/masterkoco/DuckShrink_PSP/main/duckshrink_psp.py

# Optional: Download icon if you have it in your repo
sudo curl -s -o /opt/duckshrink/icon.png https://raw.githubusercontent.com/masterkoco/DuckShrink_PSP/main/icon.png || true

# Create a convenient executable command wrapper in /usr/local/bin
echo "[*] Creating system shortcut..."
sudo tee /usr/local/bin/duckshrink > /dev/null << 'EOF'
#!/bin/bash
python3 /opt/duckshrink/duckshrink_psp.py "$@"
EOF

sudo chmod +x /usr/local/bin/duckshrink

echo "[*] DuckShrink_PSP installation complete!"
echo "Type 'duckshrink' in any terminal window to launch the app."
