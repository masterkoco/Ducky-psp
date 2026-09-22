#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "[*] Installing DuckShrink_PSP dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-tk python3-zstandard xdotool

echo "[*] Setting up installation directories..."
sudo mkdir -p /opt/duckshrink
sudo cp duckshrink_psp.py /opt/duckshrink/duckshrink_psp.py

# Download or copy icon if available
if [ -f "icon.png" ]; then
    sudo cp icon.png /opt/duckshrink/icon.png
fi

# Create a convenient executable command wrapper in /usr/local/bin
echo "[*] Creating system shortcut..."
sudo tee /usr/local/bin/duckshrink > /dev/null << 'EOF'
#!/bin/bash
python3 /opt/duckshrink/duckshrink_psp.py "$@"
EOF

sudo chmod +x /usr/local/bin/duckshrink

echo "[*] DuckShrink_PSP installation complete!"
echo "Type 'duckshrink' in any terminal window to launch the app."
