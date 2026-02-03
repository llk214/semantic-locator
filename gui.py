"""
Modern GUI for the Semantic Page Locator
Uses customtkinter for iOS-style rounded corners
"""

import sys
import io

# Fix for PyInstaller + sentence-transformers (isatty error)
if getattr(sys, 'frozen', False):
    if sys.stdout is None or not hasattr(sys.stdout, 'isatty'):
        sys.stdout = io.StringIO()
    if sys.stderr is None or not hasattr(sys.stderr, 'isatty'):
        sys.stderr = io.StringIO()

import tkinter as tk

# ===== Splash Screen (shows immediately while loading) =====
class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # No window decorations
        
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
        logo_label = tk.Label(frame, text="📚", font=("Segoe UI Emoji", 48), 
                              bg="#1a1a2e", fg="white")
        logo_label.pack(pady=(10, 5))
        
        # App name
        title_label = tk.Label(frame, text="Locus", 
                               font=("Segoe UI", 22, "bold"),
                               bg="#1a1a2e", fg="#ffffff")
        title_label.pack(pady=(0, 5))
        
        # Tagline
        tagline_label = tk.Label(frame, text="Smart PDF Search for Students & Researchers", 
                                  font=("Segoe UI", 10),
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
        self.status_var = tk.StringVar(value="Initializing...")
        status_label = tk.Label(frame, textvariable=self.status_var,
                                font=("Segoe UI", 9),
                                bg="#1a1a2e", fg="#666677")
        status_label.pack(pady=(15, 0))
        
        # Version (with extra padding at bottom)
        version_label = tk.Label(frame, text="v0.1.1", 
                                 font=("Segoe UI", 8),
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
splash.set_status("Loading libraries...", 10)

# Now import heavy libraries
import customtkinter as ctk
splash.set_status("Loading UI components...", 25)

from tkinter import filedialog, messagebox
from tkinter import ttk
from pathlib import Path
import threading
import subprocess
import platform
import os
splash.set_status("Loading search engine...", 40)

from locator import HybridLocator
splash.set_status("Starting application...", 95)

# Set appearance
ctk.set_appearance_mode("system")  # "light", "dark", or "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


def open_pdf_at_page(pdf_path: str, page_num: int):
    """Open PDF at specific page using system default viewer."""
    system = platform.system()
    pdf_path = os.path.abspath(pdf_path)
    
    if system == "Windows":
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
        rank_label = ctk.CTkLabel(self, text=f"#{rank}", font=("Segoe UI", 11, "bold"),
                                   width=30, fg_color=("gray80", "gray30"), corner_radius=5)
        rank_label.grid(row=0, column=0, rowspan=2, padx=(8, 8), pady=8)
        
        # PDF name and page
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(8, 2))
        header_frame.grid_columnconfigure(0, weight=1)
        
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info_frame, text=pdf_name, font=("Segoe UI", 11, "bold"),
                     anchor="w").pack(side="left")
        
        ctk.CTkLabel(info_frame, text=f"  📄 Page {page_num}", font=("Segoe UI", 10),
                     text_color="gray", anchor="w").pack(side="left")
        
        # Score badge
        score_color = "#28a745" if score > 0.7 else "#ffc107" if score > 0.4 else "#6c757d"
        ctk.CTkLabel(header_frame, text=f"{score:.2f}", font=("Segoe UI", 9),
                     fg_color=score_color, corner_radius=4, text_color="white",
                     padx=6, pady=1).pack(side="right", padx=(0, 5))
        
        # Snippet preview - no fixed wraplength, uses grid sticky for responsive width
        snippet_short = snippet[:120] + "..." if len(snippet) > 120 else snippet
        snippet_short = ' '.join(snippet_short.split())  # Clean whitespace
        self.snippet_label = ctk.CTkLabel(self, text=snippet_short, font=("Segoe UI", 10),
                                           anchor="w", justify="left", text_color="gray")
        self.snippet_label.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))
        
        # Bind click events to all children
        self._bind_click_recursive(self)
    
    def _bind_click_recursive(self, widget):
        """Bind click events to widget and all children."""
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
    def __init__(self):
        super().__init__()
        
        self.title("📚 Locus - PDF Search")
        self.geometry("900x650")
        self.minsize(650, 500)
        
        # Auto-scale based on screen resolution
        screen_width = self.winfo_screenwidth()
        if screen_width >= 3840:      # 4K
            ctk.set_widget_scaling(0.85)
        elif screen_width >= 2560:    # 1440p
            ctk.set_widget_scaling(0.92)
        # else: keep default 1.0 for 1080p and below
        
        self.locator = None
        self.pdf_dir = None
        self.current_results = []
        self.result_cards = []
        self.selected_card = None
        self._searching = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        
        # ===== Top Frame - Directory Selection =====
        top_frame = ctk.CTkFrame(self, corner_radius=8)
        top_frame.grid(row=0, column=0, padx=12, pady=(12, 2), sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(top_frame, text="PDF Directory:", font=("Segoe UI", 12)).grid(
            row=0, column=0, padx=(12, 8), pady=12)
        
        self.dir_entry = ctk.CTkEntry(top_frame, placeholder_text="Select a folder with PDFs...", 
                                       height=30, corner_radius=6)
        self.dir_entry.grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        
        ctk.CTkButton(top_frame, text="Browse", command=self._browse_dir,
                      width=80, height=30, corner_radius=6).grid(
            row=0, column=2, padx=4, pady=12)
        
        ctk.CTkButton(top_frame, text="Load Index", command=self._load_index,
                      width=100, height=30, corner_radius=6,
                      fg_color="#28a745", hover_color="#218838").grid(
            row=0, column=3, padx=(4, 12), pady=12)
        
        # ===== Status Label =====
        self.status_var = tk.StringVar(value="Select a directory with PDFs")
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_var, 
                                          font=("Segoe UI", 11), text_color="gray")
        self.status_label.grid(row=1, column=0, padx=12, pady=2)
        
        # ===== Search Frame =====
        search_frame = ctk.CTkFrame(self, corner_radius=8)
        search_frame.grid(row=2, column=0, padx=12, pady=2, sticky="ew")
        search_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(search_frame, text="Search:", font=("Segoe UI", 12)).grid(
            row=0, column=0, padx=(12, 8), pady=12)
        
        self.query_entry = ctk.CTkEntry(search_frame, placeholder_text="Describe what you want to find…",
                                         height=32, corner_radius=6, font=("Segoe UI", 11))
        self.query_entry.grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        self.query_entry.bind('<Return>', lambda e: self._search())
        
        ctk.CTkButton(search_frame, text="🔍 Search", command=self._search,
                      width=100, height=32, corner_radius=6, font=("Segoe UI", 11)).grid(
            row=0, column=2, padx=(4, 12), pady=12)
        
        # ===== Options Frame =====
        options_frame = ctk.CTkFrame(self, corner_radius=8)
        options_frame.grid(row=3, column=0, padx=12, pady=2, sticky="ew")
        
        # Right side FIRST - Search Mode Slider (priority)
        right_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        right_options.pack(side="right", padx=12, pady=8)
        
        ctk.CTkLabel(right_options, text="🧠 Semantic", font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        
        self.search_mode_var = tk.DoubleVar(value=0.3)
        self.search_slider = ctk.CTkSlider(right_options, from_=0, to=1, 
                                            variable=self.search_mode_var,
                                            width=160, height=16)
        self.search_slider.pack(side="left", padx=4)
        
        ctk.CTkLabel(right_options, text="🔤 Literal", font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))
        
        # Left side SECOND - Results count and Quality (shrinks first)
        left_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        left_options.pack(side="left", padx=12, pady=8)
        
        ctk.CTkLabel(left_options, text="Results:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 4))
        
        self.topk_var = tk.StringVar(value="5")
        self.topk_menu = ctk.CTkOptionMenu(left_options, variable=self.topk_var,
                                            values=["3", "5", "10", "15", "20"],
                                            width=60, height=26, corner_radius=6)
        self.topk_menu.pack(side="left", padx=(0, 16))
        
        ctk.CTkLabel(left_options, text="Quality:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 4))
        
        self.quality_options = {
            "⚡ Fast": "sentence-transformers/all-MiniLM-L6-v2",
            "⚖️ Balanced": "BAAI/bge-small-en-v1.5", 
            "🎯 High Accuracy": "BAAI/bge-base-en-v1.5",
            "🚀 Best": "BAAI/bge-large-en-v1.5",
            "🌍 Multilingual": "BAAI/bge-m3"
        }
        
        self.quality_sizes = {
            "⚡ Fast": "80MB",
            "⚖️ Balanced": "130MB", 
            "🎯 High Accuracy": "440MB",
            "🚀 Best": "1.3GB",
            "🌍 Multilingual": "2.2GB"
        }
        
        self.quality_var = tk.StringVar(value="⚡ Fast")
        self.quality_menu = ctk.CTkOptionMenu(left_options, variable=self.quality_var,
                                               values=list(self.quality_options.keys()),
                                               width=145, height=26, corner_radius=6,
                                               command=self._on_quality_change)
        self.quality_menu.pack(side="left", padx=(0, 8))
        
        # Download status label (shows ✅ if downloaded, ⬇️ if needs download)
        self.quality_status_var = tk.StringVar(value="")
        self.quality_status_label = ctk.CTkLabel(left_options, textvariable=self.quality_status_var, 
                                                  font=("Segoe UI", 9))
        self.quality_status_label.pack(side="left", padx=(0, 4))
        
        self.quality_info_var = tk.StringVar(value="4GB RAM")
        ctk.CTkLabel(left_options, textvariable=self.quality_info_var, 
                     font=("Segoe UI", 9), text_color="gray").pack(side="left")
        
        # Download/Delete button (changes based on model status)
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
                                               text="Search results will appear here...",
                                               font=("Segoe UI", 11), text_color="gray")
        self.placeholder_label.grid(row=0, column=0, pady=40)
        
        # ===== Bottom Frame =====
        bottom_frame = ctk.CTkFrame(self, corner_radius=8)
        bottom_frame.grid(row=5, column=0, padx=12, pady=(2, 10), sticky="ew")
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(bottom_frame, text="📄 Open PDF at Page", command=self._open_selected,
                      width=150, height=32, corner_radius=6, font=("Segoe UI", 11)).grid(
            row=0, column=0, padx=12, pady=10)
        
        ctk.CTkLabel(bottom_frame, text="(or double-click a result)", 
                     font=("Segoe UI", 10), text_color="gray").grid(
            row=0, column=1, padx=8, pady=10, sticky="w")
        
        # Snippet preview
        ctk.CTkLabel(bottom_frame, text="Full Snippet:", font=("Segoe UI", 10)).grid(
            row=1, column=0, padx=12, pady=(0, 4), sticky="w")
        
        self.snippet_text = ctk.CTkTextbox(bottom_frame, height=60, corner_radius=6,
                                            font=("Consolas", 10))
        self.snippet_text.grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 10), sticky="ew")
    
    def _browse_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def _on_quality_change(self, choice):
        info_map = {
            "⚡ Fast": "4GB RAM",
            "⚖️ Balanced": "4GB RAM",
            "🎯 High Accuracy": "8GB RAM",
            "🚀 Best": "16GB RAM",
            "🌍 Multilingual": "16GB+ RAM"
        }
        self.quality_info_var.set(info_map.get(choice, ""))
        self._update_model_status()
        
        if self.locator:
            self.status_var.set("Quality changed - click 'Load Index' to apply")
    
    def _is_model_downloaded(self, model_name):
        """Check if model exists in HuggingFace cache."""
        import os
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        if not os.path.exists(cache_dir):
            return False
        
        # Convert model name to cache folder format
        # e.g., "sentence-transformers/all-MiniLM-L6-v2" -> "models--sentence-transformers--all-MiniLM-L6-v2"
        model_folder = "models--" + model_name.replace("/", "--")
        model_path = os.path.join(cache_dir, model_folder)
        return os.path.exists(model_path)
    
    def _update_model_status(self):
        """Update the download status indicator and action button."""
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        size = self.quality_sizes.get(quality, "")
        
        if self._is_model_downloaded(model_name):
            self.quality_status_var.set("✅")
            self.quality_status_label.configure(text_color="green")
            self.model_action_btn.configure(text="🗑️", command=self._delete_current_model)
        else:
            self.quality_status_var.set(f"⬇️ {size}")
            self.quality_status_label.configure(text_color="orange")
            self.model_action_btn.configure(text="⬇️", command=self._download_model)
    
    def _delete_current_model(self):
        """Delete the currently selected model."""
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        
        if messagebox.askyesno("Delete Model", 
                              f"Delete {quality} model?\nYou'll need to re-download it to use this quality level."):
            self._delete_model(model_name)
            self._update_model_status()
            self.status_var.set(f"Deleted {quality} model")
    
    def _download_model(self):
        """Download the currently selected model."""
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        model_size = self.quality_sizes.get(quality, "")
        
        if self._is_model_downloaded(model_name):
            self.status_var.set(f"✅ {quality} model already downloaded")
            return
        
        # Animation flag
        self._downloading = True
        
        def animate_status():
            """Show animated downloading status."""
            import time
            frames = ["⬇️ Downloading", "⬇️ Downloading.", "⬇️ Downloading..", "⬇️ Downloading..."]
            i = 0
            while self._downloading:
                self.status_var.set(f"{frames[i % 4]} {quality} ({model_size})")
                i += 1
                time.sleep(0.4)
        
        def download():
            try:
                # Start animation
                anim_thread = threading.Thread(target=animate_status, daemon=True)
                anim_thread.start()
                
                # Download the model
                from sentence_transformers import SentenceTransformer
                SentenceTransformer(model_name)
                
                # Stop animation
                self._downloading = False
                
                # Update UI
                self._update_model_status()
                self.status_var.set(f"✅ Downloaded {quality} model successfully!")
                
            except Exception as e:
                self._downloading = False
                self.status_var.set(f"❌ Download failed: {e}")
                messagebox.showerror("Download Error", str(e))
        
        thread = threading.Thread(target=download)
        thread.start()
    
    def _get_download_progress(self, model_name):
        """Get current download progress in MB by checking HuggingFace download locations."""
        import tempfile
        
        # Check multiple possible locations where HuggingFace downloads
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        model_folder = "models--" + model_name.replace("/", "--")
        model_path = os.path.join(cache_dir, model_folder)
        
        total_size = 0
        
        # 1. Check the model cache directory
        if os.path.exists(model_path):
            for dirpath, dirnames, filenames in os.walk(model_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except:
                        pass
        
        # 2. Check HuggingFace temp download directory
        hf_temp = os.path.join(cache_dir, ".tmp")
        if os.path.exists(hf_temp):
            for dirpath, dirnames, filenames in os.walk(hf_temp):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except:
                        pass
        
        # 3. Check system temp for any huggingface downloads
        temp_dir = tempfile.gettempdir()
        for item in os.listdir(temp_dir):
            if 'huggingface' in item.lower() or 'hf' in item.lower():
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        total_size += os.path.getsize(item_path)
                    elif os.path.isdir(item_path):
                        for dirpath, dirnames, filenames in os.walk(item_path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                try:
                                    total_size += os.path.getsize(fp)
                                except:
                                    pass
                except:
                    pass
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _get_model_cache_size(self, model_name):
        """Get the size of a fully cached model in MB."""
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        model_folder = "models--" + model_name.replace("/", "--")
        model_path = os.path.join(cache_dir, model_folder)
        
        if not os.path.exists(model_path):
            return 0
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(model_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except:
                    pass
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _delete_model(self, model_name):
        """Delete a cached model."""
        import shutil
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        model_folder = "models--" + model_name.replace("/", "--")
        model_path = os.path.join(cache_dir, model_folder)
        
        if os.path.exists(model_path):
            shutil.rmtree(model_path)
            return True
        return False
    
    def _manage_models(self):
        """Show dialog to manage downloaded models."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Manage Models")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 350) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(dialog, text="Downloaded Models", font=("Segoe UI", 14, "bold")).pack(pady=(15, 10))
        
        # Scrollable frame for model list
        models_frame = ctk.CTkScrollableFrame(dialog, height=180)
        models_frame.pack(fill="x", padx=15, pady=5)
        
        model_names = {
            "⚡ Fast": "sentence-transformers/all-MiniLM-L6-v2",
            "⚖️ Balanced": "BAAI/bge-small-en-v1.5", 
            "🎯 High Accuracy": "BAAI/bge-base-en-v1.5",
            "🚀 Best": "BAAI/bge-large-en-v1.5",
            "🌍 Multilingual": "BAAI/bge-m3"
        }
        
        any_downloaded = False
        
        for display_name, model_name in model_names.items():
            if self._is_model_downloaded(model_name):
                any_downloaded = True
                size_mb = self._get_model_cache_size(model_name)
                
                row = ctk.CTkFrame(models_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                ctk.CTkLabel(row, text=f"{display_name}", font=("Segoe UI", 11),
                            anchor="w", width=120).pack(side="left", padx=(0, 10))
                
                ctk.CTkLabel(row, text=f"{size_mb:.0f} MB", font=("Segoe UI", 10),
                            text_color="gray", width=60).pack(side="left")
                
                def make_delete_callback(mn=model_name, dn=display_name, r=row):
                    def callback():
                        if messagebox.askyesno("Delete Model", 
                                              f"Delete {dn}?\nYou'll need to re-download it to use this quality level."):
                            self._delete_model(mn)
                            r.destroy()
                            self._update_model_status()
                            self.status_var.set(f"Deleted {dn} model")
                    return callback
                
                ctk.CTkButton(row, text="Delete", width=60, height=24, corner_radius=4,
                             fg_color="#dc3545", hover_color="#c82333",
                             command=make_delete_callback()).pack(side="right")
        
        if not any_downloaded:
            ctk.CTkLabel(models_frame, text="No models downloaded yet", 
                        font=("Segoe UI", 11), text_color="gray").pack(pady=20)
        
        # Total size
        total_size = sum(self._get_model_cache_size(m) for m in model_names.values())
        ctk.CTkLabel(dialog, text=f"Total: {total_size:.0f} MB", 
                    font=("Segoe UI", 10), text_color="gray").pack(pady=5)
        
        ctk.CTkButton(dialog, text="Close", command=dialog.destroy,
                     width=80, height=28, corner_radius=6).pack(pady=10)
        
        if self.locator:
            self.status_var.set("Quality changed - click 'Load Index' to apply")
    
    def _load_index(self):
        pdf_dir = self.dir_entry.get()
        if not pdf_dir or not Path(pdf_dir).exists():
            messagebox.showerror("Error", "Please select a valid directory")
            return
        
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        
        # Check if model is downloaded
        if not self._is_model_downloaded(model_name):
            messagebox.showwarning("Model Required", 
                f"Please download the {quality} model first.\nClick the ⬇️ button next to the quality selector.")
            return
        
        # Ask user for indexing mode
        self._show_index_mode_dialog(pdf_dir, model_name, quality)
    
    def _show_index_mode_dialog(self, pdf_dir, model_name, quality):
        """Show dialog to choose indexing mode."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Choose Index Mode")
        dialog.geometry("420x280")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(dialog, text="How would you like to index?", 
                     font=("Segoe UI", 14, "bold")).pack(pady=(20, 15))
        
        # Fast mode button
        fast_frame = ctk.CTkFrame(dialog, corner_radius=8)
        fast_frame.pack(padx=20, pady=5, fill="x")
        
        def select_fast():
            dialog.destroy()
            self._do_load_index(pdf_dir, model_name, quality, precompute=False)
        
        ctk.CTkButton(fast_frame, text="⚡ Fast Index", command=select_fast,
                      width=120, height=32, corner_radius=6, 
                      font=("Segoe UI", 11, "bold")).pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(fast_frame, text="Quick startup, good for small collections\nMay miss semantically related pages",
                     font=("Segoe UI", 10), text_color="gray", justify="left").pack(side="left", padx=5)
        
        # Deep mode button
        deep_frame = ctk.CTkFrame(dialog, corner_radius=8)
        deep_frame.pack(padx=20, pady=5, fill="x")
        
        def select_deep():
            dialog.destroy()
            self._do_load_index(pdf_dir, model_name, quality, precompute=True)
        
        ctk.CTkButton(deep_frame, text="🔬 Deep Index", command=select_deep,
                      width=120, height=32, corner_radius=6,
                      font=("Segoe UI", 11, "bold")).pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(deep_frame, text="Slower startup, best for large collections\nFinds all related content",
                     font=("Segoe UI", 10), text_color="gray", justify="left").pack(side="left", padx=5)
        
        # Cancel button
        ctk.CTkButton(dialog, text="Cancel", command=dialog.destroy,
                      width=80, height=28, corner_radius=6, fg_color="gray").pack(pady=15)
    
    def _do_load_index(self, pdf_dir, model_name, quality, precompute=False):
        """Actually load the index with chosen mode."""
        def load():
            try:
                self.status_var.set("Loading model...")
                self.locator = HybridLocator(pdf_dir, model_name=model_name)
                
                if precompute:
                    self.status_var.set("Indexing PDF files...")
                    self.locator.build_index()
                    page_count = len(self.locator.documents)
                    self.status_var.set(f"Computing embeddings for {page_count} pages...")
                    self.locator.precompute_embeddings()
                else:
                    self.status_var.set("Indexing PDF files...")
                    self.locator.build_index()
                
                self.pdf_dir = pdf_dir
                page_count = len(self.locator.documents)
                mode = "Deep" if precompute else "Fast"
                
                self.status_var.set(f"✅ Ready! Indexed {page_count} pages ({mode} mode)")
                    
            except Exception as e:
                self.status_var.set(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e))
        
        self.status_var.set("Loading...")
        thread = threading.Thread(target=load)
        thread.start()
    
    def _clear_results(self):
        """Clear all result cards."""
        for card in self.result_cards:
            card.destroy()
        self.result_cards = []
        self.selected_card = None
    
    def _on_card_click(self, card):
        """Handle card selection."""
        # Deselect previous
        if self.selected_card:
            self.selected_card.set_selected(False)
        
        # Select new
        card.set_selected(True)
        self.selected_card = card
        
        # Update snippet
        self.snippet_text.delete("1.0", tk.END)
        self.snippet_text.insert("1.0", card.snippet)
    
    def _on_card_double_click(self, card):
        """Handle card double-click to open PDF."""
        self._on_card_click(card)
        self._open_selected()
    
    def _search(self):
        if not self.locator:
            messagebox.showwarning("Warning", "Please load an index first")
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
        
        # Start search animation
        self._searching = True
        self._animate_search()
        
        def do_search():
            try:
                result = self.locator.search(query, top_k=top_k, bm25_weight=bm25_weight)
                
                # Handle both old (list) and new (tuple) return format
                if isinstance(result, tuple):
                    results, is_cross_lingual = result
                else:
                    results = result
                    is_cross_lingual = False
                
                # Stop animation and update UI on main thread
                self._searching = False
                self.after(0, lambda: self._display_results(results, is_cross_lingual))
                
            except Exception as e:
                self._searching = False
                self.after(0, lambda: self.status_var.set(f"❌ Search error: {e}"))
        
        thread = threading.Thread(target=do_search)
        thread.start()
    
    def _animate_search(self):
        """Animate searching status with dots."""
        if not self._searching:
            return
        
        # Cycle through animation frames
        frames = ["🔍 Searching", "🔍 Searching.", "🔍 Searching..", "🔍 Searching..."]
        if not hasattr(self, '_search_frame'):
            self._search_frame = 0
        
        self.status_var.set(frames[self._search_frame % len(frames)])
        self._search_frame += 1
        
        # Continue animation every 300ms
        self.after(300, self._animate_search)
    
    def _display_results(self, results, is_cross_lingual):
        """Display search results (called on main thread)."""
        self.current_results = results
        
        # Clear previous results
        self._clear_results()
        self.snippet_text.delete("1.0", tk.END)
        
        # Hide placeholder
        self.placeholder_label.grid_forget()
        
        # Create result cards
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
            self.placeholder_label.configure(text="No results found. Try different keywords.")
            self.placeholder_label.grid(row=0, column=0, pady=50)
        
        # Show appropriate status message
        if is_cross_lingual:
            self.status_var.set(f"🌍 Cross-lingual: {len(self.current_results)} results (semantic only)")
        else:
            self.status_var.set(f"✅ Found {len(self.current_results)} results")
    
    def _open_selected(self):
        if not self.selected_card:
            messagebox.showinfo("Info", "Please select a result first")
            return
        
        pdf_path = Path(self.pdf_dir) / self.selected_card.pdf_name
        page_num = self.selected_card.page_num
        
        if not pdf_path.exists():
            messagebox.showerror("Error", f"PDF not found: {pdf_path}")
            return
        
        self.status_var.set(f"Opening {self.selected_card.pdf_name} at page {page_num}...")
        success = open_pdf_at_page(str(pdf_path), page_num)
        
        if success:
            self.status_var.set(f"✅ Opened {self.selected_card.pdf_name} at page {page_num}")
        else:
            self.status_var.set(f"⚠️ Opened {self.selected_card.pdf_name} (page navigation may not be supported)")


def main():
    global splash
    splash.set_status("Ready!", 100)
    splash.close()  # Close splash screen
    app = LocatorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()