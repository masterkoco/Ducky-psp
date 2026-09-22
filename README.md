# 🦆 DuckShrink_psp
A cyberpunk-styled, multithreaded PSP ISO/CSO/ZSO batch compressor, metadata reader, and custom file renamer built for Linux Mint.

## 🚀 One-Line Installer
Open your terminal and paste the following command to automatically install DuckyISO and all of its dependencies:
```bash
<(curl -s https://raw.githubusercontent.com/masterkoco/DuckyShrink_psp/main/install.sh)
```
## TO UNINSTALL ON LINUX RUN
```bash
sudo rm -rf /opt/duckshrink
sudo rm /usr/local/bin/duckshrink
```
🪟 Running on Windows

An official standalone Windows installer (.exe) is coming soon! In the meantime, you can easily run the application directly from source on Windows:
Prerequisites

   Python 3.13+ installed on your system (make sure to check "Add Python to PATH" during installation).
   Install the required Python dependencies via command prompt / PowerShell:
```bash
pip install zstandard tkinterdnd2
```
Running the App

   Download or clone the repository[cite: 1].
   Open your terminal or command prompt inside the project folder.
   Launch the application:
```bash
python duckshrink_psp.py
```
🛠️ Configuration & Logs
   Settings & Cache: DuckShrink_PSP automatically saves your preferences, history cache, and undo logs locally (duckshrink_config.json, duckshrink_history.json)[cite: 1].
   Activity Logs: Detailed logs and error reports are automatically written to the logs/ directory[cite: 1].

✨ Features
 
  Universal Formats: Compresses and decompresses .iso, .cso, .zso, and .dax PSP game images.
  
  Smart Metadata Renaming: Automatically reads internal PARAM.SFO headers to rename games into clean formats (e.g., Title [GameID]).

  Custom Case Styling: Toggle between ALL CAPS, title case, snake_case, or normal case.

  Flexible Workflow Modes: Choose between renaming files instantly (Rename NOW) or cleaning up names automatically right after compression (After Compress).

  Drag and Drop Support: Drop individual game files or entire directories straight into the application window.

  Interactive Themes: Cycle through Cyberpunk, Matrix Amber, and Synthwave Purple visual themes on the fly.

  Victory Quack: Plays a celebratory duck quack audio cue when your batch queue finishes successfully!

📦 Requirements & Manual Setup

If you prefer running it manually without the installer, ensure you have Python 3, Tkinter, and Zstandard installed:
```bash
sudo apt install python3-tk python3-zstandard pulseaudio-utils python3-pip
pip install tkinterdnd2 --break-system-packages
python3 duckshrink_psp.py
```
