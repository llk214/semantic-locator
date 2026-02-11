"""
Modern GUI for the Semantic Page Locator
Uses customtkinter for iOS-style rounded corners
Supports Chinese / English language switching
"""

import sys
import os
import io
import ctypes

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

# Import i18n
from i18n import t, get_lang, set_lang

# Import split modules
from fonts import ui_font, mono_font, emoji_font
from splash import SplashScreen

# ===== Show splash immediately (always in English) =====
_user_lang = get_lang()
set_lang("en")
splash = SplashScreen()
splash.set_status(t("splash.loading_libs"), 10)

# Now import heavy libraries
import customtkinter as ctk
splash.set_status(t("splash.loading_ui"), 25)

from tkinter import filedialog, messagebox
from pathlib import Path
import threading
splash.set_status(t("splash.loading_engine"), 40)

from locator import HybridLocator
splash.set_status(t("splash.starting"), 95)

from pdf_viewer import open_pdf_at_page
from widgets import ResultCard
from dialogs import show_rounded_popup, show_manage_models_dialog, show_index_mode_dialog
import model_manager

# Restore user's saved language for the main UI
set_lang(_user_lang)

# Set appearance
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def _app_path(filename: str) -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    direct = os.path.join(base, filename)
    internal = os.path.join(base, "_internal", filename)
    return internal if os.path.exists(internal) else direct


def _set_windows_app_id():
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Locus.App")
        except Exception:
            pass


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
        ("quality.multilingual", "intfloat/multilingual-e5-large",  "1.1GB",    "8GB RAM",   "multi"),
    ]
    
    @staticmethod
    def _get_models_for_lang(lang: str) -> list[tuple]:
        """Return models relevant to the given UI language."""
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
        
        _set_windows_app_id()
        self.title(t("app.title"))
        try:
            self.iconbitmap(_app_path("locus.ico"))
        except Exception:
            pass
        self.geometry("900x650")
        self.minsize(750, 500)
        
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
        self._last_index_hash = None
        self._last_index_model = None
        self._index_cancel = None
        self._indexing = False
        self.fusion_method = "rrf"
        
        # Track translatable widgets for language switching
        self._i18n_widgets = []
        
        self._create_widgets()

    # ---- i18n helpers ----
    
    def _register_i18n(self, widget, method, key, font_size=None, font_bold=False, **kwargs):
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
        
        if hasattr(self, 'lang_btn'):
            self.lang_btn.configure(text=t("lang.switch"), font=ui_font(10))
        
        if hasattr(self, 'quality_menu'):
            self._rebuild_quality_menu()
            current_quality = self.quality_var.get()

        if hasattr(self, 'ocr_quality_var'):
            current = self.ocr_quality_var.get()
            new_label = t("ocr.off")
            for key in self.ocr_quality_options.keys():
                if current == t(key):
                    new_label = t(key)
                    break
            self.ocr_quality_var.set(new_label)
            self._update_ocr_button_style()
        
        if hasattr(self, 'status_label'):
            self.status_label.configure(font=ui_font(11))
        
        current_status = self.status_var.get()
        if current_status in ("Select a directory with PDFs", "请选择包含PDF的文件夹"):
            self.status_var.set(t("status.select_dir"))
    
    def _rebuild_quality_menu(self):
        """Rebuild quality options for current language."""
        current_model = None
        for label, model_name in getattr(self, 'quality_options', {}).items():
            if label == self.quality_var.get():
                current_model = model_name
                break
        
        self._build_quality_dicts()
        
        new_display = list(self.quality_options.keys())[0]
        if current_model:
            for label, model_name in self.quality_options.items():
                if model_name == current_model:
                    new_display = label
                    break
        
        self.quality_var.set(new_display)
        self._update_model_status()
    
    def _show_overlay(self, text, callback, duration_ms=150):
        """Show a brief overlay message, run callback while covered, then remove overlay."""
        overlay = ctk.CTkFrame(self, fg_color=("gray85", "gray17"), corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        ctk.CTkLabel(overlay, text=text, font=ui_font(14),
                     text_color=("gray40", "gray70")).place(relx=0.5, rely=0.5, anchor="center")
        
        overlay.lift()
        self.update_idletasks()
        
        def do_work():
            callback()
            self.update_idletasks()
            self.after(duration_ms, lambda: overlay.destroy())
        
        self.after(50, do_work)
    
    def _toggle_language(self):
        current = get_lang()
        new_lang = "en" if current == "zh" else "zh"
        # Show overlay in the TARGET language
        label = "Switching language..." if new_lang == "en" else "正在切换语言..."
        
        def do_switch():
            set_lang(new_lang)
            self._refresh_i18n()
        
        self._show_overlay(label, do_switch)
    
    # ---- Widget creation ----
    
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
        self.load_btn = load_btn
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
        self.options_frame = options_frame
        
        # Right side FIRST - Search Mode Slider
        right_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        right_options.pack(side="right", padx=12, pady=8)
        self.right_options = right_options
        
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
        left_options.pack(side="left", padx=12, pady=8, fill="x", expand=True)
        self.left_options = left_options
        
        results_label = ctk.CTkLabel(left_options, text=t("options.results"), font=ui_font(11))
        results_label.pack(side="left", padx=(0, 4))
        self._register_i18n(results_label, "text", "options.results", font_size=11)
        
        self.topk_var = tk.StringVar(value="5")
        self.topk_btn = ctk.CTkButton(
            left_options, textvariable=self.topk_var,
            width=36, height=26, corner_radius=6,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            font=ui_font(11),
            command=self._show_topk_popup
        )
        self.topk_btn.pack(side="left", padx=(0, 16))

        # OCR mode selector (Off/Fast/Balanced/Best)
        ocr_label = ctk.CTkLabel(left_options, text=t("options.ocr_mode"), font=ui_font(11))
        ocr_label.pack(side="left", padx=(0, 4))
        self._register_i18n(ocr_label, "text", "options.ocr_mode", font_size=11)

        self.ocr_quality_options = {
            "ocr.off": None,
            "ocr.fast": 150,
            "ocr.balanced": 200,
            "ocr.best": 260,
        }
        self.ocr_quality_var = tk.StringVar(value=t("ocr.off"))
        self.ocr_quality_btn = ctk.CTkButton(
            left_options, textvariable=self.ocr_quality_var,
            width=70, height=26, corner_radius=6,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            font=ui_font(11),
            command=self._show_ocr_quality_popup
        )
        self.ocr_quality_btn.pack(side="left", padx=(0, 8))
        self._update_ocr_button_style()
        self.options_frame.bind("<Configure>", self._update_options_layout)
        
        quality_label = ctk.CTkLabel(left_options, text=t("options.quality"), font=ui_font(11))
        quality_label.pack(side="left", padx=(0, 4))
        self._register_i18n(quality_label, "text", "options.quality", font_size=11)
        
        # Bundled model name
        self.bundled_model = model_manager.BUNDLED_MODEL
        
        # Initialize quality options for current language
        self._build_quality_dicts()
        
        self.quality_var = tk.StringVar(value=list(self.quality_options.keys())[0])
        self.quality_btn = ctk.CTkButton(
            left_options, textvariable=self.quality_var,
            width=120, height=26, corner_radius=6,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            font=ui_font(11),
            command=self._show_quality_popup
        )
        self.quality_btn.pack(side="left", padx=(0, 8))
        self.quality_menu = self.quality_btn
        
        # Manage models button
        ctk.CTkButton(
            left_options, text="⚙️", command=self._manage_models,
            width=28, height=24, corner_radius=4,
            fg_color="transparent", hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray60"), anchor="center",
            font=emoji_font(12)
        ).pack(side="left", padx=(2, 0))

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
    
    # ---- Rounded popup dropdown ----
    
    def _show_topk_popup(self):
        show_rounded_popup(
            self, self.topk_btn,
            ["3", "5", "10", "15", "20"],
            self.topk_var
        )

    def _show_quality_popup(self):
        show_rounded_popup(
            self, self.quality_btn,
            list(self.quality_options.keys()),
            self.quality_var,
            on_select=self._on_quality_change
        )

    def _show_ocr_quality_popup(self):
        show_rounded_popup(
            self, self.ocr_quality_btn,
            [t(k) for k in self.ocr_quality_options.keys()],
            self.ocr_quality_var,
            on_select=lambda _v: self._update_ocr_button_style()
        )

    def _update_ocr_button_style(self):
        if self.ocr_quality_var.get() == t("ocr.off"):
            self.ocr_quality_btn.configure(
                fg_color=("gray82", "gray18"),
                text_color=("gray50", "gray55")
            )
        else:
            self.ocr_quality_btn.configure(
                fg_color=("gray75", "gray28"),
                text_color=("gray10", "gray90")
            )

    def _get_ocr_dpi(self) -> int:
        selected = self.ocr_quality_var.get()
        for key, dpi in self.ocr_quality_options.items():
            if selected == t(key):
                return dpi or 200
        return 200

    def _update_options_layout(self, _event=None):
        width = self.options_frame.winfo_width()
        if width <= 620:
            self.topk_btn.configure(width=36)
        elif width <= 720:
            self.topk_btn.configure(width=44)
        else:
            self.topk_btn.configure(width=48)
    
    # ---- Directory / quality actions ----
    
    def _compute_pdf_hash(self, pdf_dir: Path) -> str | None:
        try:
            import hashlib
            h = hashlib.sha1()
            pdf_files = sorted(pdf_dir.glob("*.pdf"))
            for p in pdf_files:
                try:
                    stat = p.stat()
                    h.update(p.name.encode("utf-8"))
                    h.update(str(stat.st_size).encode("utf-8"))
                    h.update(str(stat.st_mtime).encode("utf-8"))
                except OSError:
                    continue
            return h.hexdigest()
        except Exception:
            return None

    def _update_index_button_label(self):
        if not hasattr(self, "load_btn"):
            return
        if self._indexing:
            self.load_btn.configure(
                text=t("dir.cancel"),
                command=self._cancel_index,
                fg_color="#dc3545",
                hover_color="#c82333",
                text_color="white"
            )
            return
        pdf_dir = self.dir_entry.get()
        if not pdf_dir or not Path(pdf_dir).exists():
            self.load_btn.configure(
                text=t("dir.load_index"),
                command=self._load_index,
                fg_color="#28a745",
                hover_color="#218838",
                text_color="white"
            )
            return
        current_quality = self.quality_var.get()
        model_name = self.quality_options.get(current_quality)
        current_hash = self._compute_pdf_hash(Path(pdf_dir))
        needs_reindex = False
        if self._last_index_hash and current_hash and self._last_index_hash != current_hash:
            needs_reindex = True
        if self._last_index_model and model_name and self._last_index_model != model_name:
            needs_reindex = True
        label_key = "dir.reindex" if needs_reindex else "dir.load_index"
        self.load_btn.configure(
            text=t(label_key),
            command=self._load_index,
            fg_color="#28a745",
            hover_color="#218838",
            text_color="white"
        )

    def _browse_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self._update_index_button_label()
    
    def _on_quality_change(self, choice):
        self._update_model_status()
        
        if self.locator:
            self.status_var.set(t("status.quality_changed"))
        self._update_index_button_label()
    
    # ---- Model management (delegates to model_manager module) ----
    
    def _is_bundled_model(self, model_name):
        return model_manager.is_bundled_model(model_name)
    
    def _is_model_downloaded(self, model_name):
        return model_manager.is_model_downloaded(model_name)
    
    def _get_model_cache_size(self, model_name):
        return model_manager.get_model_cache_size(model_name)
    
    def _delete_model(self, model_name):
        return model_manager.delete_model(model_name)
    
    def _update_model_status(self):
        # Simplified UI: no status widgets to update
        return

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
    
    def _manage_models(self):
        show_manage_models_dialog(self)

    def _clear_index_cache(self):
        pdf_dir = self.dir_entry.get()
        if not pdf_dir or not Path(pdf_dir).exists():
            messagebox.showerror(t("dialog.error"), t("dialog.invalid_dir"))
            return
        if not messagebox.askyesno(t("dialog.info"), t("cache.clear_index_confirm")):
            return
        try:
            base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else str(Path.home())
            cache_dir = Path(base) / "Locus" / "index_cache"
            if cache_dir.exists():
                for p in cache_dir.glob("*.pkl"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
                for p in cache_dir.glob("*.meta.json"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
            self.status_var.set(t("cache.cleared"))
        except Exception:
            pass

    def _clear_ocr_cache(self):
        if not messagebox.askyesno(t("dialog.info"), t("cache.clear_ocr_confirm")):
            return
        try:
            base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else str(Path.home())
            ocr_dir = Path(base) / "Locus" / "ocr_cache"
            if ocr_dir.exists():
                for p in ocr_dir.glob("*.txt"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
            self.status_var.set(t("cache.cleared"))
        except Exception:
            pass
    
    # ---- Index loading ----
    
    def _cancel_index(self):
        if self._index_cancel:
            self._index_cancel.set()
            self.status_var.set(t("status.canceling"))
            self._update_index_button_label()

    def _load_index(self):
        pdf_dir = self.dir_entry.get()
        if not pdf_dir or not Path(pdf_dir).exists():
            messagebox.showerror(t("dialog.error"), t("dialog.invalid_dir"))
            return
        
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        
        ok, _err = model_manager.verify_model_available(model_name)
        if not ok:
            should_open = messagebox.askyesno(
                t("dialog.download_model_first_title"),
                t("dialog.download_model_first", quality=quality)
            )
            if should_open:
                self._manage_models()
            return
        
        self._show_index_mode_dialog(pdf_dir, model_name, quality)
    
    def _show_index_mode_dialog(self, pdf_dir, model_name, quality):
        show_index_mode_dialog(self, pdf_dir, model_name, quality)
    
    def _do_load_index(self, pdf_dir, model_name, quality, precompute=False):
        self._index_cancel = threading.Event()
        self._indexing = True
        self._update_index_button_label()
        def update_progress(current, total):
            percent = int(current / total * 100)
            self.after(0, lambda: self.status_var.set(
                t("status.deep_indexing", current=current, total=total, percent=percent)
            ))

        def update_ocr_progress(pdf_name, page_num, total_pages):
            self.after(0, lambda: self.status_var.set(
                t("status.ocr_progress", name=pdf_name, page=page_num, total=total_pages)
            ))
        
        def load():
            try:
                self.after(0, lambda: self.status_var.set(t("status.step1_model")))
                self.locator = HybridLocator(pdf_dir, model_name=model_name)
                
                if precompute:
                    self.after(0, lambda: self.status_var.set(t("status.step2_deep")))
                    ocr_mode = "off" if self.ocr_quality_var.get() == t("ocr.off") else "deep"
                    ocr_dpi = self._get_ocr_dpi()
                    self.locator.build_index(ocr_mode=ocr_mode, ocr_progress_callback=update_ocr_progress,
                                             ocr_dpi=ocr_dpi, cancel_event=self._index_cancel)
                    page_count = len(self.locator.documents)
                    self.after(0, lambda: self.status_var.set(
                        t("status.step3_deep", current=0, total=page_count)
                    ))
                    self.locator.precompute_embeddings(progress_callback=update_progress,
                                                    cancel_event=self._index_cancel)
                else:
                    self.after(0, lambda: self.status_var.set(t("status.step2_indexing")))
                    ocr_mode = "off" if self.ocr_quality_var.get() == t("ocr.off") else "fast"
                    ocr_dpi = self._get_ocr_dpi()
                    self.locator.build_index(ocr_mode=ocr_mode, ocr_progress_callback=update_ocr_progress,
                                             ocr_dpi=ocr_dpi, cancel_event=self._index_cancel)
                
                self.pdf_dir = pdf_dir
                page_count = len(self.locator.documents)
                mode = t("status.mode_deep") if precompute else t("status.mode_fast")
                
                self.after(0, lambda: self.status_var.set(
                    t("status.ready_indexed", count=page_count, mode=mode)
                ))
                self._indexing = False
                current_hash = self._compute_pdf_hash(Path(pdf_dir))
                self._last_index_hash = current_hash
                self._last_index_model = model_name
                self.after(0, self._update_index_button_label)
                    
            except Exception as e:
                err = str(e)
                if "Indexing canceled" in err:
                    self._indexing = False
                    self.after(0, lambda: self.status_var.set(t("status.canceled")))
                    self.after(0, self._update_index_button_label)
                    return
                self._indexing = False
                self.after(0, lambda: self.status_var.set(t("status.error", msg=err)))
                self.after(0, lambda: messagebox.showerror(t("dialog.error"), err))
        
        self.status_var.set(t("status.loading"))
        thread = threading.Thread(target=load)
        thread.start()
    
    # ---- Search and results ----
    
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
                result = self.locator.search(query, top_k=top_k, bm25_weight=bm25_weight,
                                           fusion_method=self.fusion_method)
                
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
                chunk_id=r.get('chunk_id', 0),
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
