#!/bin/bash

# DuckyISO Automated Installer for Linux Mint / Ubuntu
APP_NAME="DuckyISO"
INSTALL_DIR="/opt/duckyiso"
DESKTOP_FILE="$HOME/.local/share/applications/duckyiso.desktop"

echo "=== Installing DuckyISO ==="

# 1. Check for root/sudo privileges
if [ "$EUID" -eq 0 ]; then
  echo "[-] Please run this script as a normal user (without sudo), it will prompt for sudo when necessary."
  exit 1
fi

# 2. Install system dependencies via apt
echo "[*] Installing required system packages..."
sudo apt update
sudo apt install -y python3 python3-tk python3-zstandard pulseaudio-utils python3-pip

# 3. Install Python pip dependencies (tkinterdnd2)
echo "[*] Installing Python GUI packages..."
pip install tkinterdnd2 --break-system-packages --quiet

# 4. Create installation directory & copy files
echo "[*] Setting up application directory at $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp ducky_iso.py "$INSTALL_DIR/"

if [ -f "quack.ogg" ]; then
    sudo cp quack.ogg "$INSTALL_DIR/"
fi

# Copy icon if provided (supports icon.ico or icon.png)
ICON_PATH=""
if [ -f "icon.ico" ]; then
    sudo cp icon.ico "$INSTALL_DIR/"
    ICON_PATH="$INSTALL_DIR/icon.ico"
elif [ -f "icon.png" ]; then
    sudo cp icon.png "$INSTALL_DIR/"
    ICON_PATH="$INSTALL_DIR/icon.png"
else
    ICON_PATH="utilities-terminal"
fi

sudo chmod +x "$INSTALL_DIR/ducky_iso.py"

# 5. Create Desktop Menu Shortcut Entry with custom icon
echo "[*] Creating application launcher..."
mkdir -p "$HOME/.local/share/applications"

cat << EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=DuckyISO
Comment=PSP ISO/CSO/ZSO Batch Compressor & Renamer
Exec=python3 $INSTALL_DIR/ducky_iso.py
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Utility;Game;
EOF

chmod +x "$DESKTOP_FILE"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "=== INSTALLATION COMPLETE! ==="
echo "You can now find 'DuckyISO' with your custom icon in your Linux Mint application menu!"
