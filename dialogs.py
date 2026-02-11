"""
Dialog windows and popup menus for the Locus GUI.
Includes: rounded dropdown popup, manage models dialog, index mode dialog.

All CTkToplevel dialogs use a delayed-build pattern to prevent the
known Windows blink: withdraw() immediately, build content inside
an after() callback, then deiconify() once fully positioned.
"""

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
from fonts import ui_font
from i18n import t


# ---- Rounded popup dropdown ----

def show_rounded_popup(parent, anchor_widget, options, variable, on_select=None):
    """Show a rounded-corner dropdown popup below the anchor widget."""
    if hasattr(parent, '_active_popup') and parent._active_popup is not None:
        try:
            parent._active_popup.destroy()
        except Exception:
            pass
        parent._active_popup = None

    popup = ctk.CTkToplevel(parent)
    popup.withdraw()
    popup.overrideredirect(True)
    popup.transient(parent)
    popup.attributes("-topmost", False)
    parent._active_popup = popup

    def _build_and_show():
        frame = ctk.CTkFrame(popup, corner_radius=8)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        current_val = variable.get()
        btn_width = anchor_widget.cget("width")

        for i, opt in enumerate(options):
            is_current = (opt == current_val)
            def make_cmd(v=opt):
                def cmd():
                    variable.set(v)
                    popup.destroy()
                    parent._active_popup = None
                    if on_select:
                        on_select(v)
                return cmd

            btn = ctk.CTkButton(
                frame, text=opt, width=btn_width, height=28,
                corner_radius=6,
                fg_color=("gray78", "gray35") if is_current else "transparent",
                hover_color=("gray82", "gray30"),
                text_color=("gray10", "gray90"),
                font=ui_font(11), anchor="center",
                command=make_cmd()
            )
            top_pad = 4 if i == 0 else 1
            bot_pad = 4 if i == len(options) - 1 else 1
            btn.pack(padx=4, pady=(top_pad, bot_pad))

        parent.update_idletasks()
        popup.update_idletasks()
        ax = anchor_widget.winfo_rootx()
        ay = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 2
        popup.geometry(f"+{ax}+{ay}")
        popup.deiconify()

        def close_on_click(e):
            try:
                px, py = popup.winfo_rootx(), popup.winfo_rooty()
                pw, ph = popup.winfo_width(), popup.winfo_height()
                if not (px <= e.x_root <= px + pw and py <= e.y_root <= py + ph):
                    popup.destroy()
                    parent._active_popup = None
            except Exception:
                pass

        def bind_global_click():
            # Store bind id so we can unbind only this handler.
            popup._close_bind_id = parent.bind_all("<Button-1>", close_on_click, add="+")

        def follow_parent(_e=None):
            try:
                ax = anchor_widget.winfo_rootx()
                ay = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 2
                popup.geometry(f"+{ax}+{ay}")
            except Exception:
                pass

        def on_popup_destroy(e):
            try:
                bind_id = getattr(popup, "_close_bind_id", None)
                if bind_id:
                    parent.unbind_all("<Button-1>", bind_id)
            except Exception:
                pass
            try:
                parent.unbind("<Configure>", popup._follow_id)
            except Exception:
                pass

        popup.after(100, bind_global_click)
        popup._follow_id = parent.bind("<Configure>", follow_parent, add="+")
        popup.bind("<Destroy>", on_popup_destroy)
        popup.bind("<FocusOut>", lambda _e: popup.destroy())

    popup.after(30, _build_and_show)


# ---- Manage Models dialog ----

def show_manage_models_dialog(gui):
    """Show the model management dialog."""
    dialog = ctk.CTkToplevel(gui)
    dialog.withdraw()
    dialog.title(t("models.title"))
    dialog.resizable(True, True)
    dialog.minsize(400, 300)

    def _build_and_show():
        dialog.transient(gui)

        # Header
        ctk.CTkLabel(dialog, text=t("models.header"), font=ui_font(14, bold=True)).pack(pady=(15, 5))
        
        # Total size summary at top
        total_size = sum(
            gui._get_model_cache_size(m[1]) for m in gui.ALL_MODELS
            if not gui._is_bundled_model(m[1])
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
            group_models = [m for m in gui.ALL_MODELS if m[4] == group]
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
                is_bundled = gui._is_bundled_model(model_name)
                is_downloaded = gui._is_model_downloaded(model_name)
                
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
                    actual_mb = gui._get_model_cache_size(model_name)
                    subtitle = f"{model_short} · {actual_mb:.0f} MB"
                else:
                    subtitle = f"{model_short} · {size_str}"
                
                ctk.CTkLabel(info_frame, text=subtitle, font=ui_font(9),
                            text_color="gray", anchor="w").pack(side="top", anchor="w")
                
                # Action button
                if is_bundled:
                    pass
                elif is_downloaded:
                    def make_delete_cb(mn=model_name, dn=display_label, r=row):
                        def cb():
                            if messagebox.askyesno(t("models.delete_confirm_title"),
                                                  t("models.delete_confirm", quality=dn)):
                                gui._delete_model(mn)
                                r.destroy()
                                gui._update_model_status()
                                gui.status_var.set(t("status.deleted_model", quality=dn))
                        return cb
                    
                    ctk.CTkButton(row, text=t("models.delete"), width=60, height=26, 
                                 corner_radius=4, fg_color="#dc3545", hover_color="#c82333",
                                 font=ui_font(10),
                                 command=make_delete_cb()).grid(
                        row=0, column=2, padx=(4, 10), pady=8)
                else:
                    def make_download_cb(mn=model_name, dn=display_label):
                        def cb():
                            for lbl, mname in gui.quality_options.items():
                                if mname == mn:
                                    gui.quality_var.set(lbl)
                                    break
                            dialog.destroy()
                            gui._download_model()
                        return cb
                    
                    ctk.CTkButton(row, text="⬇️ " + size_str, width=90, height=26,
                                 corner_radius=4, fg_color=("gray70", "gray35"),
                                 hover_color=("gray60", "gray45"),
                                 font=ui_font(10),
                                 command=make_download_cb()).grid(
                        row=0, column=2, padx=(4, 10), pady=8)
        
        # Fusion method selector
        fusion_frame = ctk.CTkFrame(dialog, corner_radius=6, fg_color="transparent")
        fusion_frame.pack(fill="x", padx=15, pady=(0, 12))
        fusion_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(fusion_frame, text=t("fusion.label"), font=ui_font(11)).grid(
            row=0, column=0, padx=(4, 8), pady=6, sticky="w")
        
        fusion_options = [t("fusion.percentile"), t("fusion.rrf")]
        fusion_var = tk.StringVar(value=t("fusion.percentile") if gui.fusion_method == "percentile" else t("fusion.rrf"))
        
        def on_fusion_change(value):
            gui.fusion_method = "rrf" if value == t("fusion.rrf") else "percentile"
        
        ctk.CTkOptionMenu(
            fusion_frame, values=fusion_options, variable=fusion_var,
            command=on_fusion_change, width=180, height=26, corner_radius=6,
            fg_color=("gray75", "gray28"), button_color=("gray65", "gray35"),
            button_hover_color=("gray55", "gray40"), font=ui_font(11)
        ).grid(row=0, column=1, padx=(0, 4), pady=6, sticky="w")

        # Cache actions
        cache_frame = ctk.CTkFrame(dialog, corner_radius=6, fg_color="transparent")
        cache_frame.pack(fill="x", padx=15, pady=(0, 12))
        cache_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkButton(
            cache_frame, text=t("cache.clear_index"), width=160, height=26,
            corner_radius=6, fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"), font=ui_font(10),
            command=gui._clear_index_cache
        ).grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
        
        ctk.CTkButton(
            cache_frame, text=t("cache.clear_ocr"), width=160, height=26,
            corner_radius=6, fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"), font=ui_font(10),
            command=gui._clear_ocr_cache
        ).grid(row=0, column=1, padx=(0, 4), pady=4, sticky="w")

        # Position and show
        dialog.geometry("480x420")
        dialog.update_idletasks()
        x = gui.winfo_x() + (gui.winfo_width() - 480) // 2
        y = gui.winfo_y() + (gui.winfo_height() - 420) // 2
        dialog.geometry(f"480x420+{x}+{y}")
        dialog.deiconify()
        dialog.grab_set()

    dialog.after(50, _build_and_show)


# ---- Index Mode dialog ----

def show_index_mode_dialog(gui, pdf_dir, model_name, quality):
    """Show the fast/deep index mode selection dialog."""
    dialog = ctk.CTkToplevel(gui)
    dialog.withdraw()
    dialog.title(t("index_dialog.title"))
    dialog.resizable(False, False)

    def _build_and_show():
        dialog.transient(gui)
        
        ctk.CTkLabel(dialog, text=t("index_dialog.question"), 
                     font=ui_font(14, bold=True)).pack(pady=(20, 15))
        
        # Fast mode
        fast_frame = ctk.CTkFrame(dialog, corner_radius=8)
        fast_frame.pack(padx=20, pady=5, fill="x")
        
        def select_fast():
            dialog.destroy()
            gui._do_load_index(pdf_dir, model_name, quality, precompute=False)
        
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
            gui._do_load_index(pdf_dir, model_name, quality, precompute=True)
        
        ctk.CTkButton(deep_frame, text=t("index_dialog.deep"), command=select_deep,
                      width=120, height=32, corner_radius=6,
                      font=ui_font(11, bold=True)).pack(side="left", padx=12, pady=12)
        ctk.CTkLabel(deep_frame, text=t("index_dialog.deep_desc"),
                     font=ui_font(10), text_color="gray", justify="left").pack(side="left", padx=5)
        
        # Cancel
        ctk.CTkButton(dialog, text=t("index_dialog.cancel"), command=dialog.destroy,
                      width=80, height=28, corner_radius=6, fg_color="gray").pack(pady=15)
        
        # Position and show
        dialog.geometry("420x280")
        dialog.update_idletasks()
        x = gui.winfo_x() + (gui.winfo_width() - 420) // 2
        y = gui.winfo_y() + (gui.winfo_height() - 280) // 2
        dialog.geometry(f"420x280+{x}+{y}")
        dialog.deiconify()
        dialog.grab_set()

    dialog.after(50, _build_and_show)
