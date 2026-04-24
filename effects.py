# effects.py

import tkinter as tk

class TransparencyFader:
    """Utility class to animate window alpha transitions."""

    def __init__(self, widget: tk.Tk):
        self.widget = widget
        self._fade_job = None

    def fade(self, start_alpha: float, end_alpha: float, duration_ms: int):
        """Animate alpha from start_alpha → end_alpha over duration_ms."""
        if self._fade_job:
            self.widget.after_cancel(self._fade_job)
            self._fade_job = None

        steps = max(1, int(duration_ms / 15))  # ~60 FPS
        delta = (end_alpha - start_alpha) / steps
        current = start_alpha

        def step():
            nonlocal current, steps
            current += delta
            steps -= 1

            if steps <= 0:
                self.widget.attributes("-alpha", end_alpha)
                return

            self.widget.attributes("-alpha", current)
            self._fade_job = self.widget.after(15, step)

        step()
