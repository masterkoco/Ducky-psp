# 🦆 DuckShrink_psp
A cyberpunk-styled, multithreaded PSP ISO/CSO/ZSO batch compressor, metadata reader, and custom file renamer built for Linux Mint.

## 🚀 One-Line Installer
Open your terminal and paste the following command to automatically install DuckyISO and all of its dependencies:

```bash
git clone https://github.com/masterkoco/Ducky-psp.git && cd Ducky-psp && bash install.sh
```
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
python3 ducky_iso.py
```
