#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "[*] Installing DuckShrink_PSP dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-tk python3-zstandard xdotool curl

echo "[*] Setting up installation directories..."
sudo mkdir -p /opt/duckshrink

echo "[*] Downloading DuckShrink_PSP files from GitHub..."
sudo curl -s -o /opt/duckshrink/duckshrink_psp.py https://raw.githubusercontent.com/masterkoco/DuckyShrink_psp/refs/heads/main/duckshrink_psp.py
sudo curl -s -o /opt/duckshrink/icon.png https://raw.githubusercontent.com/masterkoco/DuckyShrink_psp/refs/heads/main/icon.png || true
sudo curl -s -o /opt/duckshrink/quack.ogg https://raw.githubusercontent.com/masterkoco/DuckyShrink_psp/refs/heads/main/quack.ogg || true

# Create a convenient executable command wrapper in /usr/local/bin
echo "[*] Creating terminal shortcut..."
sudo tee /usr/local/bin/duckshrink > /dev/null << 'EOF'
#!/bin/bash
python3 /opt/duckshrink/duckshrink_psp.py "$@"
EOF

sudo chmod +x /usr/local/bin/duckshrink

# Create the desktop application menu shortcut
echo "[*] Creating desktop menu launcher..."
sudo tee /usr/share/applications/duckshrink.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=DuckShrink PSP
Comment=Batch compress and rename PSP ISOs
Exec=duckshrink
Icon=/opt/duckshrink/icon.png
Terminal=false
Type=Application
Categories=Utility;Game;
EOF

echo "[*] DuckShrink_PSP installation complete!"
echo "Type 'duckshrink' in a terminal or find it in your application menu to launch the app."
