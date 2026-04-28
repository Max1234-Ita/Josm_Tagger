# effects.py

import os
import tkinter as tk
from PIL import Image, ImageTk

from config_manager import load_config

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
    picture = (cfg.get("theme", {}) or {}).get("picture")
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

