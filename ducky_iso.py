import os
import json
import zlib
import random
import struct
import time
import re
import threading
import subprocess
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

try:
    import zstandard as zstd
except ImportError:
    zstd = None

CONFIG_FILE = "ducky_config.json"

class ISOCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DuckyISO // PSP Batch Compressor v7.2")
        self.root.geometry("640x930")
        
        # Robust Window / Taskbar Icon Loader for Linux Mint
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            for icon_name in ("icon.png", "icon.ico"):
                icon_path = os.path.join(base_dir, icon_name)
                if not os.path.exists(icon_path):
                    icon_path = os.path.join("/opt/duckyiso", icon_name)
                    
                if os.path.exists(icon_path):
                    try:
                        img = tk.PhotoImage(file=icon_path)
                        self.root.iconphoto(True, img)
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        # Color Palettes (Cyberpunk Themes)
        self.themes = {
            "Neon Cyberpunk": {
                "bg": "#05050A", "panel": "#0B0E14", "cyan": "#08F7FE", 
                "pink": "#FE53BB", "yellow": "#F5D300", "text": "#E0E0E0"
            },
            "Matrix Amber": {
                "bg": "#0A0500", "panel": "#140B00", "cyan": "#FFB000", 
                "pink": "#FF4500", "yellow": "#FFEE00", "text": "#FFD700"
            },
            "Synthwave Purple": {
                "bg": "#0D0714", "panel": "#1A0F26", "cyan": "#00FFFF", 
                "pink": "#FF007F", "yellow": "#9900FF", "text": "#F0E6FA"
            }
        }
        self.current_theme_name = "Neon Cyberpunk"
        self.apply_theme_colors()
        
        self.file_paths = []
        self.custom_output_dir = ""
        self.last_dir = os.path.expanduser("~")
        self.is_converting = False
        self.cancel_flag = False
        
        # Load saved configuration settings
        self.load_config()
        
        # Auto-download Duck Quack
        self.sound_file = "quack.ogg"
        self._ensure_quack_downloaded()
        
        # UI Styling (ttk)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.update_ttk_styles()
        
        # Header Frame
        header_frame = tk.Frame(root, bg=self.bg_color)
        header_frame.pack(pady=(8, 2), fill="x", padx=20)
        
        tk.Label(header_frame, text="DUCKY_ISO [v7.2]", font=("Monospace", 15, "bold"), bg=self.bg_color, fg=self.cyan).pack(side=tk.LEFT)
        
        # Theme Switcher Button
        self.btn_theme = tk.Button(header_frame, text="THEME: CYBERPUNK", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow,
                                   activebackground=self.yellow, activeforeground="black", command=self.cycle_theme, relief=tk.SOLID, bd=1, padx=6, pady=2)
        self.btn_theme.pack(side=tk.RIGHT)
        
        tk.Label(root, text=">> DRAG & DROP FILES/FOLDERS OR USE SELECTORS", font=("Monospace", 8), bg=self.bg_color, fg=self.yellow).pack(pady=(0, 4))
        
        # File/Folder Selection Buttons
        frame_browse = tk.Frame(root, bg=self.bg_color)
        frame_browse.pack(pady=3)
        
        self.btn_browse_file = tk.Button(frame_browse, text="[ SELECT FILE(S) ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                    activebackground=self.cyan, activeforeground="black", command=self.browse_files, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_browse_file.pack(side=tk.LEFT, padx=5)

        self.btn_browse_folder = tk.Button(frame_browse, text="[ SELECT FOLDER ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.pink, 
                                    activebackground=self.pink, activeforeground="black", command=self.browse_folder, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_browse_folder.pack(side=tk.LEFT, padx=5)

        self.btn_test_meta = tk.Button(frame_browse, text="[ TEST METADATA ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.yellow, 
                                       activebackground=self.yellow, activeforeground="black", command=self.test_metadata, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_test_meta.pack(side=tk.LEFT, padx=5)
        
        self.lbl_file = tk.Label(root, text="STATUS: AWAITING INPUT", bg=self.bg_color, fg="#555555", font=("Monospace", 9, "bold"))
        self.lbl_file.pack(pady=3)
        
        # Output Path Configuration Frame
        self.frame_output = tk.Frame(root, bg=self.panel_bg, highlightbackground=self.pink, highlightthickness=1, padx=8, pady=4)
        self.frame_output.pack(pady=3, fill="x", padx=30)
        
        out_display_text = f"OUTPUT: {self.custom_output_dir[:30]}..." if self.custom_output_dir else "OUTPUT: /.../compressed (Auto)"
        self.lbl_out_title = tk.Label(self.frame_output, text=out_display_text, bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8, "bold"), anchor="w")
        self.lbl_out_title.pack(side=tk.LEFT, fill="x", expand=True)
        
        self.btn_change_out = tk.Button(self.frame_output, text="[ CHANGE ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.pink,
                                        activebackground=self.pink, activeforeground="black", command=self.change_output_dir, relief=tk.SOLID, bd=1, padx=6, pady=2)
        self.btn_change_out.pack(side=tk.RIGHT)

        # Smart Renaming Frame
        self.frame_rename = tk.Frame(root, bg=self.panel_bg, highlightbackground=self.yellow, highlightthickness=1, padx=8, pady=4)
        self.frame_rename.pack(pady=3, fill="x", padx=30)
        
        tk.Label(self.frame_rename, text="RENAME SETTINGS:", bg=self.panel_bg, fg=self.yellow, font=("Monospace", 9, "bold")).pack(anchor="w", padx=2)
        
        ren_opts_frame = tk.Frame(self.frame_rename, bg=self.panel_bg)
        ren_opts_frame.pack(fill="x", pady=2)
        
        self.rename_mode_var = tk.StringVar(value=self.saved_settings.get("rename_mode", "OFF"))
        tk.Radiobutton(ren_opts_frame, text="Off", variable=self.rename_mode_var, value="OFF", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, font=("Monospace", 8, "bold"), command=self.save_config).pack(side=tk.LEFT, padx=4)
        tk.Radiobutton(ren_opts_frame, text="After Compress", variable=self.rename_mode_var, value="AFTER", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, font=("Monospace", 8, "bold"), command=self.save_config).pack(side=tk.LEFT, padx=4)
        tk.Radiobutton(ren_opts_frame, text="Rename NOW", variable=self.rename_mode_var, value="NOW", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, font=("Monospace", 8, "bold"), command=self.save_config).pack(side=tk.LEFT, padx=4)

        ren_sub_frame = tk.Frame(self.frame_rename, bg=self.panel_bg)
        ren_sub_frame.pack(fill="x", pady=2)
        
        tk.Label(ren_sub_frame, text="Pattern:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8)).pack(side=tk.LEFT, padx=2)
        self.pattern_var = tk.StringVar(value=self.saved_settings.get("pattern", "Title Only"))
        self.pattern_dropdown = ttk.Combobox(ren_sub_frame, textvariable=self.pattern_var, values=["Title Only", "Title [GameID]", "[GameID] Title", "Title - GameID"], state="readonly", width=15)
        self.pattern_dropdown.pack(side=tk.LEFT, padx=3)
        self.pattern_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())
        
        tk.Label(ren_sub_frame, text="Case:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8)).pack(side=tk.LEFT, padx=4)
        self.case_var = tk.StringVar(value=self.saved_settings.get("case", "Normal"))
        self.case_dropdown = ttk.Combobox(ren_sub_frame, textvariable=self.case_var, values=["Normal", "ALL CAPS", "all lowercase", "Title Case", "snake_case"], state="readonly", width=12)
        self.case_dropdown.pack(side=tk.LEFT, padx=3)
        self.case_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        # Format Selection
        self.frame_format = tk.Frame(root, bg=self.panel_bg, highlightbackground=self.cyan, highlightthickness=1, padx=8, pady=4)
        self.frame_format.pack(pady=4, fill="x", padx=30)
        
        self.lbl_fmt_title = tk.Label(self.frame_format, text="OUTPUT_FORMAT:", bg=self.panel_bg, fg=self.yellow, font=("Monospace", 9, "bold"))
        self.lbl_fmt_title.pack(side=tk.LEFT, padx=6)
        
        self.format_var = tk.StringVar(value=self.saved_settings.get("format", "ZSO"))
        self.rb_zso = tk.Radiobutton(self.frame_format, text="ZSO (ZSTD)", variable=self.format_var, value="ZSO", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, activebackground=self.panel_bg, activeforeground=self.cyan, font=("Monospace", 9, "bold"), command=self.on_format_change)
        self.rb_zso.pack(side=tk.LEFT, padx=4)
        self.rb_cso = tk.Radiobutton(self.frame_format, text="CSO (ZLIB)", variable=self.format_var, value="CSO", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, activebackground=self.panel_bg, activeforeground=self.cyan, font=("Monospace", 9, "bold"), command=self.on_format_change)
        self.rb_cso.pack(side=tk.LEFT, padx=4)
        
        # Compression Slider
        frame_slider = tk.Frame(root, bg=self.bg_color)
        frame_slider.pack(pady=3, fill="x", padx=30)
        
        slider_lvl = self.saved_settings.get("compression_level", 5)
        self.lbl_slider = tk.Label(frame_slider, text=f"COMPRESSION_OVERRIDE: [ {slider_lvl} ]", bg=self.bg_color, fg=self.text_color, font=("Monospace", 9, "bold"))
        self.lbl_slider.pack()
        
        self.level_var = tk.IntVar(value=slider_lvl)
        self.slider = tk.Scale(frame_slider, from_=1, to=10, orient=tk.HORIZONTAL, variable=self.level_var, 
                               bg=self.bg_color, fg=self.cyan, troughcolor=self.panel_bg, 
                               activebackground=self.pink, highlightthickness=0, command=self.on_slider_change)
        self.slider.pack(fill="x")
        
        # Size Estimate Display
        self.lbl_estimate = tk.Label(root, text="ESTIMATED YIELD: -- MB ?", font=("Monospace", 10, "bold"), bg=self.bg_color, fg=self.yellow)
        self.lbl_estimate.pack(pady=3)
        
        # Action Buttons
        frame_actions = tk.Frame(root, bg=self.bg_color)
        frame_actions.pack(pady=3)
        
        self.btn_convert = tk.Button(frame_actions, text="> EXECUTE <", font=("Monospace", 11, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                     activebackground=self.cyan, activeforeground="black", command=self.start_action, relief=tk.SOLID, bd=1, padx=16, pady=5)
        self.btn_convert.pack(side=tk.LEFT, padx=10)

        self.btn_cancel = tk.Button(frame_actions, text="> ABORT <", font=("Monospace", 11, "bold"), bg=self.panel_bg, fg=self.pink, 
                                    activebackground=self.pink, activeforeground="black", command=self.cancel_conversion, relief=tk.SOLID, bd=1, padx=16, pady=5, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=10)
        
        # Progress Tracking
        self.lbl_status = tk.Label(root, text="SYSTEM IDLE", bg=self.bg_color, fg=self.text_color, font=("Monospace", 9, "bold"))
        self.lbl_status.pack(pady=2)
        
        self.lbl_pbar1 = tk.Label(root, text="[ CURRENT THREAD ]", bg=self.bg_color, fg=self.cyan, font=("Monospace", 8))
        self.lbl_pbar1.pack()
        self.progress_file = ttk.Progressbar(root, orient="horizontal", length=440, mode="determinate", style="Cyan.Horizontal.TProgressbar")
        self.progress_file.pack(pady=1)

        self.lbl_pbar2 = tk.Label(root, text="[ MASTER BATCH ]", bg=self.bg_color, fg=self.pink, font=("Monospace", 8))
        self.lbl_pbar2.pack(pady=(3,0))
        self.progress_batch = ttk.Progressbar(root, orient="horizontal", length=440, mode="determinate", style="Pink.Horizontal.TProgressbar")
        self.progress_batch.pack(pady=1)

        # Terminal Console Box at Bottom
        term_frame = tk.Frame(root, bg="#000000", highlightbackground=self.cyan, highlightthickness=1)
        term_frame.pack(pady=8, fill="both", expand=True, padx=25)
        
        tk.Label(term_frame, text="[ TERMINAL OUTPUT LOG ]", bg="#000000", fg=self.cyan, font=("Monospace", 8, "bold")).pack(anchor="w", padx=5)
        
        self.term_box = tk.Text(term_frame, bg="#000000", fg="#00FF66", font=("Monospace", 8), height=6, bd=0, highlightthickness=0)
        self.term_box.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=2)
        self.term_box.config(state=tk.DISABLED)
        
        term_scroll = tk.Scrollbar(term_frame, command=self.term_box.yview, bg="#000000")
        term_scroll.pack(side=tk.RIGHT, fill="y")
        self.term_box.config(yscrollcommand=term_scroll.set)

        if TkinterDnD:
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self.handle_drop)
            except Exception:
                pass

        self.log_term("DuckyISO v7.2 Initialized with Explicit Icon Binding.")

    def load_config(self):
        self.saved_settings = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.saved_settings = json.load(f)
                    self.custom_output_dir = self.saved_settings.get("custom_output_dir", "")
                    self.last_dir = self.saved_settings.get("last_dir", os.path.expanduser("~"))
            except Exception:
                pass

    def save_config(self):
        settings = {
            "custom_output_dir": self.custom_output_dir,
            "last_dir": self.last_dir,
            "rename_mode": self.rename_mode_var.get(),
            "pattern": self.pattern_var.get(),
            "case": self.case_var.get(),
            "format": self.format_var.get(),
            "compression_level": self.level_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception:
            pass

    def log_term(self, text):
        self.term_box.config(state=tk.NORMAL)
        self.term_box.insert(tk.END, f"> {text}\n")
        self.term_box.see(tk.END)
        self.term_box.config(state=tk.DISABLED)

    def apply_theme_colors(self):
        t = self.themes[self.current_theme_name]
        self.bg_color = t["bg"]
        self.panel_bg = t["panel"]
        self.cyan = t["cyan"]
        self.pink = t["pink"]
        self.yellow = t["yellow"]
        self.text_color = t["text"]
        if hasattr(self, 'root'):
            self.root.configure(bg=self.bg_color)

    def update_ttk_styles(self):
        self.style.configure("Cyan.Horizontal.TProgressbar", thickness=12, background=self.cyan, troughcolor=self.bg_color, bordercolor=self.cyan)
        self.style.configure("Pink.Horizontal.TProgressbar", thickness=12, background=self.pink, troughcolor=self.bg_color, bordercolor=self.pink)

    def cycle_theme(self):
        names = list(self.themes.keys())
        next_idx = (names.index(self.current_theme_name) + 1) % len(names)
        self.current_theme_name = names[next_idx]
        self.apply_theme_colors()
        self.update_ttk_styles()
        
        self.btn_theme.config(text=f"THEME: {self.current_theme_name.split()[0].upper()}")
        self.root.configure(bg=self.bg_color)
        for widget in self.root.winfo_children():
            try:
                widget.configure(bg=self.bg_color)
            except Exception:
                pass
        self.frame_output.configure(bg=self.panel_bg, highlightbackground=self.pink)
        self.lbl_out_title.configure(bg=self.panel_bg, fg=self.text_color)
        self.btn_change_out.configure(bg=self.bg_color, fg=self.pink, activebackground=self.pink)
        
        self.frame_rename.configure(bg=self.panel_bg, highlightbackground=self.yellow)
        for child in self.frame_rename.winfo_children():
            try:
                child.configure(bg=self.panel_bg, fg=self.text_color)
            except Exception:
                pass

        self.frame_format.configure(bg=self.panel_bg, highlightbackground=self.cyan)
        self.lbl_fmt_title.configure(bg=self.panel_bg, fg=self.yellow)
        self.rb_zso.configure(bg=self.panel_bg, fg=self.text_color, activebackground=self.panel_bg, activeforeground=self.cyan)
        self.rb_cso.configure(bg=self.panel_bg, fg=self.text_color, activebackground=self.panel_bg, activeforeground=self.cyan)
        self.btn_browse_file.configure(bg=self.panel_bg, fg=self.cyan, activebackground=self.cyan)
        self.btn_browse_folder.configure(bg=self.panel_bg, fg=self.pink, activebackground=self.pink)
        self.btn_test_meta.configure(bg=self.panel_bg, fg=self.yellow, activebackground=self.yellow)
        self.btn_theme.configure(bg=self.panel_bg, fg=self.yellow, activebackground=self.yellow)
        self.btn_convert.configure(bg=self.panel_bg, fg=self.cyan, activebackground=self.cyan)
        self.btn_cancel.configure(bg=self.panel_bg, fg=self.pink, activebackground=self.pink)
        self.lbl_pbar1.configure(bg=self.bg_color, fg=self.cyan)
        self.lbl_pbar2.configure(bg=self.bg_color, fg=self.pink)
        self.log_term(f"Switched theme to {self.current_theme_name}")

    def _ensure_quack_downloaded(self):
        if not os.path.exists(self.sound_file):
            try:
                url = "https://actions.google.com/sounds/v1/animals/duck_quack.ogg"
                urllib.request.urlretrieve(url, self.sound_file)
            except Exception:
                pass 

    def _play_quack(self):
        if os.path.exists(self.sound_file):
            try:
                subprocess.Popen(["paplay", self.sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def change_output_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.last_dir, title="SELECT CUSTOM OUTPUT DIRECTORY")
        if dir_path:
            self.custom_output_dir = dir_path
            self.last_dir = dir_path
            short_path = (dir_path[:30] + '...') if len(dir_path) > 30 else dir_path
            self.lbl_out_title.config(text=f"OUTPUT: {short_path} (Custom)")
            self.log_term(f"Output directory set to: {dir_path}")
            self.save_config()

    def handle_drop(self, event):
        raw_data = event.data
        paths = self.root.tk.splitlist(raw_data)
        found_files = []
        valid_exts = ('.iso', '.cso', '.zso', '.dax')
        
        for p in paths:
            if os.path.isdir(p):
                self.last_dir = p
                self.log_term(f"Scanning dropped directory: {p}")
                for root_dir, _, files in os.walk(p):
                    for file in files:
                        if file.lower().endswith(valid_exts):
                            found_files.append(os.path.join(root_dir, file))
            elif os.path.isfile(p) and p.lower().endswith(valid_exts):
                found_files.append(p)
                self.last_dir = os.path.dirname(p)
                
        if found_files:
            self.file_paths = found_files
            self._update_file_status()
            self.log_term(f"Successfully loaded {len(found_files)} file(s) via Drag & Drop.")
            self.save_config()
        else:
            messagebox.showwarning("INVALID DROP", "No valid PSP game images found in drop target.")
            self.log_term("Warning: Drop target contained no valid PSP game images.")

    def browse_files(self):
        paths = filedialog.askopenfilenames(initialdir=self.last_dir, filetypes=[("PSP Game Images", "*.iso *.cso *.zso *.dax"), ("All Files", "*.*")])
        if paths:
            self.file_paths = list(paths)
            self.last_dir = os.path.dirname(paths[0])
            self._update_file_status()
            self.log_term(f"Loaded {len(paths)} file(s) via file selector.")
            self.save_config()

    def browse_folder(self):
        folder_path = filedialog.askdirectory(initialdir=self.last_dir, title="SELECT FOLDER CONTAINING GAMES")
        if folder_path:
            self.last_dir = folder_path
            found_files = []
            valid_exts = ('.iso', '.cso', '.zso', '.dax')
            self.log_term(f"Scanning folder: {folder_path}")
            for root_dir, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(valid_exts):
                        found_files.append(os.path.join(root_dir, file))
            if found_files:
                self.file_paths = found_files
                self._update_file_status()
                self.log_term(f"Found and loaded {len(found_files)} game file(s) in folder.")
                self.save_config()
            else:
                messagebox.showinfo("NO DATA FOUND", "No valid PSP game images located in target directory.")
                self.log_term("Scan complete: No game files found.")

    def test_metadata(self):
        if not self.file_paths:
            messagebox.showwarning("NOTICE", "Please select at least one file first to test metadata.")
            return
        
        test_file = self.file_paths[0]
        self.log_term(f"Testing metadata for: {os.path.basename(test_file)}")
        title, game_id = PSPImageReader.get_game_metadata(test_file)
        
        msg = f"File: {os.path.basename(test_file)}\n\n"
        if title:
            msg += f"Detected Title: {title}\n"
            msg += f"Detected Game ID: {game_id}"
            self.log_term(f"Metadata OK -> Title: '{title}' [{game_id}]")
        else:
            msg += "RESULT: Could not locate PARAM.SFO header."
            self.log_term(f"Metadata FAILED for {os.path.basename(test_file)}")
            
        messagebox.showinfo("Metadata Diagnostic", msg)

    def _update_file_status(self):
        total_size_mb = sum(os.path.getsize(p) for p in self.file_paths) / (1024 * 1024)
        file_count = len(self.file_paths)
        self.lbl_file.config(text=f"LOADED: {file_count} NODE(S) | {total_size_mb:.2f} MB", fg=self.cyan)
        if not self.custom_output_dir and self.file_paths:
            self.lbl_out_title.config(text=f"OUTPUT: .../compressed (Auto)")
        self.update_estimate()

    def on_slider_change(self, val):
        self.lbl_slider.config(text=f"COMPRESSION_OVERRIDE: [ {val} ]")
        self.update_estimate()
        self.save_config()

    def on_format_change(self):
        self.update_estimate()
        self.save_config()

    def update_estimate(self, *_):
        if not self.file_paths or self.is_converting:
            return
        fmt = self.format_var.get()
        if fmt == "ZSO" and zstd is None:
            self.lbl_estimate.config(text="ERR: 'python3-zstandard' MISSING", fg=self.pink)
            return
        self.lbl_estimate.config(text="CALCULATING METRICS... ?", fg="#555555")
        threading.Thread(target=self._run_estimate, args=(self.file_paths, fmt, self.level_var.get()), daemon=True).start()
        
    def _run_estimate(self, file_paths, fmt, level):
        try:
            total_est_size = 0
            block_size = 2048
            if fmt == 'CSO':
                c_level = max(1, min(9, int(level * 0.9)))
            else:
                c_level = max(1, min(22, int(level * 2.2)))
                z_comp = zstd.ZstdCompressor(level=c_level)

            sample_file = file_paths[0]
            reader = PSPImageReader(sample_file)
            num_blocks = reader.num_blocks
            
            if num_blocks > 0:
                sample_count = min(150, num_blocks)
                sample_indices = random.sample(range(num_blocks), sample_count)
                orig_bytes, comp_bytes = 0, 0
                for idx in sample_indices:
                    data = reader.read_block(idx)
                    orig_bytes += len(data)
                    if fmt == 'CSO':
                        comp_obj = zlib.compressobj(level=c_level, method=zlib.DEFLATED, wbits=-15)
                        compressed = comp_obj.compress(data) + comp_obj.flush()
                    else:
                        compressed = z_comp.compress(data)
                    comp_bytes += len(data) if len(compressed) >= len(data) else len(compressed)
                ratio = comp_bytes / orig_bytes if orig_bytes > 0 else 1
            else:
                ratio = 1
            reader.close()

            for path in file_paths:
                f_size = os.path.getsize(path)
                r_temp = PSPImageReader(path)
                n_blocks = r_temp.num_blocks
                r_temp.close()
                overhead = 24 + (n_blocks + 1) * 4
                total_est_size += (f_size * ratio) + overhead

            est_size_mb = total_est_size / (1024 * 1024)
            self.root.after(0, lambda: self.lbl_estimate.config(text=f"ESTIMATED YIELD: ~{est_size_mb:.2f} MB ?", fg=self.yellow))
        except Exception:
            self.root.after(0, lambda: self.lbl_estimate.config(text="ESTIMATE_FAIL ?", fg=self.pink))

    def format_filename(self, title, game_id, ext):
        clean_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
        pattern = self.pattern_var.get()
        case_style = self.case_var.get()

        if case_style == "ALL CAPS":
            clean_title = clean_title.upper()
            if game_id: game_id = game_id.upper()
        elif case_style == "all lowercase":
            clean_title = clean_title.lower()
            if game_id: game_id = game_id.lower()
        elif case_style == "Title Case":
            clean_title = clean_title.title()
        elif case_style == "snake_case":
            clean_title = clean_title.lower().replace(" ", "_")

        if pattern == "Title [GameID]" and game_id:
            base = f"{clean_title} [{game_id}]"
        elif pattern == "[GameID] Title" and game_id:
            base = f"[{game_id}] {clean_title}"
        elif pattern == "Title - GameID" and game_id:
            base = f"{clean_title} - {game_id}"
        else:
            base = clean_title

        return f"{base}{ext}"

    def start_action(self):
        if not self.file_paths:
            messagebox.showerror("SYS_ERROR", "NO DATA BLOCKS SELECTED.")
            return

        rename_mode = self.rename_mode_var.get()
        if rename_mode == "NOW":
            self.log_term("Starting instant batch rename protocol...")
            self.start_instant_rename()
        else:
            self.log_term(f"Starting batch compression protocol (Format: {self.format_var.get()})...")
            self.start_conversion()

    def start_instant_rename(self):
        self.is_converting = True
        self.cancel_flag = False
        self.btn_convert.config(state=tk.DISABLED)
        self.slider.config(state=tk.DISABLED)
        self.btn_browse_file.config(state=tk.DISABLED)
        self.btn_browse_folder.config(state=tk.DISABLED)
        self.btn_change_out.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        
        threading.Thread(target=self._run_instant_rename, daemon=True).start()

    def _run_instant_rename(self):
        total_files = len(self.file_paths)
        self.progress_batch["maximum"] = total_files
        renamed_count = 0
        skipped_count = 0

        for idx, path in enumerate(self.file_paths):
            if self.cancel_flag: break
            try:
                dirname, filename = os.path.split(path)
                ext = os.path.splitext(filename)[1]
                
                game_title, game_id = PSPImageReader.get_game_metadata(path)
                if not game_title:
                    self.log_term(f"SKIP: Could not read metadata for {filename}")
                    skipped_count += 1
                    continue
                
                new_name = self.format_filename(game_title, game_id, ext)
                new_path = os.path.join(dirname, new_name)
                
                if new_path != path and os.path.exists(new_path):
                    base_n, ext_n = os.path.splitext(new_name)
                    new_name = f"{base_n}_{random.randint(100,999)}{ext_n}"
                    new_path = os.path.join(dirname, new_name)

                if new_path != path:
                    os.rename(path, new_path)
                    renamed_count += 1
                    self.log_term(f"RENAMED: '{filename}' -> '{new_name}'")
                
                self.progress_batch["value"] = idx + 1
            except Exception as e:
                self.log_term(f"ERROR renaming {filename}: {str(e)}")
                skipped_count += 1

        self.root.after(0, lambda: self._finalize_rename_ui(renamed_count, skipped_count))

    def _finalize_rename_ui(self, count, skipped):
        self.is_converting = False
        self.btn_convert.config(state=tk.NORMAL)
        self.slider.config(state=tk.NORMAL)
        self.btn_browse_file.config(state=tk.NORMAL)
        self.btn_browse_folder.config(state=tk.NORMAL)
        self.btn_change_out.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.lbl_status.config(text=f"RENAME COMPLETE: {count} UPDATED, {skipped} SKIPPED", fg=self.cyan)
        self._play_quack()
        
        summary_msg = f"Rename Operation Finished!\n\nSuccessfully Renamed: {count}\nSkipped / Failed: {skipped}"
        self.log_term(summary_msg.replace('\n', ' // '))
        messagebox.showinfo("Operation Complete", summary_msg)
        
        self.file_paths = []
        self.lbl_file.config(text="STATUS: AWAITING INPUT", fg="#555555")

    def start_conversion(self):
        fmt = self.format_var.get()
        if fmt == "ZSO" and zstd is None:
            messagebox.showerror("DEPENDENCY_MISSING", "REQUIRES: apt install python3-zstandard")
            return
            
        rename_mode = self.rename_mode_var.get()
        target_data = []
        
        for path in self.file_paths:
            base_ext = os.path.splitext(path)[1].lower()
            out_ext = f".{fmt.lower()}"
            
            if rename_mode == "AFTER":
                game_title, game_id = PSPImageReader.get_game_metadata(path)
                if game_title:
                    base_name = self.format_filename(game_title, game_id, out_ext)
                else:
                    base_name = os.path.basename(path).replace(base_ext, out_ext)
            else:
                base_name = os.path.basename(path).replace(base_ext, out_ext)
            
            if self.custom_output_dir:
                out_dir = self.custom_output_dir
            else:
                out_dir = os.path.join(os.path.dirname(path), "compressed")
                
            os.makedirs(out_dir, exist_ok=True)
            target_data.append((path, os.path.join(out_dir, base_name)))
            
        self.is_converting = True
        self.cancel_flag = False
        
        self.btn_convert.config(state=tk.DISABLED)
        self.slider.config(state=tk.DISABLED)
        self.btn_browse_file.config(state=tk.DISABLED)
        self.btn_browse_folder.config(state=tk.DISABLED)
        self.btn_change_out.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        
        self.progress_batch["maximum"] = len(target_data)
        self.progress_batch["value"] = 0
        
        threading.Thread(target=self._run_batch_conversion, args=(target_data, fmt, self.level_var.get()), daemon=True).start()

    def cancel_conversion(self):
        if self.is_converting:
            self.cancel_flag = True
            self.btn_cancel.config(state=tk.DISABLED)
            self.lbl_status.config(text="SIGINT RECEIVED. PURGING...", fg=self.pink)
            self.log_term("Abort signal sent by user. Cleaning up...")

    def update_ui_progress(self, current_file, total_files, current_block, total_blocks, filename, speed_str):
        self.progress_file["maximum"] = total_blocks
        self.progress_file["value"] = current_block
        self.progress_batch["value"] = current_file
        percent = (current_block / total_blocks) * 100 if total_blocks > 0 else 0
        self.lbl_status.config(text=f"[{current_file + 1}/{total_files}] {filename} // {percent:.1f}% ({speed_str})", fg=self.cyan)

    def _run_batch_conversion(self, target_data, fmt, level):
        total_files = len(target_data)
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for file_idx, (in_path, out_path) in enumerate(target_data):
            if self.cancel_flag: break
                
            filename = os.path.basename(in_path)
            out_filename = os.path.basename(out_path)
            
            # SMART RESUME CHECK
            if os.path.exists(out_path):
                try:
                    if os.path.getsize(out_path) > 1024:
                        self.log_term(f"RESUME: Skipping '{out_filename}' (already fully compressed).")
                        skip_count += 1
                        self.root.after(0, self.update_ui_progress, file_idx, total_files, 100, 100, filename, "SKIPPED")
                        continue
                except Exception:
                    pass

            self.log_term(f"Processing [{file_idx+1}/{total_files}]: {filename} -> {out_filename}")
            try:
                reader = PSPImageReader(in_path)
                num_blocks = reader.num_blocks
                file_size = reader.total_size
                block_size = reader.block_size
                
                header_size = 24
                index_size = (num_blocks + 1) * 4
                
                if fmt == 'CSO':
                    c_level = max(1, min(9, int(level * 0.9)))
                else:
                    c_level = max(1, min(22, int(level * 2.2)))
                    z_comp = zstd.ZstdCompressor(level=c_level)
                    
                index_table = []
                write_pos = header_size + index_size
                
                start_time = time.time()
                bytes_processed = 0
                
                with open(out_path, 'wb') as f_out:
                    f_out.seek(write_pos) 
                    
                    for i in range(num_blocks):
                        if self.cancel_flag: break
                        data = reader.read_block(i)
                        if not data: break
                        bytes_processed += len(data)
                        
                        if fmt == 'CSO':
                            comp_obj = zlib.compressobj(level=c_level, method=zlib.DEFLATED, wbits=-15)
                            compressed = comp_obj.compress(data) + comp_obj.flush()
                        else:
                            compressed = z_comp.compress(data)
                            
                        if len(compressed) >= len(data):
                            entry = write_pos | 0x80000000 
                            f_out.write(data)
                            write_pos += len(data)
                        else:
                            entry = write_pos
                            f_out.write(compressed)
                            write_pos += len(compressed)
                            
                        index_table.append(entry)
                        
                        if i % 300 == 0 or i == num_blocks - 1:
                            elapsed = time.time() - start_time
                            speed = (bytes_processed / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                            speed_str = f"{speed:.1f} MB/s"
                            self.root.after(0, self.update_ui_progress, file_idx, total_files, i, num_blocks, filename, speed_str)
                        
                    if self.cancel_flag: 
                        reader.close()
                        break
                        
                    index_table.append(write_pos)
                    f_out.seek(0)
                    f_out.write(b'CISO' if fmt == 'CSO' else b'ZISO')
                    f_out.write(header_size.to_bytes(4, 'little'))
                    f_out.write(file_size.to_bytes(8, 'little'))
                    f_out.write(block_size.to_bytes(4, 'little'))
                    f_out.write(b'\x01\x00\x00\x00')
                    
                    for entry in index_table:
                        f_out.write(entry.to_bytes(4, 'little'))
                        
                reader.close()
                success_count += 1
                self.log_term(f"Completed successfully: {filename}")
                self.root.after(0, self.update_ui_progress, file_idx, total_files, num_blocks, num_blocks, filename, "DONE")
                
            except Exception as e:
                fail_count += 1
                err_msg = str(e)
                self.log_term(f"ERROR on {filename}: {err_msg}")
                self.root.after(0, lambda err=err_msg: messagebox.showerror("SYS_ERROR", f"CRASH ON {filename}:\n{err}"))
                if os.path.exists(out_path):
                    os.remove(out_path)
                    
            if self.cancel_flag and os.path.exists(out_path):
                os.remove(out_path)
                
        self.root.after(0, lambda: self._finalize_ui(success_count, skip_count, fail_count))
            
    def _finalize_ui(self, success_count=0, skip_count=0, fail_count=0):
        if self.cancel_flag:
            self.lbl_status.config(text="PROCESS ABORTED.", fg=self.pink)
            self.log_term("Batch process was aborted by user.")
        else:
            self.lbl_status.config(text="> ALL PROCESSES COMPLETE <", fg=self.cyan)
            self.progress_batch["value"] = self.progress_batch["maximum"]
            self._play_quack()
            
            summary_msg = f"Batch Compression Finished!\n\nSuccessful: {success_count}\nSkipped (Already Done): {skip_count}\nFailed / Errored: {fail_count}"
            self.log_term(summary_msg.replace('\n', ' // '))
            messagebox.showinfo("Operation Complete", summary_msg)
            
        self.is_converting = False
        self.btn_convert.config(state=tk.NORMAL)
        self.slider.config(state=tk.NORMAL)
        self.btn_browse_file.config(state=tk.NORMAL)
        self.btn_browse_folder.config(state=tk.NORMAL)
        self.btn_change_out.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.update_estimate()


class PSPImageReader:
    """Extension-aware parser that correctly decodes raw ISOs and compressed CSO/ZSO/DAX formats to find PARAM.SFO."""
    def __init__(self, filepath):
        self.filepath = filepath
        self.f = open(filepath, 'rb')
        self.f.seek(0, os.SEEK_END)
        self.file_size = self.f.tell()
        self.f.seek(0)
        
        ext = os.path.splitext(filepath)[1].lower()
        magic = self.f.read(4)
        
        if magic in (b'CISO', b'ZISO') or ext in ('.cso', '.zso', '.dax'):
            self.is_compressed = True
            if magic in (b'CISO', b'ZISO'):
                header_size = struct.unpack('<I', self.f.read(4))[0]
                self.total_size = struct.unpack('<Q', self.f.read(8))[0]
                self.block_size = struct.unpack('<I', self.f.read(4))[0]
                self.ver = struct.unpack('B', self.f.read(1))[0]
                self.align = struct.unpack('B', self.f.read(1))[0]
                self.f.read(2)
            else:
                self.f.seek(0)
                self.f.read(4)
                self.f.read(4)
                self.total_size = struct.unpack('<Q', self.f.read(8))[0]
                self.block_size = struct.unpack('<I', self.f.read(4))[0]
                self.ver = 1
                self.align = 0
                
            self.num_blocks = (self.total_size + self.block_size - 1) // self.block_size
            self.index_table = []
            
            self.f.seek(24)
            for _ in range(self.num_blocks + 1):
                data_bytes = self.f.read(4)
                if len(data_bytes) < 4: break
                self.index_table.append(struct.unpack('<I', data_bytes)[0])
        else:
            self.is_compressed = False
            self.total_size = self.file_size
            self.block_size = 2048
            self.num_blocks = (self.total_size + self.block_size - 1) // self.block_size

    def read_block(self, idx):
        if not self.is_compressed or idx >= len(self.index_table) - 1:
            self.f.seek(idx * self.block_size)
            return self.f.read(self.block_size)
        else:
            try:
                entry = self.index_table[idx]
                next_entry = self.index_table[idx + 1]
                is_raw = (entry & 0x80000000) != 0
                start_pos = entry & 0x7FFFFFFF
                end_pos = next_entry & 0x7FFFFFFF
                
                self.f.seek(start_pos)
                compressed_data = self.f.read(end_pos - start_pos)
                if is_raw or start_pos == end_pos or not compressed_data:
                    return compressed_data
                
                self.f.seek(0)
                fmt_magic = self.f.read(4)
                
                if fmt_magic == b'CISO' or self.filepath.lower().endswith('.cso'):
                    try:
                        return zlib.decompress(compressed_data, wbits=-15)
                    except Exception:
                        return compressed_data
                elif fmt_magic == b'ZISO' or self.filepath.lower().endswith('.zso'):
                    if zstd is not None:
                        try:
                            d = zstd.ZstdDecompressor()
                            return d.decompress(compressed_data, max_output_size=self.block_size)
                        except Exception:
                            return compressed_data
                return compressed_data
            except Exception:
                self.f.seek(idx * self.block_size)
                return self.f.read(self.block_size)

    @staticmethod
    def get_game_metadata(filepath):
        """Extension-aware metadata scanner that parses internal PARAM.SFO from ISO, CSO, or ZSO files."""
        try:
            reader = PSPImageReader(filepath)
            full_data = bytearray()
            scan_limit = min(300, reader.num_blocks)
            for i in range(scan_limit):
                full_data.extend(reader.read_block(i))
            reader.close()

            sfo_idx = full_data.find(b'\x00PSF')
            if sfo_idx != -1:
                sfo_data = full_data[sfo_idx:]
                if len(sfo_data) > 20:
                    key_table_off = struct.unpack('<I', sfo_data[8:12])[0]
                    val_table_off = struct.unpack('<I', sfo_data[12:16])[0]
                    entries_count = struct.unpack('<I', sfo_data[16:20])[0]
                    
                    title = ""
                    game_id = ""
                    
                    for i in range(entries_count):
                        entry_offset = 20 + (i * 16)
                        if entry_offset + 16 > len(sfo_data): break
                        key_offset = struct.unpack('<H', sfo_data[entry_offset:entry_offset+2])[0]
                        val_len = struct.unpack('<I', sfo_data[entry_offset+4:entry_offset+8])[0]
                        val_offset = struct.unpack('<I', sfo_data[entry_offset+12:entry_offset+16])[0]
                        
                        key_start = key_table_off + key_offset
                        key_end = sfo_data.find(b'\x00', key_start)
                        key_name = sfo_data[key_start:key_end].decode('utf-8', errors='ignore')
                        
                        val_start = val_table_off + val_offset
                        val_data = sfo_data[val_start:val_start+val_len]
                        
                        if key_name == 'TITLE':
                            title = val_data.decode('utf-8', errors='ignore').rstrip('\x00')
                        elif key_name == 'DISC_ID':
                            game_id = val_data.decode('utf-8', errors='ignore').rstrip('\x00')
                            
                    if title:
                        return title, game_id
        except Exception:
            pass
        return "", ""

    def close(self):
        if self.f:
            self.f.close()

if __name__ == "__main__":
    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        
    app = ISOCompressorApp(root)
    root.mainloop()
