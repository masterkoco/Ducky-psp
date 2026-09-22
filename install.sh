#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "[*] Installing DuckShrink_PSP dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-tk python3-zstandard xdotool

echo "[*] Setting up installation directories..."
sudo mkdir -p /opt/duckyshrink
sudo cp duckyshrink_psp.py /opt/duckyshrink/duckyshrink_psp.py

# Download or copy icon if available
if [ -f "icon.png" ]; then
    sudo cp icon.png /opt/duckyshrink/icon.png
fi

# Create a convenient executable command wrapper in /usr/local/bin
echo "[*] Creating system shortcut..."
sudo tee /usr/local/bin/duckyshrink > /dev/null << 'EOF'
#!/bin/bash
python3 /opt/duckyshrink/duckyshrink_psp.py "$@"
EOF

sudo chmod +x /usr/local/bin/duckyshrink

echo "[*] DuckShrink_PSP installation complete!"
echo "Type 'duckyshrink' in any terminal window to launch the app."
