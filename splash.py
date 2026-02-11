"""
Splash screen shown immediately on startup while heavy libraries load.
"""

import tkinter as tk
from i18n import t
from fonts import ui_font, emoji_font, _resolve_zh_font


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
