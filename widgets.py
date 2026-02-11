"""
Custom widget components for the Locus GUI.
"""

import customtkinter as ctk
from fonts import ui_font
from i18n import t


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
