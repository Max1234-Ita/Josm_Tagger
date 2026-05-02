# effects.py

import os
import tkinter as tk
from PIL import Image, ImageTk

from config_manager import load_config


def get_active_theme(config=None):
    cfg = config if isinstance(config, dict) else load_config()
    dark_enabled = bool(cfg.get("dark_theme_enabled", False))
    key = "dark_theme" if dark_enabled else "theme"
    theme = (cfg.get(key, {}) or {})
    bg = theme.get("bg", "#f0f0f0")
    return {
        "bg": bg,
        "panel": theme.get("panel", bg),
        "fg": theme.get("fg", "#101010"),
        "panel_fg": theme.get("panel_fg", theme.get("fg", "#101010")),
        "picture": theme.get("picture"),
    }


class TransparencyFader:
    def __init__(self, owner):
        self.owner = owner          # MainForm
        self.widget = owner.root
        self._fade_job = None

    def fade(self, start_alpha, end_alpha, duration_ms):
        def step():
            nonlocal current, steps
            current += delta
            steps -= 1

            if steps <= 0:
                self.widget.attributes("-alpha", end_alpha)
                # fading terminato → sblocca
                self.owner._fade_in_progress = False
                return

            self.widget.attributes("-alpha", current)
            self._fade_job = self.widget.after(15, step)

        # -----------------------------------------------------
        print(f'Fading {start_alpha} -> {end_alpha} in {duration_ms} ms')

        if start_alpha != end_alpha:
            if self._fade_job:
                self.widget.after_cancel(self._fade_job)
                self._fade_job = None

            steps = max(1, int(duration_ms / 15))
            delta = (end_alpha - start_alpha) / steps
            current = start_alpha
        else:
            print(' -> (skipped)')
            return

        # quando parte un fade, blocchiamo focus_in
        self.owner._fade_in_progress = True
        step()


def apply_background_picture(window, config=None):
    """
    Apply background image to a form (Toplevel/Tk) only.
    Child widgets are not modified.
    """
    cfg = config if isinstance(config, dict) else load_config()
    picture = get_active_theme(cfg).get("picture")

    old_label = getattr(window, "_bg_image_label", None)
    if old_label is not None:
        try:
            old_label.destroy()
        except Exception:
            pass
        window._bg_image_label = None
        window._bg_image_tk = None
        window._bg_image_original = None

    if not picture:
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.join(base_dir, "resources")
    image_path = os.path.join(resources_dir, picture)

    if not os.path.isfile(image_path):
        return

    try:
        original = Image.open(image_path).convert("RGBA")
    except Exception:
        return

    bg_label = tk.Label(window, borderwidth=0, highlightthickness=0)
    bg_label.place(x=0, y=0, anchor="nw")
    bg_label.lower()

    window._bg_image_original = original
    window._bg_image_label = bg_label
    window._bg_image_tk = ImageTk.PhotoImage(window._bg_image_original)
    window._bg_image_label.configure(image=window._bg_image_tk)


from tkinter import ttk

def setup_scrollbar_style(config):
    """Configura lo stile TTK per le scrollbar in base al tema corrente."""
    theme = get_active_theme(config)
    bg = theme.get("bg")
    panel = theme.get("panel")
    p_fg = theme.get("panel_fg")
    
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    # Configurazione elementi Scrollbar
    style.configure("TScrollbar", 
                    gripcount=0,
                    background=panel, 
                    darkcolor=panel, 
                    lightcolor=panel,
                    troughcolor=bg, 
                    bordercolor=bg, 
                    arrowcolor=p_fg)
    
    # Effetto Hover
    style.map("TScrollbar",
              background=[('active', '#0078d7')],
              arrowcolor=[('active', 'white')])

def apply_theme_colors(window, config=None):
    theme = get_active_theme(config)
    bg = theme.get("bg", "#f0f0f0")
    panel = theme.get("panel", bg)
    fg = theme.get("fg", "#101010")
    panel_fg = theme.get("panel_fg", fg)
    
    # Inizializza stile scrollbar TTK
    setup_scrollbar_style(config)

    def apply(widget, root_widget=False):
        target_bg = bg if root_widget else panel
        target_fg = fg if root_widget else panel_fg
        
        # Gestione speciale per Menu
        if isinstance(widget, tk.Menu):
            try:
                widget.configure(bg=panel, fg=panel_fg, 
                                 activebackground="#0078d7", activeforeground="white",
                                 relief="flat")
            except Exception:
                pass
        # Gestione speciale per Scrollbar
        elif isinstance(widget, tk.Scrollbar):
            try:
                widget.configure(bg=panel, troughcolor=bg, 
                                 activebackground="#0078d7",
                                 highlightthickness=0, bd=0)
            except:
                pass
        # Gestione speciale per Spinbox
        elif isinstance(widget, tk.Spinbox):
            try:
                widget.configure(bg=panel, fg=panel_fg, 
                                 buttonbackground=panel,
                                 insertbackground=panel_fg)
            except:
                pass
        else:
            try:
                widget.configure(bg=target_bg, fg=target_fg)
            except Exception:
                try:
                    widget.configure(bg=target_bg)
                except Exception:
                    pass
                    
        for child in widget.winfo_children():
            apply(child, root_widget=False)

    apply(window, root_widget=True)

