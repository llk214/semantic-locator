"""
Modern GUI for the Semantic Page Locator
Uses customtkinter for iOS-style rounded corners
Supports Chinese / English language switching
"""

import sys
import os
import io

# Suppress HuggingFace symlink warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# ----------------------------
# FastEmbed cache configuration
# ----------------------------
from pathlib import Path

def _default_fastembed_cache_dir() -> str:
    """Choose a persistent cache directory for FastEmbed (avoid system Temp)."""
    home = str(Path.home())
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or home
        return os.path.join(base, "Locus", "fastembed_cache")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Caches", "Locus", "fastembed_cache")
    return os.path.join(home, ".cache", "Locus", "fastembed_cache")

os.environ.setdefault("FASTEMBED_CACHE_PATH", _default_fastembed_cache_dir())
os.makedirs(os.environ["FASTEMBED_CACHE_PATH"], exist_ok=True)

# Fix for PyInstaller + sentence-transformers (isatty error)
if getattr(sys, 'frozen', False):
    if sys.stdout is None or not hasattr(sys.stdout, 'isatty'):
        sys.stdout = io.StringIO()
    if sys.stderr is None or not hasattr(sys.stderr, 'isatty'):
        sys.stderr = io.StringIO()

import tkinter as tk
import tkinter.font as tkfont

# Import i18n
from i18n import t, get_lang, set_lang


# ----------------------------
# Font configuration
# ----------------------------
# Windows Chinese fonts in priority order
_ZH_FONT_CANDIDATES = [
    "Microsoft YaHei UI",   # 微软雅黑 UI — best for UI, ships with Win7+
    "Microsoft YaHei",      # 微软雅黑
    "SimHei",               # 黑体 — always available on Chinese Windows
    "DengXian",             # 等线 — Win10+ default
    "Source Han Sans SC",   # 思源黑体
    "Noto Sans CJK SC",    # Google Noto
]

_EN_FONT = "Segoe UI"
_MONO_FONT = "Consolas"
_EMOJI_FONT = "Segoe UI Emoji"

_zh_font_cache = None

def _resolve_zh_font(root=None) -> str:
    """Find the best available Chinese font on this system."""
    global _zh_font_cache
    if _zh_font_cache is not None:
        return _zh_font_cache

    available = set()
    try:
        if root:
            available = set(tkfont.families(root))
        else:
            available = set(tkfont.families())
    except Exception:
        pass

    for candidate in _ZH_FONT_CANDIDATES:
        if candidate in available:
            _zh_font_cache = candidate
            return candidate

    _zh_font_cache = _EN_FONT
    return _zh_font_cache


def ui_font(size: int = 11, bold: bool = False) -> tuple:
    """Return the correct UI font tuple for the current language."""
    if get_lang() == "zh":
        family = _resolve_zh_font()
    else:
        family = _EN_FONT
    if bold:
        return (family, size, "bold")
    return (family, size)


def mono_font(size: int = 10) -> tuple:
    return (_MONO_FONT, size)


def emoji_font(size: int = 48) -> tuple:
    return (_EMOJI_FONT, size)


# ===== Splash Screen (shows immediately while loading) =====
class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # No window decorations
        
        # Resolve Chinese font now that we have a tk root
        _resolve_zh_font(self.root)
        
        # Window size (increased height to prevent text cutoff)
        width, height = 420, 320
        
        # Center on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Background
        self.root.configure(bg="#1a1a2e")
        
        # Main frame with border effect
        frame = tk.Frame(self.root, bg="#1a1a2e", padx=30, pady=30)
        frame.pack(expand=True, fill="both")
        
        # Icon/Logo area
        logo_label = tk.Label(frame, text="📚", font=emoji_font(48), 
                              bg="#1a1a2e", fg="white")
        logo_label.pack(pady=(10, 5))
        
        # App name
        title_label = tk.Label(frame, text="Locus", 
                               font=ui_font(22, bold=True),
                               bg="#1a1a2e", fg="#ffffff")
        title_label.pack(pady=(0, 5))
        
        # Tagline
        tagline_label = tk.Label(frame, text=t("splash.tagline"), 
                                  font=ui_font(10),
                                  bg="#1a1a2e", fg="#888899")
        tagline_label.pack(pady=(0, 25))
        
        # Loading bar background
        self.bar_max = width - 140
        bar_bg = tk.Frame(frame, bg="#2d2d44", height=6, width=self.bar_max)
        bar_bg.pack()
        bar_bg.pack_propagate(False)
        
        # Loading bar (step-based)
        self.bar_fill = tk.Frame(bar_bg, bg="#4f8cff", height=6, width=0)
        self.bar_fill.place(x=0, y=0, height=6)
        
        # Status text
        self.status_var = tk.StringVar(value=t("splash.initializing"))
        status_label = tk.Label(frame, textvariable=self.status_var,
                                font=ui_font(9),
                                bg="#1a1a2e", fg="#666677")
        status_label.pack(pady=(15, 0))
        
        # Version
        version_label = tk.Label(frame, text="v0.2.0", 
                                 font=ui_font(8),
                                 bg="#1a1a2e", fg="#444455")
        version_label.pack(side="bottom", pady=(15, 5))
        
        self.root.update()
    
    def set_progress(self, percent):
        """Set progress bar to specific percentage."""
        width = int(self.bar_max * percent / 100)
        self.bar_fill.configure(width=width)
        self.root.update()
    
    def set_status(self, text, percent=None):
        """Update status text and optionally progress."""
        self.status_var.set(text)
        if percent is not None:
            self.set_progress(percent)
        self.root.update()
    
    def close(self):
        """Close splash screen."""
        self.root.destroy()

# Show splash immediately
splash = SplashScreen()
splash.set_status(t("splash.loading_libs"), 10)

# Now import heavy libraries
import customtkinter as ctk
splash.set_status(t("splash.loading_ui"), 25)

from tkinter import filedialog, messagebox
from tkinter import ttk
from pathlib import Path
import threading
import subprocess
import platform
import os
splash.set_status(t("splash.loading_engine"), 40)

from locator import HybridLocator
splash.set_status(t("splash.starting"), 95)

# Set appearance
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def get_app_dir():
    """Get the directory where the app is running from."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def open_pdf_at_page(pdf_path: str, page_num: int):
    """Open PDF at specific page using bundled or system PDF viewer."""
    system = platform.system()
    pdf_path = os.path.abspath(pdf_path)
    
    if system == "Windows":
        app_dir = get_app_dir()
        bundled_sumatra_paths = [
            os.path.join(app_dir, "_internal", "SumatraPDF", "SumatraPDF.exe"),
            os.path.join(app_dir, "_internal", "SumatraPDF.exe"),
            os.path.join(app_dir, "SumatraPDF", "SumatraPDF.exe"),
            os.path.join(app_dir, "SumatraPDF.exe"),
        ]
        
        for sumatra in bundled_sumatra_paths:
            if os.path.exists(sumatra):
                subprocess.Popen([sumatra, "-page", str(page_num), pdf_path])
                return True
        
        sumatra_paths = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
        ]
        
        for sumatra in sumatra_paths:
            if os.path.exists(sumatra):
                subprocess.Popen([sumatra, "-page", str(page_num), pdf_path])
                return True
        
        adobe_paths = [
            r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        ]
        
        for adobe in adobe_paths:
            if os.path.exists(adobe):
                subprocess.Popen([adobe, "/A", f"page={page_num}", pdf_path])
                return True
        
        os.startfile(pdf_path)
        return False
        
    elif system == "Darwin":
        script = f'''
        tell application "Preview"
            open POSIX file "{pdf_path}"
            activate
        end tell
        delay 0.5
        tell application "System Events"
            keystroke "g" using {{option down, command down}}
            delay 0.2
            keystroke "{page_num}"
            keystroke return
        end tell
        '''
        subprocess.Popen(["osascript", "-e", script])
        return True
        
    else:
        viewers = [
            (["evince", "-p", str(page_num), pdf_path], "evince"),
            (["okular", "-p", str(page_num), pdf_path], "okular"),
            (["xdg-open", pdf_path], "xdg-open"),
        ]
        
        for cmd, name in viewers:
            try:
                subprocess.Popen(cmd)
                return name != "xdg-open"
            except FileNotFoundError:
                continue
        
        return False


class ResultCard(ctk.CTkFrame):
    """A single result card with modern styling."""
    
    def __init__(self, parent, rank, pdf_name, page_num, score, snippet, on_click, on_double_click):
        super().__init__(parent, corner_radius=8, fg_color=("gray90", "gray20"))
        
        self.pdf_name = pdf_name
        self.page_num = page_num
        self.snippet = snippet
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.selected = False
        
        self.grid_columnconfigure(1, weight=1)
        
        # Rank badge
        rank_label = ctk.CTkLabel(self, text=f"#{rank}", font=ui_font(11, bold=True),
                                   width=30, fg_color=("gray80", "gray30"), corner_radius=5)
        rank_label.grid(row=0, column=0, rowspan=2, padx=(8, 8), pady=8)
        
        # PDF name and page
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(8, 2))
        header_frame.grid_columnconfigure(0, weight=1)
        
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info_frame, text=pdf_name, font=ui_font(11, bold=True),
                     anchor="w").pack(side="left")
        
        ctk.CTkLabel(info_frame, text=f"  📄 {t('results.page', num=page_num)}", font=ui_font(10),
                     text_color="gray", anchor="w").pack(side="left")
        
        # Score badge
        score_color = "#28a745" if score > 0.7 else "#ffc107" if score > 0.4 else "#6c757d"
        ctk.CTkLabel(header_frame, text=f"{score:.2f}", font=ui_font(9),
                     fg_color=score_color, corner_radius=4, text_color="white",
                     padx=6, pady=1).pack(side="right", padx=(0, 5))
        
        # Snippet preview
        snippet_short = snippet[:120] + "..." if len(snippet) > 120 else snippet
        snippet_short = ' '.join(snippet_short.split())
        self.snippet_label = ctk.CTkLabel(self, text=snippet_short, font=ui_font(10),
                                           anchor="w", justify="left", text_color="gray")
        self.snippet_label.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))
        
        # Bind click events to all children
        self._bind_click_recursive(self)
    
    def _bind_click_recursive(self, widget):
        widget.bind("<Button-1>", self._handle_click)
        widget.bind("<Double-Button-1>", self._handle_double_click)
        for child in widget.winfo_children():
            self._bind_click_recursive(child)
    
    def _handle_click(self, event):
        self.on_click(self)
    
    def _handle_double_click(self, event):
        self.on_double_click(self)
    
    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self.configure(fg_color=("lightblue", "#1f538d"))
        else:
            self.configure(fg_color=("gray90", "gray20"))


class LocatorGUI(ctk.CTk):
    
    # ---- Central model registry ----
    # Each entry: (i18n_key, model_name, download_size, ram_hint, group)
    # group: "en", "zh", "multi"
    ALL_MODELS = [
        ("quality.balanced",     "BAAI/bge-small-en-v1.5",  "Built-in", "4GB RAM",   "en"),
        ("quality.high",         "BAAI/bge-base-en-v1.5",   "210MB",    "8GB RAM",   "en"),
        ("quality.best",         "BAAI/bge-large-en-v1.5",  "1.2GB",    "16GB RAM",  "en"),
        ("quality.balanced",     "BAAI/bge-small-zh-v1.5",  "90MB",     "4GB RAM",   "zh"),
        ("quality.best",         "BAAI/bge-large-zh-v1.5",  "1.2GB",    "16GB RAM",  "zh"),
        ("quality.multilingual", "BAAI/bge-m3",             "2.2GB",    "16GB+ RAM", "multi"),
    ]
    
    @staticmethod
    def _get_models_for_lang(lang: str) -> list[tuple]:
        """Return models relevant to the given UI language.
        
        English mode:  en models + multilingual
        Chinese mode:  zh models + multilingual
        """
        target_groups = {"multi", lang}
        return [m for m in LocatorGUI.ALL_MODELS if m[4] in target_groups]
    
    def _build_quality_dicts(self):
        """Build quality_options, quality_sizes, quality_ram from current language."""
        models = self._get_models_for_lang(get_lang())
        self.quality_options = {}
        self.quality_sizes = {}
        self.quality_ram = {}
        for i18n_key, model_name, size, ram, _group in models:
            label = t(i18n_key)
            self.quality_options[label] = model_name
            self.quality_sizes[label] = size
            self.quality_ram[label] = ram
    def __init__(self):
        super().__init__()
        
        self.title(t("app.title"))
        self.geometry("900x650")
        self.minsize(650, 500)
        
        # Auto-scale based on screen resolution
        screen_width = self.winfo_screenwidth()
        if screen_width >= 3840:
            ctk.set_widget_scaling(0.85)
        elif screen_width >= 2560:
            ctk.set_widget_scaling(0.92)
        
        self.locator = None
        self.pdf_dir = None
        self.current_results = []
        self.result_cards = []
        self.selected_card = None
        self._searching = False
        
        # Track translatable widgets for language switching
        self._i18n_widgets = []
        
        self._create_widgets()
    
    def _register_i18n(self, widget, method, key, font_size=None, font_bold=False, **kwargs):
        """Register a widget for language-switch updates.
        
        Args:
            widget: The tkinter/ctk widget
            method: 'configure' key, e.g. 'text' or 'placeholder_text'
            key: i18n translation key
            font_size: if set, also update font on language switch
            font_bold: whether font is bold
            **kwargs: extra format arguments for t()
        """
        self._i18n_widgets.append((widget, method, key, kwargs, font_size, font_bold))
    
    def _refresh_i18n(self):
        """Re-apply all translations and fonts after language switch."""
        self.title(t("app.title"))
        
        for entry in self._i18n_widgets:
            widget, method, key, kwargs, font_size, font_bold = entry
            try:
                text = t(key, **kwargs) if kwargs else t(key)
                cfg = {method: text}
                if font_size is not None:
                    cfg["font"] = ui_font(font_size, bold=font_bold)
                widget.configure(**cfg)
            except Exception:
                pass
        
        # Update the language toggle button text
        if hasattr(self, 'lang_btn'):
            self.lang_btn.configure(text=t("lang.switch"), font=ui_font(10))
        
        # Update quality option menu
        if hasattr(self, 'quality_menu'):
            self._rebuild_quality_menu()
            # Update RAM info for current selection
            current_quality = self.quality_var.get()
            self.quality_info_var.set(self.quality_ram.get(current_quality, ""))
        
        # Update status label font
        if hasattr(self, 'status_label'):
            self.status_label.configure(font=ui_font(11))
        
        # Update status if it's the default
        current_status = self.status_var.get()
        if current_status in ("Select a directory with PDFs", "请选择包含PDF的文件夹"):
            self.status_var.set(t("status.select_dir"))
    
    def _rebuild_quality_menu(self):
        """Rebuild quality options for current language."""
        # Remember current model_name before rebuild
        current_model = None
        for label, model_name in getattr(self, 'quality_options', {}).items():
            if label == self.quality_var.get():
                current_model = model_name
                break
        
        self._build_quality_dicts()
        
        # Try to keep the same model selected; fall back to first (default)
        new_display = list(self.quality_options.keys())[0]
        if current_model:
            for label, model_name in self.quality_options.items():
                if model_name == current_model:
                    new_display = label
                    break
        
        self.quality_var.set(new_display)
        self.quality_menu.configure(values=list(self.quality_options.keys()))
        self._update_model_status()
    
    def _toggle_language(self):
        """Toggle between Chinese and English."""
        current = get_lang()
        new_lang = "en" if current == "zh" else "zh"
        set_lang(new_lang)
        self._refresh_i18n()
    
    def _create_widgets(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        
        # ===== Top Frame - Directory Selection =====
        top_frame = ctk.CTkFrame(self, corner_radius=8)
        top_frame.grid(row=0, column=0, padx=12, pady=(12, 2), sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)
        
        # Language switch button (top-right of top frame)
        self.lang_btn = ctk.CTkButton(
            top_frame, text=t("lang.switch"), command=self._toggle_language,
            width=65, height=26, corner_radius=6,
            fg_color=("gray75", "gray35"), hover_color=("gray65", "gray45"),
            font=ui_font(10)
        )
        self.lang_btn.grid(row=0, column=4, padx=(4, 12), pady=12)
        
        dir_label = ctk.CTkLabel(top_frame, text=t("dir.label"), font=ui_font(12))
        dir_label.grid(row=0, column=0, padx=(12, 8), pady=12)
        self._register_i18n(dir_label, "text", "dir.label", font_size=12)
        
        self.dir_entry = ctk.CTkEntry(top_frame, placeholder_text=t("dir.placeholder"), 
                                       height=30, corner_radius=6)
        self.dir_entry.grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        self._register_i18n(self.dir_entry, "placeholder_text", "dir.placeholder")
        
        browse_btn = ctk.CTkButton(top_frame, text=t("dir.browse"), command=self._browse_dir,
                      width=80, height=30, corner_radius=6)
        browse_btn.grid(row=0, column=2, padx=4, pady=12)
        self._register_i18n(browse_btn, "text", "dir.browse")
        
        load_btn = ctk.CTkButton(top_frame, text=t("dir.load_index"), command=self._load_index,
                      width=100, height=30, corner_radius=6,
                      fg_color="#28a745", hover_color="#218838")
        load_btn.grid(row=0, column=3, padx=(4, 4), pady=12)
        self._register_i18n(load_btn, "text", "dir.load_index")
        
        # ===== Status Label =====
        self.status_var = tk.StringVar(value=t("status.select_dir"))
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_var, 
                                          font=ui_font(11), text_color="gray")
        self.status_label.grid(row=1, column=0, padx=12, pady=2)
        
        # ===== Search Frame =====
        search_frame = ctk.CTkFrame(self, corner_radius=8)
        search_frame.grid(row=2, column=0, padx=12, pady=2, sticky="ew")
        search_frame.grid_columnconfigure(1, weight=1)
        
        search_label = ctk.CTkLabel(search_frame, text=t("search.label"), font=ui_font(12))
        search_label.grid(row=0, column=0, padx=(12, 8), pady=12)
        self._register_i18n(search_label, "text", "search.label", font_size=12)
        
        self.query_entry = ctk.CTkEntry(search_frame, placeholder_text=t("search.placeholder"),
                                         height=32, corner_radius=6, font=ui_font(11))
        self.query_entry.grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        self._register_i18n(self.query_entry, "placeholder_text", "search.placeholder", font_size=11)
        self.query_entry.bind('<Return>', lambda e: self._search())
        
        search_btn = ctk.CTkButton(search_frame, text=t("search.button"), command=self._search,
                      width=100, height=32, corner_radius=6, font=ui_font(11))
        search_btn.grid(row=0, column=2, padx=(4, 12), pady=12)
        self._register_i18n(search_btn, "text", "search.button", font_size=11)
        
        # ===== Options Frame =====
        options_frame = ctk.CTkFrame(self, corner_radius=8)
        options_frame.grid(row=3, column=0, padx=12, pady=2, sticky="ew")
        
        # Right side FIRST - Search Mode Slider
        right_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        right_options.pack(side="right", padx=12, pady=8)
        
        semantic_label = ctk.CTkLabel(right_options, text=t("options.semantic"), font=ui_font(10))
        semantic_label.pack(side="left", padx=(0, 8))
        self._register_i18n(semantic_label, "text", "options.semantic", font_size=10)
        
        self.search_mode_var = tk.DoubleVar(value=0.3)
        self.search_slider = ctk.CTkSlider(right_options, from_=0, to=1, 
                                            variable=self.search_mode_var,
                                            width=160, height=16)
        self.search_slider.pack(side="left", padx=4)
        
        literal_label = ctk.CTkLabel(right_options, text=t("options.literal"), font=ui_font(10))
        literal_label.pack(side="left", padx=(8, 0))
        self._register_i18n(literal_label, "text", "options.literal", font_size=10)
        
        # Left side - Results count and Quality
        left_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        left_options.pack(side="left", padx=12, pady=8)
        
        results_label = ctk.CTkLabel(left_options, text=t("options.results"), font=ui_font(11))
        results_label.pack(side="left", padx=(0, 4))
        self._register_i18n(results_label, "text", "options.results", font_size=11)
        
        self.topk_var = tk.StringVar(value="5")
        self.topk_menu = ctk.CTkOptionMenu(left_options, variable=self.topk_var,
                                            values=["3", "5", "10", "15", "20"],
                                            width=60, height=26, corner_radius=6)
        self.topk_menu.pack(side="left", padx=(0, 16))
        
        quality_label = ctk.CTkLabel(left_options, text=t("options.quality"), font=ui_font(11))
        quality_label.pack(side="left", padx=(0, 4))
        self._register_i18n(quality_label, "text", "options.quality", font_size=11)
        
        # Bundled model name
        self.bundled_model = "BAAI/bge-small-en-v1.5"
        
        # Initialize quality options for current language
        self._build_quality_dicts()
        
        self.quality_var = tk.StringVar(value=list(self.quality_options.keys())[0])
        self.quality_menu = ctk.CTkOptionMenu(left_options, variable=self.quality_var,
                                               values=list(self.quality_options.keys()),
                                               width=155, height=26, corner_radius=6,
                                               command=self._on_quality_change)
        self.quality_menu.pack(side="left", padx=(0, 8))
        
        # Download status label
        self.quality_status_var = tk.StringVar(value="")
        self.quality_status_label = ctk.CTkLabel(left_options, textvariable=self.quality_status_var, 
                                                  font=ui_font(9))
        self.quality_status_label.pack(side="left", padx=(0, 4))
        
        first_label = list(self.quality_options.keys())[0]
        self.quality_info_var = tk.StringVar(value=self.quality_ram.get(first_label, ""))
        ctk.CTkLabel(left_options, textvariable=self.quality_info_var, 
                     font=ui_font(9), text_color="gray").pack(side="left")
        
        # Download/Delete button
        self.model_action_btn = ctk.CTkButton(left_options, text="⬇️", command=self._download_model,
                      width=28, height=24, corner_radius=4,
                      fg_color="transparent", hover_color=("gray80", "gray30"),
                      text_color=("gray40", "gray60"))
        self.model_action_btn.pack(side="left", padx=(4, 0))
        
        # Manage models button
        ctk.CTkButton(left_options, text="⚙️", command=self._manage_models,
                      width=28, height=24, corner_radius=4,
                      fg_color="transparent", hover_color=("gray80", "gray30"),
                      text_color=("gray40", "gray60")).pack(side="left", padx=(2, 0))
        
        # Check initial model status
        self._update_model_status()
        
        # ===== Results Frame (Scrollable) =====
        results_container = ctk.CTkFrame(self, corner_radius=8)
        results_container.grid(row=4, column=0, padx=12, pady=2, sticky="nsew")
        results_container.grid_columnconfigure(0, weight=1)
        results_container.grid_rowconfigure(0, weight=1)
        
        self.results_scroll = ctk.CTkScrollableFrame(results_container, corner_radius=6,
                                                      fg_color="transparent")
        self.results_scroll.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.results_scroll.grid_columnconfigure(0, weight=1)
        
        # Placeholder text
        self.placeholder_label = ctk.CTkLabel(self.results_scroll, 
                                               text=t("results.placeholder"),
                                               font=ui_font(11), text_color="gray")
        self.placeholder_label.grid(row=0, column=0, pady=40)
        self._register_i18n(self.placeholder_label, "text", "results.placeholder", font_size=11)
        
        # ===== Bottom Frame =====
        bottom_frame = ctk.CTkFrame(self, corner_radius=8)
        bottom_frame.grid(row=5, column=0, padx=12, pady=(2, 10), sticky="ew")
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        open_btn = ctk.CTkButton(bottom_frame, text=t("bottom.open_pdf"), command=self._open_selected,
                      width=160, height=32, corner_radius=6, font=ui_font(11))
        open_btn.grid(row=0, column=0, padx=12, pady=10)
        self._register_i18n(open_btn, "text", "bottom.open_pdf", font_size=11)
        
        hint_label = ctk.CTkLabel(bottom_frame, text=t("bottom.double_click_hint"), 
                     font=ui_font(10), text_color="gray")
        hint_label.grid(row=0, column=1, padx=8, pady=10, sticky="w")
        self._register_i18n(hint_label, "text", "bottom.double_click_hint", font_size=10)
        
        # Snippet preview
        snippet_label = ctk.CTkLabel(bottom_frame, text=t("bottom.snippet"), font=ui_font(10))
        snippet_label.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="w")
        self._register_i18n(snippet_label, "text", "bottom.snippet", font_size=10)
        
        self.snippet_text = ctk.CTkTextbox(bottom_frame, height=60, corner_radius=6,
                                            font=mono_font(10))
        self.snippet_text.grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 10), sticky="ew")
    
    def _browse_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def _on_quality_change(self, choice):
        self.quality_info_var.set(self.quality_ram.get(choice, ""))
        self._update_model_status()
        
        if self.locator:
            self.status_var.set(t("status.quality_changed"))
    
    def _get_fastembed_cache_locations(self):
        """Get FastEmbed cache locations (current + legacy)."""
        import tempfile

        locations = []

        env_path = os.environ.get("FASTEMBED_CACHE_PATH")
        if env_path:
            locations.append(env_path)

        temp_dir = tempfile.gettempdir()
        locations.append(os.path.join(temp_dir, "fastembed_cache"))

        if os.name == "nt":
            localappdata = os.environ.get("LOCALAPPDATA", "")
            if localappdata:
                locations.append(os.path.join(localappdata, "Temp", "fastembed_cache"))
            temp_env = os.environ.get("TEMP", "")
            if temp_env:
                locations.append(os.path.join(temp_env, "fastembed_cache"))

        locations.append(os.path.expanduser("~/.cache/fastembed_cache"))

        seen = set()
        unique_locations = []
        for loc in locations:
            normalized = os.path.normpath(loc)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_locations.append(normalized)

        return unique_locations
    
    def _is_bundled_model(self, model_name):
        return model_name == self.bundled_model
    
    def _get_bundled_model_path(self):
        if getattr(sys, 'frozen', False):
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            possible_paths = [
                os.path.join(base_path, '_internal', 'models', 'bge-small-en-v1.5'),
                os.path.join(base_path, 'models', 'bge-small-en-v1.5'),
                os.path.join(os.path.dirname(sys.executable), '_internal', 'models', 'bge-small-en-v1.5'),
                os.path.join(os.path.dirname(sys.executable), 'models', 'bge-small-en-v1.5'),
            ]
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(script_dir, 'models', 'bge-small-en-v1.5'),
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    if 'model.onnx' in files or 'model_optimized.onnx' in files:
                        return path
        return None
    
    def _is_model_downloaded(self, model_name):
        if self._is_bundled_model(model_name) and self._get_bundled_model_path():
            return True
        
        model_short = model_name.split("/")[-1]
        
        for cache_dir in self._get_fastembed_cache_locations():
            if not os.path.exists(cache_dir):
                continue
            
            try:
                for folder in os.listdir(cache_dir):
                    if model_short in folder or model_short.replace("-", "_") in folder:
                        folder_path = os.path.join(cache_dir, folder)
                        for root, dirs, files in os.walk(folder_path):
                            if 'model.onnx' in files or 'model_optimized.onnx' in files:
                                return True
            except (PermissionError, OSError):
                continue
        
        return False
    
    def _update_model_status(self):
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        size = self.quality_sizes.get(quality, "")
        
        is_bundled = self._is_bundled_model(model_name) if model_name else False
        
        if model_name and self._is_model_downloaded(model_name):
            if is_bundled:
                self.quality_status_var.set("📦")
                self.quality_status_label.configure(text_color="blue")
                self.model_action_btn.configure(text="📦", command=lambda: None, state="disabled")
            else:
                self.quality_status_var.set("✅")
                self.quality_status_label.configure(text_color="green")
                self.model_action_btn.configure(text="🗑️", command=self._delete_current_model, state="normal")
        else:
            self.quality_status_var.set(f"⬇️ {size}")
            self.quality_status_label.configure(text_color="orange")
            self.model_action_btn.configure(text="⬇️", command=self._download_model, state="normal")
    
    def _delete_current_model(self):
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        
        if messagebox.askyesno(t("models.delete_confirm_title"), 
                              t("models.delete_confirm", quality=quality)):
            self._delete_model(model_name)
            self._update_model_status()
            self.status_var.set(t("status.deleted_model", quality=quality))
    
    def _download_model(self):
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        model_size = self.quality_sizes.get(quality, "")
        
        if self._is_model_downloaded(model_name):
            self.status_var.set(t("status.model_downloaded", quality=quality))
            self._update_model_status()
            return
        
        self._downloading = True
        
        def animate_status():
            import time
            base = t("download.downloading")
            frames = [base, base + ".", base + "..", base + "..."]
            i = 0
            while self._downloading:
                self.after(0, lambda f=frames[i % 4]: self.status_var.set(f"{f} {quality} ({model_size})"))
                i += 1
                time.sleep(0.4)
        
        def download():
            try:
                anim_thread = threading.Thread(target=animate_status, daemon=True)
                anim_thread.start()
                
                self.after(0, lambda: self.status_var.set(t("status.downloading_init", quality=quality)))
                
                from fastembed import TextEmbedding
                
                self.after(0, lambda: self.status_var.set(t("status.downloading", quality=quality, size=model_size)))
                
                cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")
                model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
                
                self.after(0, lambda: self.status_var.set(t("status.verifying", quality=quality)))
                
                list(model.embed(["test"]))
                
                self._downloading = False
                
                self.after(0, self._update_model_status)
                self.after(0, lambda: self.status_var.set(t("status.download_ok", quality=quality)))
                
            except Exception as e:
                self._downloading = False
                error_msg = str(e)
                print(f"Download error: {error_msg}")
                self.after(0, lambda: self.status_var.set(t("status.download_fail", msg=error_msg[:50])))
                self.after(0, lambda: messagebox.showerror(
                    t("models.download_error_title"), 
                    t("models.download_error", quality=quality, error=error_msg)))
        
        thread = threading.Thread(target=download, daemon=True)
        thread.start()
    
    def _get_download_progress(self, model_name):
        total_size = 0
        model_short = model_name.split("/")[-1]
        
        for cache_dir in self._get_fastembed_cache_locations():
            if not os.path.exists(cache_dir):
                continue
            
            for folder in os.listdir(cache_dir):
                if model_short in folder:
                    folder_path = os.path.join(cache_dir, folder)
                    if os.path.isdir(folder_path):
                        for dirpath, dirnames, filenames in os.walk(folder_path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                try:
                                    total_size += os.path.getsize(fp)
                                except:
                                    pass
        
        return total_size / (1024 * 1024)
    
    def _get_model_cache_size(self, model_name):
        total_size = 0
        model_short = model_name.split("/")[-1]
        
        for cache_dir in self._get_fastembed_cache_locations():
            if not os.path.exists(cache_dir):
                continue
            
            for folder in os.listdir(cache_dir):
                if model_short in folder:
                    folder_path = os.path.join(cache_dir, folder)
                    if os.path.isdir(folder_path):
                        for dirpath, dirnames, filenames in os.walk(folder_path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                try:
                                    total_size += os.path.getsize(fp)
                                except:
                                    pass
        
        return total_size / (1024 * 1024)
    
    def _delete_model(self, model_name):
        import shutil
        deleted = False

        model_short = model_name.split("/")[-1]

        for cache_dir in self._get_fastembed_cache_locations():
            if not os.path.exists(cache_dir):
                continue

            try:
                for folder in os.listdir(cache_dir):
                    if model_short in folder or model_short.replace("-", "_") in folder:
                        folder_path = os.path.join(cache_dir, folder)
                        try:
                            shutil.rmtree(folder_path, ignore_errors=False)
                            deleted = True
                        except PermissionError:
                            shutil.rmtree(folder_path, ignore_errors=True)
                            deleted = True
            except (PermissionError, OSError):
                continue

        return deleted
    
    def _manage_models(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("models.title"))
        dialog.geometry("480x420")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(True, True)
        dialog.minsize(400, 300)
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 480) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        ctk.CTkLabel(dialog, text=t("models.header"), font=ui_font(14, bold=True)).pack(pady=(15, 5))
        
        # Total size summary at top
        total_size = sum(
            self._get_model_cache_size(m[1]) for m in self.ALL_MODELS
            if not self._is_bundled_model(m[1])
        )
        ctk.CTkLabel(dialog, text=t("models.downloaded_size", size=f"{total_size:.0f}"), 
                    font=ui_font(10), text_color="gray").pack(pady=(0, 8))
        
        # Scrollable frame for all models
        scroll_frame = ctk.CTkScrollableFrame(dialog, corner_radius=6, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Group models by section
        sections = [
            ("models.section_en",    "en"),
            ("models.section_zh",    "zh"),
            ("models.section_multi", "multi"),
        ]
        
        for section_key, group in sections:
            group_models = [m for m in self.ALL_MODELS if m[4] == group]
            if not group_models:
                continue
            
            # Section header
            section_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            section_frame.pack(fill="x", pady=(10, 4), padx=4)
            
            ctk.CTkLabel(section_frame, text=t(section_key), 
                        font=ui_font(12, bold=True), anchor="w").pack(side="left")
            
            # Separator line
            sep = ctk.CTkFrame(scroll_frame, height=1, fg_color=("gray70", "gray40"))
            sep.pack(fill="x", padx=4, pady=(0, 6))
            
            # Model rows
            for i18n_key, model_name, size_str, ram, _grp in group_models:
                is_bundled = self._is_bundled_model(model_name)
                is_downloaded = self._is_model_downloaded(model_name)
                
                row = ctk.CTkFrame(scroll_frame, corner_radius=6, 
                                  fg_color=("gray92", "gray22"))
                row.pack(fill="x", pady=2, padx=4)
                row.grid_columnconfigure(1, weight=1)
                
                # Status icon
                if is_bundled:
                    icon = "📦"
                elif is_downloaded:
                    icon = "✅"
                else:
                    icon = "⬜"
                
                ctk.CTkLabel(row, text=icon, font=ui_font(12), width=28).grid(
                    row=0, column=0, padx=(8, 4), pady=8)
                
                # Model info (name + technical details)
                info_frame = ctk.CTkFrame(row, fg_color="transparent")
                info_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=8)
                
                display_label = t(i18n_key)
                ctk.CTkLabel(info_frame, text=display_label, font=ui_font(11, bold=True),
                            anchor="w").pack(side="top", anchor="w")
                
                # Subtitle: model short name + size
                model_short = model_name.split("/")[-1]
                if is_bundled:
                    subtitle = f"{model_short} · {t('models.builtin')}"
                elif is_downloaded:
                    actual_mb = self._get_model_cache_size(model_name)
                    subtitle = f"{model_short} · {actual_mb:.0f} MB"
                else:
                    subtitle = f"{model_short} · {size_str}"
                
                ctk.CTkLabel(info_frame, text=subtitle, font=ui_font(9),
                            text_color="gray", anchor="w").pack(side="top", anchor="w")
                
                # Action button
                if is_bundled:
                    # No action for bundled
                    pass
                elif is_downloaded:
                    def make_delete_cb(mn=model_name, dn=display_label, r=row):
                        def cb():
                            if messagebox.askyesno(t("models.delete_confirm_title"),
                                                  t("models.delete_confirm", quality=dn)):
                                self._delete_model(mn)
                                r.destroy()
                                self._update_model_status()
                                self.status_var.set(t("status.deleted_model", quality=dn))
                        return cb
                    
                    ctk.CTkButton(row, text=t("models.delete"), width=60, height=26, 
                                 corner_radius=4, fg_color="#dc3545", hover_color="#c82333",
                                 font=ui_font(10),
                                 command=make_delete_cb()).grid(
                        row=0, column=2, padx=(4, 10), pady=8)
                else:
                    def make_download_cb(mn=model_name, dn=display_label):
                        def cb():
                            # Set dropdown to this model and trigger download
                            for lbl, mname in self.quality_options.items():
                                if mname == mn:
                                    self.quality_var.set(lbl)
                                    break
                            dialog.destroy()
                            self._download_model()
                        return cb
                    
                    ctk.CTkButton(row, text="⬇️ " + size_str, width=90, height=26,
                                 corner_radius=4, fg_color=("gray70", "gray35"),
                                 hover_color=("gray60", "gray45"),
                                 font=ui_font(10),
                                 command=make_download_cb()).grid(
                        row=0, column=2, padx=(4, 10), pady=8)
    
    def _load_index(self):
        pdf_dir = self.dir_entry.get()
        if not pdf_dir or not Path(pdf_dir).exists():
            messagebox.showerror(t("dialog.error"), t("dialog.invalid_dir"))
            return
        
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        
        if not self._is_model_downloaded(model_name):
            messagebox.showwarning(t("dialog.model_required"), 
                t("dialog.download_model_first", quality=quality))
            return
        
        self._show_index_mode_dialog(pdf_dir, model_name, quality)
    
    def _show_index_mode_dialog(self, pdf_dir, model_name, quality):
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("index_dialog.title"))
        dialog.geometry("420x280")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(dialog, text=t("index_dialog.question"), 
                     font=ui_font(14, bold=True)).pack(pady=(20, 15))
        
        # Fast mode
        fast_frame = ctk.CTkFrame(dialog, corner_radius=8)
        fast_frame.pack(padx=20, pady=5, fill="x")
        
        def select_fast():
            dialog.destroy()
            self._do_load_index(pdf_dir, model_name, quality, precompute=False)
        
        ctk.CTkButton(fast_frame, text=t("index_dialog.fast"), command=select_fast,
                      width=120, height=32, corner_radius=6, 
                      font=ui_font(11, bold=True)).pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(fast_frame, text=t("index_dialog.fast_desc"),
                     font=ui_font(10), text_color="gray", justify="left").pack(side="left", padx=5)
        
        # Deep mode
        deep_frame = ctk.CTkFrame(dialog, corner_radius=8)
        deep_frame.pack(padx=20, pady=5, fill="x")
        
        def select_deep():
            dialog.destroy()
            self._do_load_index(pdf_dir, model_name, quality, precompute=True)
        
        ctk.CTkButton(deep_frame, text=t("index_dialog.deep"), command=select_deep,
                      width=120, height=32, corner_radius=6,
                      font=ui_font(11, bold=True)).pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(deep_frame, text=t("index_dialog.deep_desc"),
                     font=ui_font(10), text_color="gray", justify="left").pack(side="left", padx=5)
        
        # Cancel
        ctk.CTkButton(dialog, text=t("index_dialog.cancel"), command=dialog.destroy,
                      width=80, height=28, corner_radius=6, fg_color="gray").pack(pady=15)
    
    def _do_load_index(self, pdf_dir, model_name, quality, precompute=False):
        def update_progress(current, total):
            percent = int(current / total * 100)
            self.after(0, lambda: self.status_var.set(
                t("status.deep_indexing", current=current, total=total, percent=percent)
            ))
        
        def load():
            try:
                self.after(0, lambda: self.status_var.set(t("status.step1_model")))
                self.locator = HybridLocator(pdf_dir, model_name=model_name)
                
                if precompute:
                    self.after(0, lambda: self.status_var.set(t("status.step2_deep")))
                    self.locator.build_index()
                    page_count = len(self.locator.documents)
                    self.after(0, lambda: self.status_var.set(
                        t("status.step3_deep", current=0, total=page_count)
                    ))
                    self.locator.precompute_embeddings(progress_callback=update_progress)
                else:
                    self.after(0, lambda: self.status_var.set(t("status.step2_indexing")))
                    self.locator.build_index()
                
                self.pdf_dir = pdf_dir
                page_count = len(self.locator.documents)
                mode = t("status.mode_deep") if precompute else t("status.mode_fast")
                
                self.after(0, lambda: self.status_var.set(
                    t("status.ready_indexed", count=page_count, mode=mode)
                ))
                    
            except Exception as e:
                self.status_var.set(t("status.error", msg=str(e)))
                messagebox.showerror(t("dialog.error"), str(e))
        
        self.status_var.set(t("status.loading"))
        thread = threading.Thread(target=load)
        thread.start()
    
    def _clear_results(self):
        for card in self.result_cards:
            card.destroy()
        self.result_cards = []
        self.selected_card = None
    
    def _on_card_click(self, card):
        if self.selected_card:
            self.selected_card.set_selected(False)
        card.set_selected(True)
        self.selected_card = card
        self.snippet_text.delete("1.0", tk.END)
        self.snippet_text.insert("1.0", card.snippet)
    
    def _on_card_double_click(self, card):
        self._on_card_click(card)
        self._open_selected()
    
    def _search(self):
        if not self.locator:
            messagebox.showwarning(t("dialog.warning"), t("dialog.load_index_first"))
            return
        
        query = self.query_entry.get().strip()
        if not query:
            return
        
        try:
            top_k = int(self.topk_var.get())
            bm25_weight = self.search_mode_var.get()
        except ValueError:
            top_k = 5
            bm25_weight = 0.3
        
        self._searching = True
        self._animate_search()
        
        def do_search():
            try:
                result = self.locator.search(query, top_k=top_k, bm25_weight=bm25_weight)
                
                if isinstance(result, tuple):
                    results, is_cross_lingual = result
                else:
                    results = result
                    is_cross_lingual = False
                
                self._searching = False
                self.after(0, lambda: self._display_results(results, is_cross_lingual))
                
            except Exception as e:
                self._searching = False
                self.after(0, lambda: self.status_var.set(t("status.search_error", msg=str(e))))
        
        thread = threading.Thread(target=do_search)
        thread.start()
    
    def _animate_search(self):
        if not self._searching:
            return
        
        base = t("search.searching")
        frames = [base, base + ".", base + "..", base + "..."]
        if not hasattr(self, '_search_frame'):
            self._search_frame = 0
        
        self.status_var.set(frames[self._search_frame % len(frames)])
        self._search_frame += 1
        
        self.after(300, self._animate_search)
    
    def _display_results(self, results, is_cross_lingual):
        self.current_results = results
        self._clear_results()
        self.snippet_text.delete("1.0", tk.END)
        self.placeholder_label.grid_forget()
        
        for i, r in enumerate(self.current_results, 1):
            card = ResultCard(
                self.results_scroll,
                rank=i,
                pdf_name=r['pdf_name'],
                page_num=r['page_num'],
                score=r['score'],
                snippet=r['snippet'],
                on_click=self._on_card_click,
                on_double_click=self._on_card_double_click
            )
            card.grid(row=i-1, column=0, padx=5, pady=5, sticky="ew")
            self.result_cards.append(card)
        
        if not self.current_results:
            self.placeholder_label.configure(text=t("results.no_results"))
            self.placeholder_label.grid(row=0, column=0, pady=50)
        
        if is_cross_lingual:
            self.status_var.set(t("status.cross_lingual", count=len(self.current_results)))
        else:
            self.status_var.set(t("status.found_results", count=len(self.current_results)))
    
    def _open_selected(self):
        if not self.selected_card:
            messagebox.showinfo(t("dialog.info"), t("dialog.select_result"))
            return
        
        pdf_path = Path(self.pdf_dir) / self.selected_card.pdf_name
        page_num = self.selected_card.page_num
        
        if not pdf_path.exists():
            messagebox.showerror(t("dialog.error"), t("dialog.pdf_not_found", path=str(pdf_path)))
            return
        
        self.status_var.set(t("status.opening", name=self.selected_card.pdf_name, page=page_num))
        success = open_pdf_at_page(str(pdf_path), page_num)
        
        if success:
            self.status_var.set(t("status.opened", name=self.selected_card.pdf_name, page=page_num))
        else:
            self.status_var.set(t("status.opened_no_nav", name=self.selected_card.pdf_name))


def main():
    global splash
    splash.set_status(t("splash.ready"), 100)
    splash.close()
    app = LocatorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()