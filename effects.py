# effects.py

import tkinter as tk

class TransparencyFader:
    def __init__(self, owner):
        self.owner = owner          # MainForm
        self.widget = owner.root
        self._fade_job = None

    def fade(self, start_alpha, end_alpha, duration_ms):
        if self._fade_job:
            self.widget.after_cancel(self._fade_job)
            self._fade_job = None

        steps = max(1, int(duration_ms / 15))
        delta = (end_alpha - start_alpha) / steps
        current = start_alpha

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

        # quando parte un fade, blocchiamo focus_in
        self.owner._fade_in_progress = True
        step()

