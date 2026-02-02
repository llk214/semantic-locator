"""
Simple GUI for the Semantic Page Locator
Uses tkinter (built into Python)
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from pathlib import Path
import threading
import subprocess
import platform
import os
import ctypes

# Fix blurry UI on Windows (DPI awareness)
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Fallback
        except:
            pass

from locator import HybridLocator


def open_pdf_at_page(pdf_path: str, page_num: int):
    """
    Open PDF at specific page using system default viewer.
    
    Supports:
    - Adobe Acrobat/Reader: /A "page=N"
    - SumatraPDF: -page N
    - Foxit Reader: /A "page=N"
    - macOS Preview: -a Preview with AppleScript
    - Linux: evince, okular, etc.
    """
    system = platform.system()
    pdf_path = os.path.abspath(pdf_path)
    
    if system == "Windows":
        # Try common PDF readers with page argument
        # SumatraPDF (recommended - lightweight and supports page arg well)
        sumatra_paths = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
        ]
        
        for sumatra in sumatra_paths:
            if os.path.exists(sumatra):
                subprocess.Popen([sumatra, "-page", str(page_num), pdf_path])
                return True
        
        # Adobe Acrobat/Reader
        adobe_paths = [
            r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        ]
        
        for adobe in adobe_paths:
            if os.path.exists(adobe):
                subprocess.Popen([adobe, "/A", f"page={page_num}", pdf_path])
                return True
        
        # Fallback: open with default app (won't go to specific page)
        os.startfile(pdf_path)
        return False  # Opened but couldn't go to page
        
    elif system == "Darwin":  # macOS
        # Use Preview with AppleScript for page navigation
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
        
    else:  # Linux
        # Try evince (GNOME), okular (KDE), or xdg-open
        viewers = [
            (["evince", "-p", str(page_num), pdf_path], "evince"),
            (["okular", "-p", str(page_num), pdf_path], "okular"),
            (["xdg-open", pdf_path], "xdg-open"),  # Fallback, no page support
        ]
        
        for cmd, name in viewers:
            try:
                subprocess.Popen(cmd)
                return name != "xdg-open"
            except FileNotFoundError:
                continue
        
        return False
    
    return False


class LocatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📚 Course PDF Search")
        self.root.geometry("1400x700")
        self.root.minsize(800, 600)
        
        # Apply a nicer theme
        style = ttk.Style()
        available_themes = style.theme_names()
        # Prefer modern themes
        for theme in ['vista', 'winnative', 'clam', 'alt']:
            if theme in available_themes:
                style.theme_use(theme)
                break
        
        # Custom styling
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=2)
        style.configure('Header.TLabel', font=('Segoe UI', 11, 'bold'))
        
        self.locator = None
        self.pdf_dir = None
        self.current_results = []  # Store search results for opening
        
        self._create_widgets()
        
    def _create_widgets(self):
        # Top frame - directory selection
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="PDF Directory:").pack(side=tk.LEFT)
        
        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(top_frame, textvariable=self.dir_var, width=50)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="Browse", command=self._browse_dir).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Load/Rebuild Index", command=self._load_index).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Select a directory with PDFs")
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=5)
        
        # Search frame
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(search_frame, textvariable=self.query_var, width=60)
        self.query_entry.pack(side=tk.LEFT, padx=5)
        self.query_entry.bind('<Return>', lambda e: self._search())
        
        ttk.Button(search_frame, text="Search", command=self._search).pack(side=tk.LEFT)
        
        # Options frame
        options_frame = ttk.Frame(self.root, padding="5")
        options_frame.pack(fill=tk.X)
        
        ttk.Label(options_frame, text="Results:").pack(side=tk.LEFT)
        self.topk_var = tk.StringVar(value="5")
        ttk.Spinbox(options_frame, from_=1, to=20, width=5, textvariable=self.topk_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(options_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=15, fill=tk.Y)
        
        # Search quality dropdown (friendly names for models)
        ttk.Label(options_frame, text="Search Quality:").pack(side=tk.LEFT)
        
        self.quality_options = {
            "⚡ Fast": "sentence-transformers/all-MiniLM-L6-v2",
            "⚖️ Balanced": "sentence-transformers/all-mpnet-base-v2", 
            "🎯 High Accuracy": "BAAI/bge-base-en-v1.5",
            "🚀 Best": "BAAI/bge-large-en-v1.5"
        }
        
        self.quality_var = tk.StringVar(value="⚡ Fast")
        quality_dropdown = ttk.Combobox(options_frame, textvariable=self.quality_var,
                                         values=list(self.quality_options.keys()),
                                         state="readonly", width=18)
        quality_dropdown.pack(side=tk.LEFT, padx=5)
        quality_dropdown.bind("<<ComboboxSelected>>", self._on_quality_change)
        
        # Info label
        self.quality_info_var = tk.StringVar(value="~80MB, runs on 4GB laptops")
        ttk.Label(options_frame, textvariable=self.quality_info_var, 
                  foreground='gray', font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=5)
        
        # Semantic vs Literal slider frame
        slider_frame = ttk.LabelFrame(self.root, text="Search Mode", padding="10")
        slider_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Labels on either end
        slider_inner = ttk.Frame(slider_frame)
        slider_inner.pack(fill=tk.X)
        
        ttk.Label(slider_inner, text="🧠 Semantic\n(meaning-based)", 
                  font=('Segoe UI', 9), justify='center').pack(side=tk.LEFT)
        
        # Slider in the middle
        self.search_mode_var = tk.DoubleVar(value=0.3)
        self.search_slider = ttk.Scale(slider_inner, from_=0.0, to=1.0, 
                                        variable=self.search_mode_var,
                                        orient=tk.HORIZONTAL, length=300,
                                        command=self._update_slider_label)
        self.search_slider.pack(side=tk.LEFT, padx=20, expand=True)
        
        ttk.Label(slider_inner, text="🔤 Literal\n(exact keywords)", 
                  font=('Segoe UI', 9), justify='center').pack(side=tk.RIGHT)
        
        # Current value indicator
        self.slider_label_var = tk.StringVar(value="Balanced (70% semantic, 30% literal)")
        ttk.Label(slider_frame, textvariable=self.slider_label_var, 
                  font=('Segoe UI', 9, 'italic')).pack(pady=(5, 0))
        
        # Results area - using Treeview for selectable results
        results_frame = ttk.Frame(self.root, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for results
        columns = ('rank', 'pdf', 'page', 'score', 'snippet')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=10)
        
        self.results_tree.heading('rank', text='#')
        self.results_tree.heading('pdf', text='PDF')
        self.results_tree.heading('page', text='Page')
        self.results_tree.heading('score', text='Score')
        self.results_tree.heading('snippet', text='Snippet')
        
        self.results_tree.column('rank', width=30, anchor='center')
        self.results_tree.column('pdf', width=150)
        self.results_tree.column('page', width=50, anchor='center')
        self.results_tree.column('score', width=60, anchor='center')
        self.results_tree.column('snippet', width=500)
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to open
        self.results_tree.bind('<Double-1>', self._on_double_click)
        
        # Bottom frame - Open button and snippet display
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        self.open_btn = ttk.Button(bottom_frame, text="📄 Open PDF at Page", command=self._open_selected)
        self.open_btn.pack(side=tk.LEFT)
        
        ttk.Label(bottom_frame, text="  (or double-click a result)", 
                  foreground='gray').pack(side=tk.LEFT)
        
        # Snippet preview
        snippet_frame = ttk.LabelFrame(self.root, text="Snippet Preview", padding="5")
        snippet_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.snippet_text = scrolledtext.ScrolledText(snippet_frame, wrap=tk.WORD, 
                                                       height=4, font=('Consolas', 9))
        self.snippet_text.pack(fill=tk.X)
        
        # Show snippet on selection
        self.results_tree.bind('<<TreeviewSelect>>', self._on_select)
        
    def _browse_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_var.set(directory)
    
    def _update_slider_label(self, value):
        """Update the slider description based on current value."""
        val = float(value)
        semantic_pct = int((1 - val) * 100)
        literal_pct = int(val * 100)
        
        if val < 0.2:
            mode = "Mostly semantic"
        elif val < 0.4:
            mode = "Balanced (semantic-leaning)"
        elif val < 0.6:
            mode = "Balanced"
        elif val < 0.8:
            mode = "Balanced (literal-leaning)"
        else:
            mode = "Mostly literal"
        
        self.slider_label_var.set(f"{mode} ({semantic_pct}% semantic, {literal_pct}% literal)")
    
    def _on_quality_change(self, event):
        """Update info label and reload model when quality changes."""
        quality = self.quality_var.get()
        
        info_map = {
            "⚡ Fast": "~80MB, needs 4GB RAM",
            "⚖️ Balanced": "~420MB, needs 8GB RAM",
            "🎯 High Accuracy": "~440MB, needs 8GB+ RAM",
            "🚀 Best": "~1.3GB, needs 16GB+ RAM"
        }
        self.quality_info_var.set(info_map.get(quality, ""))
        
        # Mark that model needs reload
        if self.locator:
            self.status_var.set("Quality changed - click 'Load/Rebuild Index' to apply")
            
    def _load_index(self):
        pdf_dir = self.dir_var.get()
        if not pdf_dir or not Path(pdf_dir).exists():
            messagebox.showerror("Error", "Please select a valid directory")
            return
        
        # Get selected model
        quality = self.quality_var.get()
        model_name = self.quality_options.get(quality)
        
        self.status_var.set("Loading index... (this may take a moment)")
        self.root.update()
        
        def load():
            try:
                self.locator = HybridLocator(pdf_dir, model_name=model_name)
                self.locator.build_index()
                self.pdf_dir = pdf_dir
                page_count = len(self.locator.documents)
                if model_name:
                    self.status_var.set(f"Ready! Indexed {page_count} pages with {quality.split()[0]} mode")
                else:
                    self.status_var.set(f"Ready! Indexed {page_count} pages (keywords only)")
            except Exception as e:
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", str(e))
        
        # Run in background thread
        thread = threading.Thread(target=load)
        thread.start()
        
    def _search(self):
        if not self.locator:
            messagebox.showwarning("Warning", "Please load an index first")
            return
            
        query = self.query_var.get().strip()
        if not query:
            return
            
        try:
            top_k = int(self.topk_var.get())
            bm25_weight = self.search_mode_var.get()  # From slider
        except ValueError:
            top_k = 5
            bm25_weight = 0.3
        
        self.status_var.set("Searching...")
        self.root.update()
        
        try:
            # Get results
            self.current_results = self.locator.search(query, top_k=top_k, bm25_weight=bm25_weight)
            
            # Clear previous results
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.snippet_text.delete(1.0, tk.END)
            
            # Populate treeview
            for i, r in enumerate(self.current_results, 1):
                snippet_short = r['snippet'][:80] + "..." if len(r['snippet']) > 80 else r['snippet']
                self.results_tree.insert('', tk.END, values=(
                    i,
                    r['pdf_name'],
                    r['page_num'],
                    r['score'],
                    snippet_short
                ))
            
            self.status_var.set(f"Found {len(self.current_results)} results")
            
        except Exception as e:
            self.status_var.set(f"Search error: {e}")
    
    def _on_select(self, event):
        """Show full snippet when a result is selected."""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            rank = int(item['values'][0]) - 1  # 0-indexed
            
            if 0 <= rank < len(self.current_results):
                snippet = self.current_results[rank]['snippet']
                self.snippet_text.delete(1.0, tk.END)
                self.snippet_text.insert(tk.END, snippet)
    
    def _on_double_click(self, event):
        """Open PDF on double-click."""
        self._open_selected()
    
    def _open_selected(self):
        """Open the selected PDF at the specified page."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a result first")
            return
        
        item = self.results_tree.item(selection[0])
        rank = int(item['values'][0]) - 1
        
        if 0 <= rank < len(self.current_results):
            result = self.current_results[rank]
            pdf_path = Path(self.pdf_dir) / result['pdf_name']
            page_num = result['page_num']
            
            if not pdf_path.exists():
                messagebox.showerror("Error", f"PDF not found: {pdf_path}")
                return
            
            self.status_var.set(f"Opening {result['pdf_name']} at page {page_num}...")
            success = open_pdf_at_page(str(pdf_path), page_num)
            
            if success:
                self.status_var.set(f"Opened {result['pdf_name']} at page {page_num}")
            else:
                self.status_var.set(f"Opened {result['pdf_name']} (page navigation may not be supported)")


def main():
    root = tk.Tk()
    app = LocatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()