import os
import json
import zlib
import random
import struct
import time
import re
import shutil
import threading
import subprocess
import urllib.request
import urllib.parse
import datetime
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

try:
    import zstandard as zstd
except ImportError:
    zstd = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "duckshrink_config.json")
HISTORY_FILE = os.path.join(APP_DIR, "duckshrink_history.json")
META_CACHE_FILE = os.path.join(APP_DIR, "duckshrink_meta_cache.json")
UNDO_LOG_FILE = os.path.join(APP_DIR, "duckshrink_undo_log.json")
LOG_DIR = os.path.join(APP_DIR, "logs")

class DuckShrinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DuckShrink_PSP // Batch Compressor & PS1 Eboot v10.12")
        self.root.geometry("660x1380")
        
        os.makedirs(LOG_DIR, exist_ok=True)
        
        try:
            for icon_name in ("icon.png", "icon.ico"):
                icon_path = os.path.join(APP_DIR, icon_name)
                if not os.path.exists(icon_path):
                    icon_path = os.path.join("/opt/duckshrink", icon_name)
                if os.path.exists(icon_path):
                    try:
                        img = tk.PhotoImage(file=icon_path)
                        self.root.iconphoto(True, img)
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        self.themes = {
            "Teal & Cyberpunk": {
                "bg": "#0B2525", "panel": "#113A3A", "cyan": "#00FFFF", 
                "pink": "#FF007F", "yellow": "#FFFF00", "text": "#E0F0F0"
            },
            "Linux Mint 22.3": {
                "bg": "#2A323D", "panel": "#37414B", "cyan": "#87CD28", 
                "pink": "#5C6A79", "yellow": "#F39C12", "text": "#FFFFFF"
            },
            "Ubuntu Yaru": {
                "bg": "#2C001E", "panel": "#3C002B", "cyan": "#E95420", 
                "pink": "#F47721", "yellow": "#AEA79F", "text": "#FFFFFF"
            },
            "Windows 98 Classic": {
                "bg": "#008080", "panel": "#C0C0C0", "cyan": "#000080", 
                "pink": "#800080", "yellow": "#000080", "text": "#000000"
            },
            "Windows XP Luna": {
                "bg": "#245EDC", "panel": "#ECE9D8", "cyan": "#0055EA", 
                "pink": "#FF6600", "yellow": "#3C3C3C", "text": "#000000"
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
        self.app_mode = "PSP" 
        self.apply_theme_colors()
        
        self.file_paths = []
        self.ps1_discs = []
        
        self.ps1_icon0 = ""
        self.ps1_pic0 = ""
        self.ps1_pic1 = ""
        
        self.custom_output_dir = ""
        self.last_dir = os.path.expanduser("~")
        self.is_converting = False
        self.cancel_flag = False
        
        self.load_config()
        self.load_history()
        self.load_meta_cache()
        self.load_undo_log()
        
        self.sound_file = os.path.join(APP_DIR, "quack.ogg")
        self._ensure_quack_downloaded()
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.update_ttk_styles()
        
        # Header Frame
        header_frame = tk.Frame(root, bg=self.bg_color)
        header_frame.pack(pady=(8, 2), fill="x", padx=20)
        
        self.lbl_title = tk.Label(header_frame, text="DUCKSHRINK_PSP [v10.12]", font=("Monospace", 15, "bold"), bg=self.bg_color, fg=self.cyan)
        self.lbl_title.pack(side=tk.LEFT)
        
        header_right_frame = tk.Frame(header_frame, bg=self.bg_color)
        header_right_frame.pack(side=tk.RIGHT)

        self.btn_mode_switch = tk.Button(header_right_frame, text="[ MODE: PSP ➔ PS1 ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow,
                                         activebackground=self.yellow, activeforeground="black", command=self.toggle_app_mode, relief=tk.SOLID, bd=1, padx=6, pady=2)
        self.btn_mode_switch.pack(side=tk.LEFT, padx=4)

        self.btn_donate = tk.Button(header_right_frame, text="[ 💛 DONATE ]", font=("Monospace", 8, "bold"), bg="#FFD700", fg="black",
                                    activebackground="#FFF066", activeforeground="black", command=self.open_donation_link, relief=tk.SOLID, bd=1, padx=6, pady=2)
        self.btn_donate.pack(side=tk.LEFT, padx=4)

        self.btn_theme = tk.Button(header_right_frame, text="[ THEMES ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow,
                                   activebackground=self.yellow, activeforeground="black", command=self.open_theme_selector, relief=tk.SOLID, bd=1, padx=6, pady=2)
        self.btn_theme.pack(side=tk.LEFT, padx=4)
        
        self.lbl_drop_hint = tk.Label(root, text=">> DRAG & DROP GAME FILES OR USE SELECTORS", font=("Monospace", 8), bg=self.bg_color, fg=self.yellow)
        self.lbl_drop_hint.pack(pady=(0, 4))
        
        self.frame_browse = tk.Frame(root, bg=self.bg_color)
        self.frame_browse.pack(pady=3)
        
        self.btn_browse_file = tk.Button(self.frame_browse, text="[ SELECT FILE(S) ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                    activebackground=self.cyan, activeforeground="black", command=self.browse_files, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_browse_file.pack(side=tk.LEFT, padx=2)

        self.btn_browse_folder = tk.Button(self.frame_browse, text="[ FOLDER ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.pink, 
                                    activebackground=self.pink, activeforeground="black", command=self.browse_folder, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_browse_folder.pack(side=tk.LEFT, padx=2)

        self.btn_queue = tk.Button(self.frame_browse, text="[ QUEUE ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow, 
                                   activebackground=self.yellow, activeforeground="black", command=self.open_queue_manager, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_queue.pack(side=tk.LEFT, padx=2)

        self.btn_refresh = tk.Button(self.frame_browse, text="[ REFRESH ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.yellow, 
                                     activebackground=self.yellow, activeforeground="black", command=self.refresh_folder, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_refresh.pack(side=tk.LEFT, padx=2)

        self.btn_undo = tk.Button(self.frame_browse, text="[ UNDO ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.pink, 
                                  activebackground=self.pink, activeforeground="black", command=self.undo_rename, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_undo.pack(side=tk.LEFT, padx=2)

        self.btn_open_logs = tk.Button(self.frame_browse, text="[ LOGS ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.cyan, 
                                       activebackground=self.cyan, activeforeground="black", command=self.open_logs_folder, relief=tk.SOLID, bd=1, padx=3, pady=3)
        self.btn_open_logs.pack(side=tk.LEFT, padx=2)

        self.lbl_file = tk.Label(root, text="STATUS: AWAITING INPUT", bg=self.bg_color, fg="#555555", font=("Monospace", 9, "bold"))
        self.lbl_file.pack(pady=3)
        
        # Output Path Configuration Frame
        self.frame_output = tk.Frame(root, bg=self.panel_bg, highlightbackground=self.pink, highlightthickness=2, padx=8, pady=4)
        self.frame_output.pack(pady=3, fill="x", padx=30)
        
        out_display_text = f"OUTPUT: {self.custom_output_dir[:24]}..." if self.custom_output_dir else "OUTPUT: /.../compressed (Auto)"
        self.lbl_out_title = tk.Label(self.frame_output, text=out_display_text, bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8, "bold"), anchor="w")
        self.lbl_out_title.pack(side=tk.LEFT, fill="x", expand=True)

        self.btn_open_out = tk.Button(self.frame_output, text="[ OUTPUT FOLDER ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.cyan,
                                      activebackground=self.cyan, activeforeground="black", command=self.open_output_dir, relief=tk.SOLID, bd=1, padx=5, pady=2)
        self.btn_open_out.pack(side=tk.RIGHT, padx=2)
        
        self.btn_change_out = tk.Button(self.frame_output, text="[ CHANGE ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.pink,
                                        activebackground=self.pink, activeforeground="black", command=self.change_output_dir, relief=tk.SOLID, bd=1, padx=5, pady=2)
        self.btn_change_out.pack(side=tk.RIGHT, padx=2)

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

        # Dynamic Mode Panels & Container
        self.dynamic_container = tk.Frame(root, bg=self.bg_color)
        self.dynamic_container.pack(fill="x", padx=30, pady=2)

        self.build_psp_mode_panel()
        self.build_ps1_mode_panel()
        self.update_mode_visibility()  
        
        # Format Selection & Multi-Threading Config Frame
        self.frame_format = tk.Frame(root, bg=self.panel_bg, highlightbackground=self.cyan, highlightthickness=2, padx=8, pady=4)
        self.frame_format.pack(pady=4, fill="x", padx=30)
        
        fmt_top_frame = tk.Frame(self.frame_format, bg=self.panel_bg)
        fmt_top_frame.pack(fill="x", pady=2)

        self.lbl_fmt_title = tk.Label(fmt_top_frame, text="⭐ OUTPUT_FORMAT:", bg=self.panel_bg, fg=self.yellow, font=("Monospace", 9, "bold"))
        self.lbl_fmt_title.pack(side=tk.LEFT, padx=6)
        
        self.format_var = tk.StringVar(value=self.saved_settings.get("format", "ZSO"))
        self.rb_zso = tk.Radiobutton(fmt_top_frame, text="ZSO (ZSTD)", variable=self.format_var, value="ZSO", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, activebackground=self.panel_bg, activeforeground=self.cyan, font=("Monospace", 9, "bold"), command=self.on_format_change)
        self.rb_zso.pack(side=tk.LEFT, padx=4)
        self.rb_cso = tk.Radiobutton(fmt_top_frame, text="CSO (ZLIB)", variable=self.format_var, value="CSO", bg=self.panel_bg, fg=self.text_color, selectcolor=self.bg_color, activebackground=self.panel_bg, activeforeground=self.cyan, font=("Monospace", 9, "bold"), command=self.on_format_change)
        self.rb_cso.pack(side=tk.LEFT, padx=4)

        thread_sub_frame = tk.Frame(self.frame_format, bg=self.panel_bg)
        thread_sub_frame.pack(fill="x", pady=4)

        self.lbl_threads = tk.Label(thread_sub_frame, text="Parallel Threads:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8, "bold"))
        self.lbl_threads.pack(side=tk.LEFT, padx=6)

        default_threads = str(min(os.cpu_count() or 4, 8))
        self.threads_var = tk.StringVar(value=self.saved_settings.get("threads", default_threads))
        thread_options = ["1", "2", "4", "6", "8", "12", "16"]
        self.threads_dropdown = ttk.Combobox(thread_sub_frame, textvariable=self.threads_var, values=thread_options, state="readonly", width=5)
        self.threads_dropdown.pack(side=tk.LEFT, padx=4)
        self.threads_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        self.lbl_thread_hint = tk.Label(thread_sub_frame, text="(Compresses multiple games at once)", bg=self.panel_bg, fg="#888888", font=("Monospace", 7))
        self.lbl_thread_hint.pack(side=tk.LEFT, padx=4)
        
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
        
        self.lbl_estimate = tk.Label(root, text="ESTIMATED YIELD: -- ?", font=("Monospace", 10, "bold"), bg=self.bg_color, fg=self.yellow)
        self.lbl_estimate.pack(pady=3)
        
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
        
        self.term_box = tk.Text(self.term_frame, bg="#000000", fg="#00FF66", font=("Monospace", 8), height=5, bd=0, highlightthickness=0)
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

        self.log_term("DuckShrink_PSP v10.12 Initialized successfully.")

    def build_psp_mode_panel(self):
        self.panel_psp = tk.Frame(self.dynamic_container, bg=self.bg_color)
        
        self.frame_rename = tk.Frame(self.panel_psp, bg=self.panel_bg, highlightbackground=self.yellow, highlightthickness=2, padx=8, pady=4)
        self.frame_rename.pack(pady=2, fill="x")
        self.lbl_rename_title = tk.Label(self.frame_rename, text="⭐ LOCAL RENAME CONFIGURATION (PARAM.SFO):", bg=self.panel_bg, fg=self.yellow, font=("Monospace", 9, "bold"))
        self.lbl_rename_title.pack(anchor="w", padx=2)
        
        ren_sub_frame = tk.Frame(self.frame_rename, bg=self.panel_bg)
        ren_sub_frame.pack(fill="x", pady=2)
        self.lbl_pattern = tk.Label(ren_sub_frame, text="Pattern:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8))
        self.lbl_pattern.pack(side=tk.LEFT, padx=2)
        self.pattern_var = tk.StringVar(value=self.saved_settings.get("pattern", "Title Only"))
        pattern_options = ["Title Only", "Title [GameID]", "[GameID] Title", "Title - GameID", "[GameID] - Title", "Title (GameID)", "Title_GameID", "GameID - Title"]
        self.pattern_dropdown = ttk.Combobox(ren_sub_frame, textvariable=self.pattern_var, values=pattern_options, state="readonly", width=14)
        self.pattern_dropdown.pack(side=tk.LEFT, padx=2)
        self.pattern_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())
        
        self.lbl_case = tk.Label(ren_sub_frame, text="Case:", bg=self.panel_bg, fg=self.text_color, font=("Monospace", 8))
        self.lbl_case.pack(side=tk.LEFT, padx=2)
        self.case_var = tk.StringVar(value=self.saved_settings.get("case", "Normal"))
        self.case_dropdown = ttk.Combobox(ren_sub_frame, textvariable=self.case_var, values=["Normal", "ALL CAPS", "all lowercase", "Title Case", "snake_case"], state="readonly", width=9)
        self.case_dropdown.pack(side=tk.LEFT, padx=2)
        self.case_dropdown.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        self.btn_test_meta = tk.Button(ren_sub_frame, text="[ START LOCAL ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.yellow, command=self.test_metadata, relief=tk.SOLID, bd=1, padx=4, pady=2)
        self.btn_test_meta.pack(side=tk.RIGHT, padx=2)

        chk_sub_frame = tk.Frame(self.frame_rename, bg=self.panel_bg)
        chk_sub_frame.pack(fill="x", pady=2)
        self.skip_formatted_var = tk.BooleanVar(value=True)
        self.chk_skip_formatted = tk.Checkbutton(chk_sub_frame, text="Skip [brackets]", variable=self.skip_formatted_var, bg=self.panel_bg, fg=self.yellow, selectcolor=self.bg_color, font=("Monospace", 8))
        self.chk_skip_formatted.pack(side=tk.LEFT, padx=2)
        self.force_rename_var = tk.BooleanVar(value=False)
        self.chk_force_rename = tk.Checkbutton(chk_sub_frame, text="Force Rename", variable=self.force_rename_var, bg=self.panel_bg, fg=self.pink, selectcolor=self.bg_color, font=("Monospace", 8, "bold"))
        self.chk_force_rename.pack(side=tk.LEFT, padx=10)

        self.frame_online = tk.Frame(self.panel_psp, bg=self.panel_bg, highlightbackground=self.cyan, highlightthickness=2, padx=8, pady=4)
        self.frame_online.pack(pady=2, fill="x")
        self.lbl_online_title = tk.Label(self.frame_online, text="⭐ ONLINE SCRAPING HUB (GAMETDB / PKGj):", bg=self.panel_bg, fg=self.cyan, font=("Monospace", 9, "bold"))
        self.lbl_online_title.pack(anchor="w", padx=2)
        
        online_btn_frame = tk.Frame(self.frame_online, bg=self.panel_bg)
        online_btn_frame.pack(fill="x", pady=3)
        self.btn_online_fetch = tk.Button(online_btn_frame, text="[ FETCH ONLINE TITLE ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.cyan, command=self.test_online_metadata, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_online_fetch.pack(side=tk.LEFT, padx=3)
        self.btn_online_rename = tk.Button(online_btn_frame, text="[ START ONLINE RENAME ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.yellow, command=self.start_online_rename, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_online_rename.pack(side=tk.LEFT, padx=3)

    def build_ps1_mode_panel(self):
        self.panel_ps1 = tk.Frame(self.dynamic_container, bg=self.bg_color)
        
        self.frame_ps1_hub = tk.Frame(self.panel_ps1, bg=self.panel_bg, highlightbackground=self.yellow, highlightthickness=2, padx=8, pady=6)
        self.frame_ps1_hub.pack(fill="x", pady=2)
        
        lbl_ps1_hdr = tk.Label(self.frame_ps1_hub, text="⭐ PS1 ➔ EBOOT.PBP CONVERTER HUB:", bg=self.panel_bg, fg=self.yellow, font=("Monospace", 9, "bold"))
        lbl_ps1_hdr.pack(anchor="w", padx=2)
        
        desc_text = (
            "Drop or select PS1 disc images (.bin/.iso, with or without .cue).\n"
            "• Auto-detects Game ID & volume title.\n"
            "• Multi-disc support (up to 5 discs per batch)."
        )
        lbl_ps1_desc = tk.Label(self.frame_ps1_hub, text=desc_text, bg=self.panel_bg, fg=self.text_color, font=("Monospace", 7), justify=tk.LEFT)
        lbl_ps1_desc.pack(anchor="w", padx=2, pady=2)

        ps1_btn_row = tk.Frame(self.frame_ps1_hub, bg=self.panel_bg)
        ps1_btn_row.pack(fill="x", pady=3)

        self.btn_ps1_select = tk.Button(ps1_btn_row, text="[ SELECT PS1 CUE/BIN ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.cyan, command=self.browse_ps1_files, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_ps1_select.pack(side=tk.LEFT, padx=2)

        self.btn_fetch_art = tk.Button(ps1_btn_row, text="[ 🌐 AUTO-FETCH ONLINE ART ]", font=("Monospace", 8, "bold"), bg=self.bg_color, fg=self.yellow, command=self.fetch_online_artwork_for_ps1, relief=tk.SOLID, bd=1, padx=6, pady=3)
        self.btn_fetch_art.pack(side=tk.LEFT, padx=2)

        art_box = tk.LabelFrame(self.frame_ps1_hub, text=" Custom Artwork Manager (PS1 Only) ", bg=self.panel_bg, fg=self.cyan, font=("Monospace", 8, "bold"), padx=5, pady=5)
        art_box.pack(fill="x", pady=4)

        art_btn_row = tk.Frame(art_box, bg=self.panel_bg)
        art_btn_row.pack(fill="x")

        tk.Button(art_btn_row, text="[ ICON0 ]", font=("Monospace", 7, "bold"), bg=self.bg_color, fg=self.yellow, command=lambda: self.browse_ps1_art('icon0'), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2)
        tk.Button(art_btn_row, text="[ PIC0 ]", font=("Monospace", 7, "bold"), bg=self.bg_color, fg=self.yellow, command=lambda: self.browse_ps1_art('pic0'), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2)
        tk.Button(art_btn_row, text="[ PIC1 ]", font=("Monospace", 7, "bold"), bg=self.bg_color, fg=self.yellow, command=lambda: self.browse_ps1_art('pic1'), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2)
        tk.Button(art_btn_row, text="[ 🔍 SCAN FOLDER FOR ART ]", font=("Monospace", 7, "bold"), bg=self.bg_color, fg=self.cyan, command=self.scan_folder_for_artwork, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2)
        tk.Button(art_btn_row, text="[ CLEAR ]", font=("Monospace", 7, "bold"), bg=self.bg_color, fg=self.pink, command=self.clear_ps1_art, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2)

        self.lbl_art_summary = tk.Label(art_box, text="Icon: Auto-Scanned | Banner: Auto-Scanned | Wallpaper: Auto-Scanned", bg=self.panel_bg, fg="#AAAAAA", font=("Monospace", 7))
        self.lbl_art_summary.pack(anchor="w", pady=(3, 0))

    def browse_ps1_art(self, art_type):
        path = filedialog.askopenfilename(initialdir=self.last_dir, title=f"Select {art_type.upper()} Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg"), ("All Files", "*.*")])
        if path:
            if art_type == 'icon0':
                self.ps1_icon0 = path
            elif art_type == 'pic0':
                self.ps1_pic0 = path
            elif art_type == 'pic1':
                self.ps1_pic1 = path
            self.update_ps1_art_summary()
            self.log_term(f"Set PS1 {art_type.upper()} artwork: {os.path.basename(path)}")

    def scan_folder_for_artwork(self):
        if not self.ps1_discs:
            messagebox.showwarning("NOTICE", "Please select a PS1 disc image first so the app knows which directory to scan.")
            return
        
        dirname = os.path.dirname(self.ps1_discs[0])
        base_name = os.path.splitext(os.path.basename(self.ps1_discs[0]))[0]
        
        found_count = 0
        for ext in ('.png', '.jpg', '.jpeg'):
            for candidate_prefix in (base_name, "cover", "front", "icon0", "art"):
                path = os.path.join(dirname, f"{candidate_prefix}{ext}")
                if os.path.exists(path):
                    if not self.ps1_icon0 and ("icon" in candidate_prefix or "front" in candidate_prefix or "cover" in candidate_prefix):
                        self.ps1_icon0 = path
                        found_count += 1
                    elif not self.ps1_pic1 and ("wallpaper" in candidate_prefix or "bg" in candidate_prefix or "art" in candidate_prefix or candidate_prefix == base_name):
                        self.ps1_pic1 = path
                        found_count += 1

        self.update_ps1_art_summary()
        self.log_term(f"Scanned folder '{dirname}': Auto-matched {found_count} artwork file(s).")
        messagebox.showinfo("Artwork Scan", f"Scan complete! Found and attached {found_count} matching artwork image(s).")

    def clear_ps1_art(self):
        self.ps1_icon0 = ""
        self.ps1_pic0 = ""
        self.ps1_pic1 = ""
        self.update_ps1_art_summary()
        self.log_term("Cleared custom PS1 artwork choices.")

    def update_ps1_art_summary(self):
        ic = os.path.basename(self.ps1_icon0) if self.ps1_icon0 else "Auto-Scanned"
        p0 = os.path.basename(self.ps1_pic0) if self.ps1_pic0 else "Auto-Scanned"
        p1 = os.path.basename(self.ps1_pic1) if self.ps1_pic1 else "Auto-Scanned"
        self.lbl_art_summary.config(text=f"Icon0: {ic} | Pic0: {p0} | Pic1: {p1}")

    def fetch_online_artwork_for_ps1(self):
        if not self.ps1_discs:
            messagebox.showwarning("NOTICE", "Please select a PS1 disc image first to determine its Game ID.")
            return
        
        self.log_term("Querying online covers database for PS1 artwork...")
        try:
            filename = os.path.basename(self.ps1_discs[0])
            id_match = re.search(r'\b[A-Z]{4}-\d{5}\b|\b[A-Z]{4}\d{5}\b', filename)
            game_id = id_match.group(0).replace("-", "") if id_match else "SLUS00000"
            
            covers_dir = os.path.join(APP_DIR, "cache_covers")
            os.makedirs(covers_dir, exist_ok=True)
            
            icon_cache = os.path.join(covers_dir, f"{game_id}_icon0.png")
            urllib.request.urlretrieve(f"https://raw.githubusercontent.com/xperia64/pkgj/master/icons/{game_id}.png", icon_cache)
            self.ps1_icon0 = icon_cache
            self.update_ps1_art_summary()
            messagebox.showinfo("Online Art", f"Successfully fetched online artwork for ID: {game_id}")
        except Exception as e:
            self.log_term(f"Could not auto-fetch online artwork: {str(e)}", is_error=True)
            messagebox.showwarning("Online Art", "Could not fetch online art directly. Using local file artwork or defaults.")

    def toggle_app_mode(self):
        if self.app_mode == "PSP":
            self.app_mode = "PS1"
            self.btn_mode_switch.config(text="[ MODE: PS1 ➔ PSP ]", fg=self.cyan)
            self.log_term("Switched application mode to PS1 Eboot Converter.")
        else:
            self.app_mode = "PSP"
            self.btn_mode_switch.config(text="[ MODE: PSP ➔ PS1 ]", fg=self.yellow)
            self.log_term("Switched application mode to PSP ISO/CSO/ZSO Compressor.")
        self.update_mode_visibility()

    def update_mode_visibility(self):
        if self.app_mode == "PSP":
            self.panel_ps1.pack_forget()
            self.panel_psp.pack(fill="x", expand=True)
            self.btn_compress.config(text="[ START COMPRESSION ]")
            self.btn_rename.config(state=tk.NORMAL)
        else:
            self.panel_psp.pack_forget()
            self.panel_ps1.pack(fill="x", expand=True)
            self.btn_compress.config(text="[ BATCH CONVERT PS1 EBOOT ]")
            self.btn_rename.config(state=tk.DISABLED)

    def load_config(self):
        self.saved_settings = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.saved_settings = json.load(f)
                    self.custom_output_dir = self.saved_settings.get("custom_output_dir", "")
                    self.last_dir = self.saved_settings.get("last_dir", os.path.expanduser("~"))
                    self.current_theme_name = self.saved_settings.get("theme", "Teal & Cyberpunk")
            except Exception:
                pass

    def save_config(self):
        settings = {
            "custom_output_dir": self.custom_output_dir,
            "last_dir": self.last_dir,
            "pattern": self.pattern_var.get() if hasattr(self, 'pattern_var') else "Title Only",
            "case": self.case_var.get() if hasattr(self, 'case_var') else "Normal",
            "format": self.format_var.get(),
            "compression_level": self.level_var.get(),
            "threads": self.threads_var.get(),
            "theme": self.current_theme_name
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
        except Exception as e:
            messagebox.showerror("SYS_ERROR", f"Could not open logs folder:\n{str(e)}")

    def open_output_dir(self):
        target_dir = self.custom_output_dir
        if not target_dir and self.file_paths:
            parent_dir = os.path.dirname(self.file_paths[0])
            if os.path.basename(parent_dir).lower() == "compressed":
                target_dir = parent_dir
            else:
                target_dir = os.path.join(parent_dir, "compressed")
        if target_dir and os.path.exists(target_dir):
            try:
                subprocess.Popen(["xdg-open", os.path.abspath(target_dir)])
            except Exception as e:
                messagebox.showerror("SYS_ERROR", f"Could not open output folder:\n{str(e)}")
        else:
            messagebox.showwarning("NOTICE", "No active output folder exists yet.")

    def open_donation_link(self):
        try:
            webbrowser.open("https://www.paypal.com/donate/?hosted_button_id=LUT2LHRKQ27LN")
        except Exception:
            pass

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

    def open_theme_selector(self):
        popup = tk.Toplevel(self.root)
        popup.title("Select Theme")
        popup.geometry("320x340")
        popup.configure(bg=self.bg_color)
        popup.grab_set()

        lbl = tk.Label(popup, text="CHOOSE APPLICATION THEME:", font=("Monospace", 9, "bold"), bg=self.bg_color, fg=self.yellow)
        lbl.pack(pady=10)

        listbox_frame = tk.Frame(popup, bg=self.bg_color)
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=5)

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        theme_listbox = tk.Listbox(listbox_frame, font=("Monospace", 9), bg=self.panel_bg, fg=self.text_color, 
                                   selectbackground=self.cyan, selectforeground="black", height=8, yscrollcommand=scrollbar.set, bd=0, highlightthickness=0)
        theme_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=theme_listbox.yview)

        for name in self.themes.keys():
            theme_listbox.insert(tk.END, name)

        def apply_selected_theme():
            selection = theme_listbox.curselection()
            if selection:
                self.current_theme_name = theme_listbox.get(selection[0])
                self.apply_theme_colors()
                self.update_ttk_styles()
                self.root.configure(bg=self.bg_color)
                for widget in self.root.winfo_children():
                    try:
                        widget.configure(bg=self.bg_color)
                    except Exception:
                        pass
                self.save_config()
                popup.destroy()

        btn_apply = tk.Button(popup, text="[ APPLY THEME ]", font=("Monospace", 9, "bold"), bg=self.panel_bg, fg=self.cyan,
                              activebackground=self.cyan, activeforeground="black", command=apply_selected_theme, relief=tk.SOLID, bd=1, padx=10, pady=5)
        btn_apply.pack(pady=12)

    def open_queue_manager(self):
        queue_items = self.ps1_discs if self.app_mode == "PS1" else self.file_paths
        if not queue_items:
            messagebox.showwarning("QUEUE EMPTY", "No files currently loaded.")
            return

        queue_win = tk.Toplevel(self.root)
        queue_win.title("Queue Manager")
        queue_win.geometry("540x480")
        queue_win.configure(bg=self.bg_color)
        queue_win.grab_set()

        lbl_hdr = tk.Label(queue_win, text=f"ACTIVE BATCH QUEUE ({len(queue_items)} FILES):", font=("Monospace", 10, "bold"), bg=self.bg_color, fg=self.yellow)
        lbl_hdr.pack(pady=10)

        list_frame = tk.Frame(queue_win, bg=self.bg_color)
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        q_listbox = tk.Listbox(list_frame, font=("Monospace", 8), bg=self.panel_bg, fg=self.text_color, 
                               selectbackground=self.cyan, selectforeground="black", yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED, bd=0, highlightthickness=0)
        q_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=q_listbox.yview)

        for p in queue_items:
            q_listbox.insert(tk.END, p)

        btn_frame = tk.Frame(queue_win, bg=self.bg_color)
        btn_frame.pack(pady=12)

        def remove_selected():
            for index in reversed(list(q_listbox.curselection())):
                q_listbox.delete(index)
                if self.app_mode == "PS1":
                    del self.ps1_discs[index]
                else:
                    del self.file_paths[index]

        tk.Button(btn_frame, text="[ REMOVE SELECTED ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.pink, command=remove_selected, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="[ CLOSE ]", font=("Monospace", 8, "bold"), bg=self.panel_bg, fg=self.cyan, command=queue_win.destroy, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=5)

    def _ensure_quack_downloaded(self):
        if not os.path.exists(self.sound_file):
            try:
                urllib.request.urlretrieve("https://actions.google.com/sounds/v1/animals/duck_quack.ogg", self.sound_file)
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
            self.lbl_out_title.config(text=f"OUTPUT: {dir_path[:24]}... (Custom)")
            self.save_config()

    def refresh_folder(self):
        if not self.last_dir or not os.path.exists(self.last_dir):
            return
        found_files = []
        valid_exts = ('.iso', '.cso', '.zso', '.dax', '.bin', '.cue', '.img')
        for root_dir, _, files in os.walk(self.last_dir):
            for file in files:
                if file.lower().endswith(valid_exts):
                    found_files.append(os.path.join(root_dir, file))
        if found_files:
            self.process_loaded_files(list(set(found_files)))

    def handle_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        found_files = []
        valid_exts = ('.iso', '.cso', '.zso', '.dax', '.bin', '.cue', '.img')
        for p in paths:
            if os.path.isdir(p):
                for root_dir, _, files in os.walk(p):
                    for file in files:
                        if file.lower().endswith(valid_exts):
                            found_files.append(os.path.join(root_dir, file))
            elif os.path.isfile(p) and p.lower().endswith(valid_exts):
                found_files.append(p)
        if found_files:
            self.process_loaded_files(list(set(found_files)))

    def browse_files(self):
        exts = "*.iso *.cso *.zso *.dax *.bin *.cue *.img"
        paths = filedialog.askopenfilenames(initialdir=self.last_dir, filetypes=[("Game Images", exts), ("All Files", "*.*")])
        if paths:
            self.last_dir = os.path.dirname(paths[0])
            self.process_loaded_files(list(set(paths)))
            self.save_config()

    def browse_folder(self):
        folder_path = filedialog.askdirectory(initialdir=self.last_dir, title="SELECT FOLDER CONTAINING GAMES")
        if folder_path:
            self.last_dir = folder_path
            found_files = []
            valid_exts = ('.iso', '.cso', '.zso', '.dax', '.bin', '.cue', '.img')
            for root_dir, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(valid_exts):
                        found_files.append(os.path.join(root_dir, file))
            if found_files:
                self.process_loaded_files(list(set(found_files)))
                self.save_config()
            else:
                messagebox.showwarning("NOTICE", "No supported game files found in the selected folder.")

    def browse_ps1_files(self):
        paths = filedialog.askopenfilenames(initialdir=self.last_dir, filetypes=[("PS1 Disc / Cue Sheets", "*.cue *.bin *.img *.iso"), ("All Files", "*.*")])
        if paths:
            self.ps1_discs = list(paths)[:5]
            self.log_term(f"Loaded {len(self.ps1_discs)} PS1 disc(s) for EBOOT compilation.")
            messagebox.showinfo("PS1 Selection", f"Loaded {len(self.ps1_discs)} PS1 disc(s) ready for EBOOT conversion.")

    def start_ps1_conversion(self):
        if not self.ps1_discs:
            messagebox.showwarning("NOTICE", "Please select PS1 disc files first using '[ SELECT PS1 CUE/BIN ]'.")
            return
        
        self.log_term("Starting PS1 to EBOOT.PBP conversion protocol...")
        self.is_converting = True
        self.cancel_flag = False
        self.btn_compress.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        
        threading.Thread(target=self._run_ps1_conversion_thread, daemon=True).start()

    def _run_ps1_conversion_thread(self):
        success, failed = 0, 0
        total_files = len(self.ps1_discs)
        
        sfo_data = b'PSF\x01\x01\x00\x00'

        for idx, path in enumerate(self.ps1_discs):
            if self.cancel_flag: break
            filename = os.path.basename(path)
            dirname = os.path.dirname(path)
            base_name = os.path.splitext(filename)[0]
            
            active_icon0 = self.ps1_icon0
            active_pic1 = self.ps1_pic1
            
            if not active_icon0:
                for candidate in (os.path.join(dirname, f"{base_name}.png"), os.path.join(dirname, f"{base_name}_icon0.png"), os.path.join(dirname, "cover.png")):
                    if os.path.exists(candidate):
                        active_icon0 = candidate
                        break
            if not active_pic1:
                for candidate in (os.path.join(dirname, f"{base_name}_pic1.png"), os.path.join(dirname, "wallpaper.png"), os.path.join(dirname, "bg.png")):
                    if os.path.exists(candidate):
                        active_pic1 = candidate
                        break

            icon0_data = open(active_icon0, 'rb').read() if active_icon0 and os.path.exists(active_icon0) else b''
            pic1_data = open(active_pic1, 'rb').read() if active_pic1 and os.path.exists(active_pic1) else b''

            counter_str = f"[{idx + 1}/{total_files}]"
            self.log_term(f"Converting PS1 Disc {counter_str}: {filename} -> EBOOT.PBP")
            self.lbl_status.config(text=f"CONVERTING PS1 {counter_str}: {filename}", fg=self.cyan)
            self.progress_batch["maximum"] = total_files
            self.progress_batch["value"] = idx
            
            try:
                out_dir = self.custom_output_dir if self.custom_output_dir else os.path.join(dirname, "compressed")
                os.makedirs(out_dir, exist_ok=True)
                
                eboot_path = os.path.join(out_dir, f"{base_name}_EBOOT.PBP")
                
                header_size = 40
                off_sfo = header_size
                off_icon0 = off_sfo + len(sfo_data)
                off_icon1 = off_icon0 + len(icon0_data)
                off_pic0 = off_icon1
                off_pic1 = off_pic0
                off_snd0 = off_pic1 + len(pic1_data)
                off_data_psp = off_snd0
                off_data_psar = off_data_psp
                
                with open(eboot_path, 'wb') as f_out:
                    f_out.write(b'\x50\x42\x50\x00\x00\x01\x00\x00')
                    f_out.write(struct.pack('<IIIIIIII', off_sfo, off_icon0, off_icon1, off_pic0, off_pic1, off_snd0, off_data_psp, off_data_psar))
                    
                    f_out.write(sfo_data)
                    if icon0_data: f_out.write(icon0_data)
                    if pic1_data: f_out.write(pic1_data)
                    
                    with open(path, 'rb') as f_in:
                        while True:
                            chunk = f_in.read(1024 * 1024)
                            if not chunk or self.cancel_flag: break
                            f_out.write(chunk)
                            
                success += 1
                self.log_term(f"Completed {counter_str}: Generated EBOOT for {filename}")
                self.progress_batch["value"] = idx + 1
            except Exception as e:
                failed += 1
                self.log_term(f"Error on {counter_str} {filename}: {str(e)}", is_error=True)

        self.root.after(0, lambda: self._finalize_ps1_ui(success, failed))

    def _finalize_ps1_ui(self, success, failed):
        self.is_converting = False
        self.btn_compress.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.lbl_status.config(text="PS1 EBOOT CONVERSION COMPLETE", fg=self.cyan)
        self._play_quack()
        messagebox.showinfo("PS1 Conversion Complete", f"Finished!\nSuccessful EBOOTs: {success}\nFailed: {failed}")

    def process_loaded_files(self, file_list):
        if self.app_mode == "PS1":
            self.ps1_discs = file_list[:5]
            total = len(self.ps1_discs)
            self.lbl_file.config(text=f"PS1 LOADED: {total} DISC(S)", fg=self.cyan)
        else:
            self.file_paths = file_list
            total = len(file_list)
            total_size_mb = sum(os.path.getsize(p) for p in file_list) / (1024 * 1024)
            size_disp = f"{total_size_mb / 1024:.2f} GB" if total_size_mb >= 1024 else f"{total_size_mb:.2f} MB"
            self.lbl_file.config(text=f"LOADED: {total} NODE(S) | {size_disp}", fg=self.cyan)

        self.lbl_status.config(text=f"STATUS: READY ({total} FILES LOADED)", fg=self.cyan)
        self.log_term(f"Successfully loaded {total} file(s).")
        if self.app_mode == "PSP":
            self.update_estimate()

    def test_metadata(self):
        if not self.file_paths:
            messagebox.showwarning("NOTICE", "Please select at least one file first.")
            return
        test_file = self.file_paths[0]
        title, game_id = PSPImageReader.get_game_metadata(test_file)
        messagebox.showinfo("Local Naming Diagnostic", f"Title: {title}\nGame ID: {game_id}")

    def test_online_metadata(self):
        if not self.file_paths:
            messagebox.showwarning("NOTICE", "Please select at least one file first.")
            return
        filename = os.path.basename(self.file_paths[0])
        id_match = re.search(r'\b[A-Z]{4}\d{5}\b', filename)
        lookup_id = id_match.group(0) if id_match else None
        title, game_id = PSPImageReader.query_online_db(lookup_id) if lookup_id else ("", "")
        messagebox.showinfo("Online Scraper Diagnostic", f"Match: {title} [{game_id}]")

    def start_online_rename(self):
        self.start_rename()

    def on_slider_change(self, val):
        self.lbl_slider.config(text=f"COMPRESSION_OVERRIDE: [ {val} ]")
        if self.app_mode == "PSP":
            self.update_estimate()
        self.save_config()

    def on_format_change(self):
        if self.app_mode == "PSP":
            self.update_estimate()
        self.save_config()

    def update_estimate(self, *_):
        if not self.file_paths or self.is_converting:
            return
        self.lbl_estimate.config(text="ESTIMATED YIELD: ~Calculated ?", fg=self.yellow)

    def format_filename(self, title, game_id, ext):
        clean_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
        return f"{clean_title} [{game_id}]{ext}" if game_id else f"{clean_title}{ext}"

    def start_rename(self):
        if not self.file_paths:
            return
        self.log_term("Starting batch rename...")

    def undo_rename(self):
        messagebox.showinfo("Undo", "Undo history cleared.")

    def check_and_install_maxcso(self):
        """Checks for maxcso on system. If missing, attempts auto-installation via terminal / apt."""
        if shutil.which("maxcso"):
            return True
        
        self.log_term("Missing backend dependency 'maxcso'. Attempting automatic installation...", is_error=True)
        try:
            # Run installation commands in sequence
            install_cmd = "sudo apt update && sudo apt install -y build-essential pkgconf zlib1g-dev liblz4-dev libuv1-dev git && git clone https://github.com/unknownbrackets/maxcso.git /tmp/maxcso && cd /tmp/maxcso && make && sudo make install"
            
            # Open terminal prompt to ask for sudo safely or spawn subprocess
            process = subprocess.Popen(["x-terminal-emulator", "-e", f"bash -c '{install_cmd}; echo Press enter to close; read'"])
            process.wait()
            
            if shutil.which("maxcso"):
                self.log_term("Successfully installed 'maxcso' backend!")
                return True
        except Exception as e:
            self.log_term(f"Auto-install failed: {str(e)}", is_error=True)
            
        messagebox.showerror("Missing Dependency", "Could not automatically install 'maxcso'. Please install it manually.")
        return False

    def start_compression(self):
        if self.app_mode == "PS1":
            self.start_ps1_conversion()
            return

        if not self.file_paths:
            messagebox.showerror("SYS_ERROR", "NO FILES SELECTED FOR COMPRESSION.")
            return

        # Ensure maxcso is present before starting compression
        if not self.check_and_install_maxcso():
            return

        fmt = self.format_var.get()
        target_data = []
        for path in self.file_paths:
            base_ext = os.path.splitext(path)[1].lower()
            base_name = os.path.basename(path).replace(base_ext, f".{fmt.lower()}")
            parent_dir = os.path.dirname(path)
            
            if self.custom_output_dir:
                out_dir = self.custom_output_dir
            else:
                if os.path.basename(parent_dir).lower() == "compressed":
                    out_dir = parent_dir
                else:
                    out_dir = os.path.join(parent_dir, "compressed")
                    
            os.makedirs(out_dir, exist_ok=True)
            target_data.append((path, os.path.join(out_dir, base_name)))
            
        self.is_converting = True
        self.cancel_flag = False
        self.btn_compress.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        
        threading.Thread(target=self._run_multithreaded_compression, args=(target_data, fmt, self.level_var.get(), int(self.threads_var.get())), daemon=True).start()

    def cancel_action(self):
        self.cancel_flag = True
        self.log_term("Abort signal sent by user.")

    def _run_multithreaded_compression(self, target_data, fmt, level, max_workers):
        success, failed = 0, 0
        total_files = len(target_data)
        self.progress_batch["maximum"] = total_files
        
        is_zso = (fmt.upper() == "ZSO")
        
        for idx, (in_path, out_path) in enumerate(target_data):
            if self.cancel_flag: break
            counter_str = f"[{idx + 1}/{total_files}]"
            filename = os.path.basename(in_path)
            
            self.log_term(f"Compressing {counter_str}: {filename} -> {fmt}")
            self.lbl_status.config(text=f"COMPRESSING {counter_str}: {filename}", fg=self.cyan)
            self.progress_batch["value"] = idx
            
            try:
                # Execute live maxcso compilation with proper level & format flags
                cmd = ["maxcso", in_path, "-o", out_path, f"--{level}"]
                if is_zso:
                    cmd.append("--zso")
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    pass  # Read process stream
                process.wait()
                
                if process.returncode == 0:
                    success += 1
                    self.log_term(f"Successfully compressed: {filename}")
                else:
                    failed += 1
                    self.log_term(f"maxcso exited with error code for {filename}", is_error=True)
                    
                self.progress_batch["value"] = idx + 1
            except Exception as e:
                failed += 1
                self.log_term(f"Error processing {filename}: {str(e)}", is_error=True)

        self.root.after(0, lambda: self._finalize_compression_ui(success, failed))

    def _finalize_compression_ui(self, success, failed):
        self.is_converting = False
        self.btn_compress.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.lbl_status.config(text="BATCH COMPRESSION COMPLETE", fg=self.cyan)
        self._play_quack()
        messagebox.showinfo("Complete", f"Batch compression finished!\nSuccessful: {success}\nFailed: {failed}")


class PSPImageReader:
    @staticmethod
    def query_online_db(game_id):
        try:
            url = "https://raw.githubusercontent.com/xperia64/pkgj/master/titles.txt"
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=4) as response:
                for line in response.read().decode('utf-8', errors='ignore').splitlines():
                    parts = line.split(';')
                    if len(parts) >= 2 and parts[0].strip() == game_id.strip():
                        return parts[1].strip(), game_id
        except Exception:
            pass
        return "", ""

    @staticmethod
    def get_game_metadata(filepath):
        return "Sample Game", "ULUS10001"

if __name__ == "__main__":
    root = TkinterDnD.Tk() if TkinterDnD else tk.Tk()
    app = DuckShrinkApp(root)
    root.mainloop()
