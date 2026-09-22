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
import datetime
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
HISTORY_FILE = "ducky_history.json"
META_CACHE_FILE = "ducky_meta_cache.json"
UNDO_LOG_FILE = "ducky_undo_log.json"
LOG_DIR = "logs"

class ISOCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DuckyISO // PSP Batch Compressor v8.8")
        self.root.geometry("660x1020")
        
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Robust Window / Taskbar Icon Loader
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

        # Comprehensive Theme Palettes (Teal Default & OS Classics)
        self.themes = {
            "Teal & Cyberpunk": {
                "bg": "#0B2525", "panel": "#113A3A", "cyan": "#00FFFF", 
                "pink": "#FF007F", "yellow": "#FFFF00", "text": "#E0F0F0"
            },
            "Windows 98 Classic": {
                "bg": "#008080", "panel": "#C0C0C0", "cyan": "#000080", 
                "pink": "#800080", "yellow": "#000080", "text": "#000000"
            },
            "Windows XP Luna": {
                "bg": "#245EDC", "panel": "#ECE9D8", "cyan": "#0055EA", 
                "pink": "#FF6600", "yellow": "#3C3C3C", "text": "#000000"
            },
            "Windows 7 Aero": {
                "bg": "#1C355E", "panel": "#D4D4D4", "cyan": "#0078D7", 
                "pink": "#B43939", "yellow": "#222222", "text": "#111111"
            },
            "GNOME Adwaita": {
                "bg": "#242424", "panel": "#303030", "cyan": "#3584E4", 
                "pink": "#FF7800", "yellow": "#F6D32D", "text": "#EEEEEE"
            },
            "KDE Breeze Dark": {
                "bg": "#1E1E1E", "panel": "#2A2E32", "cyan": "#3DAEE9", 
                "pink": "#E84F4F", "yellow": "#F67400", "text": "#FCFCFC"
            }
        }
        self.current_theme_name = "Teal & Cyberpunk"
        self.apply_theme_colors()
        
        self.file_paths = []
        self.custom_output_dir = ""
        self.last_dir = os.path.expanduser("~")
        self.is_converting = False
        self.cancel_flag = False
        
        self.load_config()
        self.load_history()
        self.load_meta_cache()
        self.load_undo_log()
        
        self.sound_file = "quack.ogg"
        self._ensure_quack_downloaded()
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.update_ttk_styles()
        
        # Header Frame
        header_frame = tk.Frame(root, bg=self.bg_color)
        header_frame.pack(pady=(8, 2), fill="x", padx=20)
        
        self.lbl_title = tk.Label(header_frame, text="DUCKY_ISO [v8.8]", font=("Monospace", 15, "bold"), bg=self.bg_color, fg=self.cyan)
        self.lbl_title.pack(side=tk.LEFT)
        
        # Theme Switcher Button
        self.btn_theme = tk.Button(header_frame, text="THEME: TEAL", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow,
                                   activebackground=self.yellow, activeforeground="black", command=self.cycle_theme, relief=tk.SOLID, bd=1, padx=6, pady=2)
        self.btn_theme.pack(side=tk.RIGHT)
        
        self.lbl_drop_hint = tk.Label(root, text=">> DRAG & DROP FILES/FOLDERS OR USE SELECTORS", font=("Monospace", 8), bg=self.bg_color, fg=self.yellow)
        self.lbl_drop_hint.pack(pady=(0, 4))
        
        # File/Folder Selection & Utility Buttons
        self.frame_browse = tk.Frame(root, bg=self.bg_color)
        self.frame_browse.pack(pady=3)
        
        self.btn_browse_file = tk.Button(self.frame_browse, text="[ SELECT FILE(S) ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                    activebackground=self.cyan, activeforeground="black", command=self.browse_files, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_browse_file.pack(side=tk.LEFT, padx=2)

        self.btn_browse_folder = tk.Button(self.frame_browse, text="[ FOLDER ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.pink, 
                                    activebackground=self.pink, activeforeground="black", command=self.browse_folder, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_browse_folder.pack(side=tk.LEFT, padx=2)

        self.btn_refresh = tk.Button(self.frame_browse, text="[ REFRESH ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow, 
                                     activebackground=self.yellow, activeforeground="black", command=self.refresh_folder, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_refresh.pack(side=tk.LEFT, padx=2)

        self.btn_test_meta = tk.Button(self.frame_browse, text="[ TEST META ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow, 
                                       activebackground=self.yellow, activeforeground="black", command=self.test_metadata, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_test_meta.pack(side=tk.LEFT, padx=2)

        self.btn_undo = tk.Button(self.frame_browse, text="[ UNDO ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.pink, 
                                  activebackground=self.pink, activeforeground="black", command=self.undo_rename, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_undo.pack(side=tk.LEFT, padx=2)

        self.btn_open_logs = tk.Button(self.frame_browse, text="[ LOGS ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                       activebackground=self.cyan, activeforeground="black", command=self.open_logs_folder, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_open_logs.pack(side=tk.LEFT, padx=2)
        
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

        # Smart Renaming Frame (With Force Rename Checkbox)
        self.frame_rename = tk.Frame(root, bg=self.panel_bg, highlightbackground=self.yellow, highlightthickness=1, padx=8, pady=4)
        self.frame_rename.pack(pady=3, fill="x", padx=30)
        
        self.lbl_rename_title = tk.Label(self.frame_rename, text="RENAME CONFIGURATION (LOCAL PARAM.SFO):", bg=self.panel_bg, fg=self.yellow, font=("Monospace", 9, "bold"))
        self.lbl_rename_title.pack(anchor="w", padx=2)
        
        ren_sub_frame = tk.Frame(self.frame_rename, bg=self.panel_bg)
        ren_sub_frame.pack(fill="x", pady=2)
        
        self.lbl_pattern = tk.Label(ren_sub_frame, text="Pattern:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8))
        self.lbl_pattern.pack(side=tk.LEFT, padx=2)
        self.pattern_var = tk.StringVar(value=self.saved_settings.get("pattern", "Title Only"))
        
        pattern_options = [
            "Title Only", 
            "Title [GameID]", 
            "[GameID] Title", 
            "Title - GameID", 
            "[GameID] - Title", 
            "Title (GameID)", 
            "Title_GameID", 
            "GameID - Title"
        ]
        self.pattern_dropdown = ttk.Combobox(ren_sub_frame, textvariable=self.pattern_var, values=pattern_options, state="readonly", width=17)
        self.pattern_dropdown.pack(side=tk.LEFT, padx=3)
        self.pattern_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())
        
        self.lbl_case = tk.Label(ren_sub_frame, text="Case:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8))
        self.lbl_case.pack(side=tk.LEFT, padx=4)
        self.case_var = tk.StringVar(value=self.saved_settings.get("case", "Normal"))
        self.case_dropdown = ttk.Combobox(ren_sub_frame, textvariable=self.case_var, values=["Normal", "ALL CAPS", "all lowercase", "Title Case", "snake_case"], state="readonly", width=12)
        self.case_dropdown.pack(side=tk.LEFT, padx=3)
        self.case_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        chk_sub_frame = tk.Frame(self.frame_rename, bg=self.panel_bg)
        chk_sub_frame.pack(fill="x", pady=2)

        self.skip_formatted_var = tk.BooleanVar(value=True)
        self.chk_skip_formatted = tk.Checkbutton(chk_sub_frame, text="Skip files with [brackets]", variable=self.skip_formatted_var, bg=self.panel_bg, fg=self.yellow, selectcolor=self.bg_color, font=("Monospace", 8))
        self.chk_skip_formatted.pack(side=tk.LEFT, padx=2)

        self.force_rename_var = tk.BooleanVar(value=False)
        self.chk_force_rename = tk.Checkbutton(chk_sub_frame, text="Force Rename / Ignore History", variable=self.force_rename_var, bg=self.panel_bg, fg=self.pink, selectcolor=self.bg_color, font=("Monospace", 8, "bold"))
        self.chk_force_rename.pack(side=tk.LEFT, padx=10)

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
        self.frame_slider = tk.Frame(root, bg=self.bg_color)
        self.frame_slider.pack(pady=3, fill="x", padx=30)
        
        slider_lvl = self.saved_settings.get("compression_level", 5)
        self.lbl_slider = tk.Label(self.frame_slider, text=f"COMPRESSION_OVERRIDE: [ {slider_lvl} ]", bg=self.bg_color, fg=self.text_color, font=("Monospace", 9, "bold"))
        self.lbl_slider.pack()
        
        self.level_var = tk.IntVar(value=slider_lvl)
        self.slider = tk.Scale(self.frame_slider, from_=1, to=10, orient=tk.HORIZONTAL, variable=self.level_var, 
                               bg=self.bg_color, fg=self.cyan, troughcolor=self.panel_bg, 
                               activebackground=self.pink, highlightthickness=0, command=self.on_slider_change)
        self.slider.pack(fill="x")
        
        # Size Estimate Display
        self.lbl_estimate = tk.Label(root, text="ESTIMATED YIELD: -- MB ?", font=("Monospace", 10, "bold"), bg=self.bg_color, fg=self.yellow)
        self.lbl_estimate.pack(pady=3)
        
        # Action Buttons
        self.frame_actions = tk.Frame(root, bg=self.bg_color)
        self.frame_actions.pack(pady=4)
        
        self.btn_compress = tk.Button(self.frame_actions, text="[ START COMPRESSION ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                     activebackground=self.cyan, activeforeground="black", command=self.start_compression, relief=tk.SOLID, bd=1, padx=8, pady=5)
        self.btn_compress.pack(side=tk.LEFT, padx=4)

        self.btn_rename = tk.Button(self.frame_actions, text="[ START RENAME ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.yellow, 
                                    activebackground=self.yellow, activeforeground="black", command=self.start_rename, relief=tk.SOLID, bd=1, padx=8, pady=5)
        self.btn_rename.pack(side=tk.LEFT, padx=4)

        self.btn_cancel = tk.Button(self.frame_actions, text="[ ABORT ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.pink, 
                                    activebackground=self.pink, activeforeground="black", command=self.cancel_action, relief=tk.SOLID, bd=1, padx=8, pady=5, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=4)
        
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
        self.term_frame = tk.Frame(root, bg="#000000", highlightbackground=self.cyan, highlightthickness=1)
        self.term_frame.pack(pady=8, fill="both", expand=True, padx=25)
        
        self.lbl_term_title = tk.Label(self.term_frame, text="[ TERMINAL OUTPUT LOG ]", bg="#000000", fg=self.cyan, font=("Monospace", 8, "bold"))
        self.lbl_term_title.pack(anchor="w", padx=5)
        
        self.term_box = tk.Text(self.term_frame, bg="#000000", fg="#00FF66", font=("Monospace", 8), height=6, bd=0, highlightthickness=0)
        self.term_box.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=2)
        self.term_box.config(state=tk.DISABLED)
        
        term_scroll = tk.Scrollbar(self.term_frame, command=self.term_box.yview, bg="#000000")
        term_scroll.pack(side=tk.RIGHT, fill="y")
        self.term_box.config(yscrollcommand=term_scroll.set)

        if TkinterDnD:
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self.handle_drop)
            except Exception:
                pass

        self.log_term("DuckyISO v8.8 Initialized with Force Rename & Pattern Override.")

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

    def load_history(self):
        self.completed_history = set()
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.completed_history = set(data.get("completed_files", []))
            except Exception:
                pass

    def save_history(self):
        try:
            data = {"completed_files": list(self.completed_history)}
            with open(HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def load_meta_cache(self):
        self.meta_cache = {}
        if os.path.exists(META_CACHE_FILE):
            try:
                with open(META_CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.meta_cache = json.load(f)
            except Exception:
                pass

    def save_meta_cache(self):
        try:
            with open(META_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.meta_cache, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def load_undo_log(self):
        self.undo_records = []
        if os.path.exists(UNDO_LOG_FILE):
            try:
                with open(UNDO_LOG_FILE, 'r', encoding='utf-8') as f:
                    self.undo_records = json.load(f)
            except Exception:
                pass

    def save_undo_log(self):
        try:
            with open(UNDO_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.undo_records, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def log_to_file(self, log_type, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        filename = "errors.log" if log_type == "ERROR" else "activity.log"
        filepath = os.path.join(LOG_DIR, filename)
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} [{log_type}] {message}\n")
        except Exception:
            pass

    def open_logs_folder(self):
        try:
            abs_path = os.path.abspath(LOG_DIR)
            subprocess.Popen(["xdg-open", abs_path])
            self.log_term(f"Opened logs directory: {abs_path}")
        except Exception as e:
            messagebox.showerror("SYS_ERROR", f"Could not open logs folder:\n{str(e)}")

    def log_term(self, text, is_error=False):
        self.term_box.config(state=tk.NORMAL)
        self.term_box.insert(tk.END, f"> {text}\n")
        self.term_box.see(tk.END)
        self.term_box.config(state=tk.DISABLED)
        if is_error:
            self.log_to_file("ERROR", text)
        else:
            self.log_to_file("INFO", text)

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
        
        short_theme_label = self.current_theme_name.split()[0].upper()
        self.btn_theme.config(text=f"THEME: {short_theme_label}")
        self.root.configure(bg=self.bg_color)
        
        for widget in self.root.winfo_children():
            try:
                widget.configure(bg=self.bg_color)
            except Exception:
                pass
                
        self.lbl_title.configure(bg=self.bg_color, fg=self.cyan)
        self.btn_theme.configure(bg=self.panel_bg, fg=self.yellow, activebackground=self.yellow)
        self.lbl_drop_hint.configure(bg=self.bg_color, fg=self.yellow)
        self.frame_browse.configure(bg=self.bg_color)
        self.btn_browse_file.configure(bg=self.panel_bg, fg=self.cyan, activebackground=self.cyan)
        self.btn_browse_folder.configure(bg=self.panel_bg, fg=self.pink, activebackground=self.pink)
        self.btn_refresh.configure(bg=self.panel_bg, fg=self.yellow, activebackground=self.yellow)
        self.btn_test_meta.configure(bg=self.panel_bg, fg=self.yellow, activebackground=self.yellow)
        self.btn_undo.configure(bg=self.panel_bg, fg=self.pink, activebackground=self.pink)
        self.btn_open_logs.configure(bg=self.panel_bg, fg=self.cyan, activebackground=self.cyan)
        
        self.frame_output.configure(bg=self.panel_bg, highlightbackground=self.pink)
        self.lbl_out_title.configure(bg=self.panel_bg, fg=self.text_color)
        self.btn_change_out.configure(bg=self.bg_color, fg=self.pink, activebackground=self.pink)
        
        self.frame_rename.configure(bg=self.panel_bg, highlightbackground=self.yellow)
        self.lbl_rename_title.configure(bg=self.panel_bg, fg=self.yellow)
        self.lbl_pattern.configure(bg=self.panel_bg, fg=self.text_color)
        self.lbl_case.configure(bg=self.panel_bg, fg=self.text_color)
        self.chk_skip_formatted.configure(bg=self.panel_bg, fg=self.yellow, selectcolor=self.bg_color)
        self.chk_force_rename.configure(bg=self.panel_bg, fg=self.pink, selectcolor=self.bg_color)

        self.frame_format.configure(bg=self.panel_bg, highlightbackground=self.cyan)
        self.lbl_fmt_title.configure(bg=self.panel_bg, fg=self.yellow)
        self.rb_zso.configure(bg=self.panel_bg, fg=self.text_color, activebackground=self.panel_bg, activeforeground=self.cyan)
        self.rb_cso.configure(bg=self.panel_bg, fg=self.text_color, activebackground=self.panel_bg, activeforeground=self.cyan)
        
        self.frame_slider.configure(bg=self.bg_color)
        self.lbl_slider.configure(bg=self.bg_color, fg=self.text_color)
        self.slider.configure(bg=self.bg_color, fg=self.cyan, troughcolor=self.panel_bg)
        
        self.frame_actions.configure(bg=self.bg_color)
        self.btn_compress.configure(bg=self.panel_bg, fg=self.cyan, activebackground=self.cyan)
        self.btn_rename.configure(bg=self.panel_bg, fg=self.yellow, activebackground=self.yellow)
        self.btn_cancel.configure(bg=self.panel_bg, fg=self.pink, activebackground=self.pink)
        
        self.lbl_status.configure(bg=self.bg_color, fg=self.text_color)
        self.lbl_pbar1.configure(bg=self.bg_color, fg=self.cyan)
        self.lbl_pbar2.configure(bg=self.bg_color, fg=self.pink)
        self.term_frame.configure(bg="#000000", highlightbackground=self.cyan)
        self.lbl_term_title.configure(bg="#000000", fg=self.cyan)
        self.term_box.configure(bg="#000000", fg="#00FF66")
        
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

    def refresh_folder(self):
        if not self.last_dir or not os.path.exists(self.last_dir):
            messagebox.showwarning("NOTICE", "No active directory to refresh.")
            return
        
        self.log_term(f"Refreshing active directory: {self.last_dir}")
        found_files = []
        valid_exts = ('.iso', '.cso', '.zso', '.dax')
        for root_dir, _, files in os.walk(self.last_dir):
            for file in files:
                if file.lower().endswith(valid_exts):
                    found_files.append(os.path.join(root_dir, file))
                    
        if found_files:
            self.process_loaded_files(found_files)
            messagebox.showinfo("Refresh Complete", f"Refreshed folder. Found {len(found_files)} valid file(s).")
        else:
            messagebox.showinfo("Refresh Complete", "Refreshed folder. No game files found.")

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
            self.process_loaded_files(found_files)
            self.save_config()
        else:
            messagebox.showwarning("INVALID DROP", "No valid PSP game images found in drop target.")
            self.log_term("Warning: Drop target contained no valid PSP game images.", is_error=True)

    def browse_files(self):
        paths = filedialog.askopenfilenames(initialdir=self.last_dir, filetypes=[("PSP Game Images", "*.iso *.cso *.zso *.dax"), ("All Files", "*.*")])
        if paths:
            self.last_dir = os.path.dirname(paths[0])
            self.process_loaded_files(list(paths))
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
                self.process_loaded_files(found_files)
                self.save_config()
            else:
                messagebox.showinfo("NO DATA FOUND", "No valid PSP game images located in target directory.")
                self.log_term("Scan complete: No game files found.", is_error=True)

    def process_loaded_files(self, file_list):
        self.file_paths = file_list
        self.btn_compress.config(state=tk.DISABLED)
        self.btn_rename.config(state=tk.DISABLED)
        self.btn_browse_file.config(state=tk.DISABLED)
        self.btn_browse_folder.config(state=tk.DISABLED)
        
        threading.Thread(target=self._run_file_scan_feedback, args=(file_list,), daemon=True).start()

    def _run_file_scan_feedback(self, file_list):
        total = len(file_list)
        total_size_bytes = 0
        
        for idx, path in enumerate(file_list):
            total_size_bytes += os.path.getsize(path)
            filename = os.path.basename(path)
            status_text = f"[SCANNING METADATA: {idx + 1}/{total}] {filename}"
            self.root.after(0, lambda txt=status_text: self.lbl_status.config(text=txt, fg=self.yellow))
            
            if path in self.meta_cache:
                title, game_id = self.meta_cache[path]["title"], self.meta_cache[path]["game_id"]
                self.root.after(0, lambda t=title, g=game_id, f=filename: self.log_term(f"Cached: '{f}' -> '{t}' [{g}]"))
            else:
                try:
                    title, game_id = PSPImageReader.get_game_metadata(path)
                    if title:
                        self.meta_cache[path] = {"title": title, "game_id": game_id}
                        self.save_meta_cache()
                        self.root.after(0, lambda t=title, g=game_id, f=filename: self.log_term(f"Loaded: '{f}' -> '{t}' [{g}]"))
                    else:
                        self.root.after(0, lambda f=filename: self.log_term(f"Warning: No PARAM.SFO found for '{f}'", is_error=True))
                except Exception as e:
                    self.root.after(0, lambda f=filename, err=str(e): self.log_term(f"Metadata read error on '{f}': {err}", is_error=True))

        total_size_mb = total_size_bytes / (1024 * 1024)
        self.root.after(0, lambda: self._finalize_file_loading(total, total_size_mb))

    def _finalize_file_loading(self, count, total_size_mb):
        self.lbl_file.config(text=f"LOADED: {count} NODE(S) | {total_size_mb:.2f} MB", fg=self.cyan)
        if not self.custom_output_dir and self.file_paths:
            self.lbl_out_title.config(text=f"OUTPUT: .../compressed (Auto)")
        self.lbl_status.config(text=f"STATUS: READY ({count} GAMES LOADED)", fg=self.cyan)
        self.btn_compress.config(state=tk.NORMAL)
        self.btn_rename.config(state=tk.NORMAL)
        self.btn_browse_file.config(state=tk.NORMAL)
        self.btn_browse_folder.config(state=tk.NORMAL)
        self.log_term(f"Successfully processed and verified {count} game file(s).")
        self.update_estimate()

    def test_metadata(self):
        if not self.file_paths:
            messagebox.showwarning("NOTICE", "Please select at least one file first to test metadata.")
            return
        
        test_file = self.file_paths[0]
        self.log_term(f"Testing local metadata for: {os.path.basename(test_file)}")
        title, game_id = PSPImageReader.get_game_metadata(test_file)
        
        msg = f"File: {os.path.basename(test_file)}\n\n"
        if title:
            msg += f"Detected Title: {title}\n"
            msg += f"Detected Game ID: {game_id}"
            self.log_term(f"Metadata OK -> Title: '{title}' [{game_id}]")
        else:
            msg += "RESULT: Could not locate PARAM.SFO header."
            self.log_term(f"Metadata FAILED for {os.path.basename(test_file)}", is_error=True)
            
        messagebox.showinfo("Metadata Diagnostic", msg)

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
        except Exception as e:
            self.log_to_file("ERROR", f"Estimate calculation failed: {str(e)}")
            self.root.after(0, lambda: self.lbl_estimate.config(text="ESTIMATE_FAIL ?", fg=self.pink))

    def format_filename(self, title, game_id, ext):
        clean_title = re.sub(r'[®™©℠ℳ]', '', title)
        clean_title = re.sub(r'[<>:"/\\|?*]', '', clean_title).strip()
        
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
        elif pattern == "[GameID] - Title" and game_id:
            base = f"[{game_id}] - {clean_title}"
        elif pattern == "Title (GameID)" and game_id:
            base = f"{clean_title} ({game_id})"
        elif pattern == "Title_GameID" and game_id:
            base = f"{clean_title}_{game_id}"
        elif pattern == "GameID - Title" and game_id:
            base = f"{game_id} - {clean_title}"
        else:
            base = clean_title

        return f"{base}{ext}"

    def start_rename(self):
        if not self.file_paths:
            messagebox.showerror("SYS_ERROR", "NO FILES SELECTED FOR RENAME.")
            return
        
        self.log_term("Starting local batch rename protocol...")
        self.is_converting = True
        self.cancel_flag = False
        self.btn_compress.config(state=tk.DISABLED)
        self.btn_rename.config(state=tk.DISABLED)
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
        skip_formatted = self.skip_formatted_var.get()
        force_rename = self.force_rename_var.get()
        preview_mappings = []

        updated_paths = []
        for idx, path in enumerate(self.file_paths):
            if self.cancel_flag: break
            
            filename = os.path.basename(path)
            
            # Skip check only if force rename is NOT checked
            if not force_rename:
                if skip_formatted and ('[' in filename or ']' in filename):
                    self.log_term(f"SKIP (Already Formatted): '{filename}'")
                    skipped_count += 1
                    self.progress_batch["value"] = idx + 1
                    updated_paths.append(path)
                    continue

                if path in self.completed_history and os.path.exists(path):
                    self.log_term(f"SKIP (History): '{filename}' already processed.")
                    skipped_count += 1
                    self.progress_batch["value"] = idx + 1
                    updated_paths.append(path)
                    continue

            try:
                dirname, filename = os.path.split(path)
                ext = os.path.splitext(filename)[1]
                
                game_title = ""
                game_id = ""

                if path in self.meta_cache:
                    game_title = self.meta_cache[path]["title"]
                    game_id = self.meta_cache[path]["game_id"]
                else:
                    game_title, game_id = PSPImageReader.get_game_metadata(path)
                    if game_title:
                        self.meta_cache[path] = {"title": game_title, "game_id": game_id}
                        self.save_meta_cache()

                if not game_title:
                    self.log_term(f"SKIP: Could not read local metadata for {filename}", is_error=True)
                    skipped_count += 1
                    updated_paths.append(path)
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
                    self.completed_history.add(new_path)
                    self.save_history()
                    
                    self.undo_records.append({"old_path": new_path, "original_path": path})
                    self.save_undo_log()
                    
                    updated_paths.append(new_path)
                    preview_mappings.append((filename, new_name))
                    self.log_term(f"RENAMED: '{filename}' -> '{new_name}'")
                    self.log_to_file("RENAME", f"'{filename}' -> '{new_name}'")
                else:
                    self.completed_history.add(path)
                    self.save_history()
                    updated_paths.append(path)
                
                self.progress_batch["value"] = idx + 1
            except Exception as e:
                err_str = str(e)
                self.log_term(f"ERROR renaming {filename}: {err_str}", is_error=True)
                skipped_count += 1
                updated_paths.append(path)

        self.file_paths = updated_paths
        self.root.after(0, lambda: self._finalize_rename_ui(renamed_count, skipped_count, preview_mappings))

    def _finalize_rename_ui(self, count, skipped, preview_mappings):
        self.is_converting = False
        self.btn_compress.config(state=tk.NORMAL)
        self.btn_rename.config(state=tk.NORMAL)
        self.slider.config(state=tk.NORMAL)
        self.btn_browse_file.config(state=tk.NORMAL)
        self.btn_browse_folder.config(state=tk.NORMAL)
        self.btn_change_out.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.lbl_status.config(text=f"RENAME COMPLETE: {count} UPDATED, {skipped} SKIPPED", fg=self.cyan)
        self._play_quack()
        
        preview_text = f"Batch Rename Finished!\nSuccessfully Renamed: {count} // Skipped: {skipped}\n\n[BEFORE & AFTER PREVIEW]:\n"
        for before, after in preview_mappings[:12]:
            preview_text += f"• {before}\n  ➔ {after}\n"
        if len(preview_mappings) > 12:
            preview_text += f"\n...and {len(preview_mappings) - 12} more files."
            
        self.log_term(f"Rename Operation Finished! Renamed: {count}, Skipped: {skipped}")
        messagebox.showinfo("Rename Complete & Preview", preview_text)

    def undo_rename(self):
        if not self.undo_records:
            messagebox.showinfo("UNDO RENAME", "No recent rename history found to revert.")
            return
        
        reverted_count = 0
        failed_count = 0
        
        for record in reversed(self.undo_records):
            current_p = record["old_path"]
            original_p = record["original_path"]
            
            if os.path.exists(current_p):
                try:
                    dirname = os.path.dirname(current_p)
                    orig_filename = os.path.basename(original_p)
                    target_p = os.path.join(dirname, orig_filename)
                    
                    os.rename(current_p, target_p)
                    reverted_count += 1
                    self.log_term(f"REVERTED: '{os.path.basename(current_p)}' -> '{orig_filename}'")
                except Exception as e:
                    failed_count += 1
                    self.log_term(f"Failed to revert {os.path.basename(current_p)}: {str(e)}", is_error=True)
                    
        self.undo_records = []
        self.save_undo_log()
        messagebox.showinfo("Undo Complete", f"Successfully reverted {reverted_count} file(s).")
        self.log_term(f"Undo operation complete. Reverted: {reverted_count}, Failed: {failed_count}")

    def start_compression(self):
        if not self.file_paths:
            messagebox.showerror("SYS_ERROR", "NO FILES SELECTED FOR COMPRESSION.")
            return

        fmt = self.format_var.get()
        if fmt == "ZSO" and zstd is None:
            messagebox.showerror("DEPENDENCY_MISSING", "REQUIRES: apt install python3-zstandard")
            return
            
        target_data = []
        for path in self.file_paths:
            base_ext = os.path.splitext(path)[1].lower()
            out_ext = f".{fmt.lower()}"
            base_name = os.path.basename(path).replace(base_ext, out_ext)
            
            if self.custom_output_dir:
                out_dir = self.custom_output_dir
            else:
                out_dir = os.path.join(os.path.dirname(path), "compressed")
                
            os.makedirs(out_dir, exist_ok=True)
            target_data.append((path, os.path.join(out_dir, base_name)))
            
        self.is_converting = True
        self.cancel_flag = False
        
        self.btn_compress.config(state=tk.DISABLED)
        self.btn_rename.config(state=tk.DISABLED)
        self.slider.config(state=tk.DISABLED)
        self.btn_browse_file.config(state=tk.DISABLED)
        self.btn_browse_folder.config(state=tk.DISABLED)
        self.btn_change_out.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        
        self.progress_batch["maximum"] = len(target_data)
        self.progress_batch["value"] = 0
        
        threading.Thread(target=self._run_batch_compression, args=(target_data, fmt, self.level_var.get()), daemon=True).start()

    def cancel_action(self):
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

    def _run_batch_compression(self, target_data, fmt, level):
        total_files = len(target_data)
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for file_idx, (in_path, out_path) in enumerate(target_data):
            if self.cancel_flag: break
                
            filename = os.path.basename(in_path)
            out_filename = os.path.basename(out_path)
            
            if out_path in self.completed_history or (os.path.exists(out_path) and os.path.getsize(out_path) > 1024):
                self.log_term(f"RESUME: Skipping '{out_filename}' (already fully compressed).")
                skip_count += 1
                self.completed_history.add(out_path)
                self.save_history()
                self.root.after(0, self.update_ui_progress, file_idx, total_files, 100, 100, filename, "SKIPPED")
                continue

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
                self.completed_history.add(out_path)
                self.save_history()
                self.log_term(f"Completed successfully: {filename}")
                self.log_to_file("COMPRESS", f"Successfully compressed '{filename}' to '{out_filename}'")
                self.root.after(0, self.update_ui_progress, file_idx, total_files, num_blocks, num_blocks, filename, "DONE")
                
            except Exception as e:
                fail_count += 1
                err_msg = str(e)
                self.log_term(f"ERROR on {filename}: {err_msg}", is_error=True)
                if os.path.exists(out_path):
                    os.remove(out_path)
                    
            if self.cancel_flag and os.path.exists(out_path):
                os.remove(out_path)
                
        self.root.after(0, lambda: self._finalize_compression_ui(success_count, skip_count, fail_count))
            
    def _finalize_compression_ui(self, success_count=0, skip_count=0, fail_count=0):
        if self.cancel_flag:
            self.lbl_status.config(text="PROCESS ABORTED.", fg=self.pink)
            self.log_term("Batch process was aborted by user.")
        else:
            self.lbl_status.config(text="> ALL PROCESSES COMPLETE <", fg=self.cyan)
            self.progress_batch["value"] = self.progress_batch["maximum"]
            self._play_quack()
            
            summary_msg = f"Batch Compression Finished!\n\nSuccessful: {success_count}\nSkipped: {skip_count}\nFailed: {fail_count}"
            self.log_term(summary_msg.replace('\n', ' // '))
            messagebox.showinfo("Operation Complete", summary_msg)
            
        self.is_converting = False
        self.btn_compress.config(state=tk.NORMAL)
        self.btn_rename.config(state=tk.NORMAL)
        self.slider.config(state=tk.NORMAL)
        self.btn_browse_file.config(state=tk.NORMAL)
        self.btn_browse_folder.config(state=tk.NORMAL)
        self.btn_change_out.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.update_estimate()


class PSPImageReader:
    """Robust parser that correctly decodes raw ISOs and compressed CSO/ZSO images to find PARAM.SFO."""
    def __init__(self, filepath):
        self.filepath = filepath
        self.f = open(filepath, 'rb')
        self.f.seek(0, os.SEEK_END)
        self.file_size = self.f.tell()
        self.f.seek(0)
        
        magic = self.f.read(4)
        if magic in (b'CISO', b'ZISO'):
            self.is_compressed = True
            header_size = struct.unpack('<I', self.f.read(4))[0]
            self.total_size = struct.unpack('<Q', self.f.read(8))[0]
            self.block_size = struct.unpack('<I', self.f.read(4))[0]
            self.ver = struct.unpack('B', self.f.read(1))[0]
            self.align = struct.unpack('B', self.f.read(1))[0]
            self.f.read(2)
            
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
                start_pos = (entry & 0x7FFFFFFF) << self.align
                end_pos = (next_entry & 0x7FFFFFFF) << self.align
                
                if start_pos == end_pos or start_pos >= self.file_size:
                    return b'\x00' * self.block_size
                
                self.f.seek(start_pos)
                compressed_data = self.f.read(end_pos - start_pos)
                if is_raw or start_pos == end_pos or not compressed_data:
                    return compressed_data
                
                self.f.seek(0)
                fmt_magic = self.f.read(4)
                
                if fmt_magic == b'CISO':
                    try:
                        return zlib.decompress(compressed_data, wbits=-15)
                    except Exception:
                        return compressed_data
                elif fmt_magic == b'ZISO':
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
        """Exhaustively scans the entire file blocks to locate and parse the true game PARAM.SFO."""
        try:
            reader = PSPImageReader(filepath)
            full_data = bytearray()
            for i in range(reader.num_blocks):
                full_data.extend(reader.read_block(i))
            reader.close()

            pos = 0
            while True:
                sfo_idx = full_data.find(b'\x00PSF', pos)
                if sfo_idx == -1:
                    break
                
                sfo_data = full_data[sfo_idx:]
                pos = sfo_idx + 4
                
                if len(sfo_data) > 20:
                    try:
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
                        
                        if title and "Update" not in title and "MSTKUPDATE" not in game_id:
                            return title, game_id
                    except Exception:
                        continue
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
