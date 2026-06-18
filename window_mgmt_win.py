# window_mgmt_win.py

import ctypes
import sys
import time
import tkinter as tk

from window_mgmt import BaseWindowManager
from config_manager import debug_print
import effects


class WindowManagerWin(BaseWindowManager):
    def disable_maximize(self):
        """Completely disables window maximization on Windows via ctypes."""
        try:
            self.root.attributes("-toolwindow", True)
        except Exception:
            pass

        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

            GWL_STYLE = -16
            WS_MAXIMIZEBOX = 0x00010000

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style &= ~WS_MAXIMIZEBOX

            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        except Exception:
            pass

    def prevent_maximize(self, event):
        """If window is maximized, restore saved geometry on Windows."""
        if self.root.state() == "zoomed":
            self.root.state("normal")
            self.main_form.apply_geometry()

    def force_focus(self):
        """Aggressively force focus on the window and entry box using Windows API."""
        try:
            self.root.update_idletasks()
            self.root.focus_force()
            self.main_form._activate_entry_for_next_command()

            # On Windows, try to force focus via ctypes for .exe compatibility
            hwnd = self.root.winfo_id()

            # Get the ID of the foreground window's thread
            foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
            foreground_thread_id = ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, None)
            
            # Get the ID of our application's thread
            current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

            # Attach our thread to the foreground window's thread
            ctypes.windll.user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
            
            # Bring window to foreground (Windows API)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.SetActiveWindow(hwnd)

            # Detach our thread from the foreground window's thread
            ctypes.windll.user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)

        except Exception as e:
            debug_print(f"Error forcing focus on Windows: {e}", cfg=self.main_form.config)

    def on_focus_in(self, event=None):
        """Fade-in only when necessary, with debounce."""
        effects.fade_away = True
        self.main_form._activate_entry_for_next_command()

        now = time.time()

        if self.main_form._fade_in_progress:
            debug_print("Focus In prevented (fade running)", cfg=self.main_form.config)
            return

        # Debounce: ignore events too close (< 80 ms)
        if hasattr(self.main_form, "_last_focus_in") and (now - self.main_form._last_focus_in) < 0.08:
            debug_print("Focus In prevented (debounced)", cfg=self.main_form.config)
            return

        self.main_form._last_focus_in = now

        beh = self.main_form.config.get("behaviour", {})
        target = beh.get("transparency_active", 100) / 100
        try:
            current_alpha = float(self.root.attributes("-alpha"))
        except Exception:
            current_alpha = 1.0

        # If we are already practically at the target, do not redo the fade
        fade_duration = beh.get("fade_duration_ms", 250)
        if abs(current_alpha - target) < 0.01:
            debug_print("Fading", current_alpha, "->", target, "in", fade_duration, "ms\n -> (skipped)", cfg=self.main_form.config)
            return

        debug_print(f"Fading {current_alpha} -> {target} in {fade_duration} ms", cfg=self.main_form.config)

        self.main_form.fader.fade(
            start_alpha=current_alpha,
            end_alpha=target,
            duration_ms=fade_duration
        )

    def on_focus_out(self, event=None):
        """Fade-out only when focus really leaves the window, with debounce."""
        now = time.time()

        if self.main_form._fade_in_progress:
            debug_print("Focus Out prevented (fade running)", cfg=self.main_form.config)
            return

        # Debounce: ignore events too close (< 80 ms)
        if hasattr(self.main_form, "_last_focus_out") and (now - self.main_form._last_focus_out) < 0.08:
            debug_print("Focus Out prevented (debounced)", cfg=self.main_form.config)
            return

        self.main_form._last_focus_out = now

        # 1) Block during startup or transitions (e.g. menu) or if secondary windows are open
        if (not self.main_form.allow_focus_out or self.main_form._block_focus_out or
            getattr(effects, "is_any_form_opening", False) or 
            self._has_open_secondary_windows()):
            
            if getattr(effects, "is_any_form_opening", False):
                debug_print("Focus Out prevented (internal form opening)", cfg=self.main_form.config)
                beh = self.main_form.config.get("behaviour", {})
                self.main_form.fader.stop(reset_alpha=beh.get("transparency_active", 100) / 100)
            elif self._has_open_secondary_windows():
                debug_print("Focus Out prevented (secondary window open)", cfg=self.main_form.config)
            else:
                debug_print(f"Focus Out prevented (startup/blocked, allow={self.main_form.allow_focus_out}, block={self.main_form._block_focus_out})", cfg=self.main_form.config)
            return

        # 2) Block during tag sending
        if self.main_form._sending_in_progress:
            debug_print("Focus Out prevented (sending)", cfg=self.main_form.config)
            return

        if not self.main_form.allow_fade:
            debug_print("Focus Out prevented (fade disabled)", cfg=self.main_form.config)
            return

        # 3) If focus is still inside the application -> NOT a real FocusOut.
        try:
            focused_widget = self.root.focus_get()
            if focused_widget is not None:
                debug_print(f"Focus Out prevented (focus on widget: {focused_widget})", cfg=self.main_form.config)
                return
                
            focused_display = self.root.focus_displayof()
            if focused_display is not None:
                debug_print("Focus Out prevented (focus_displayof match)", cfg=self.main_form.config)
                return

            raw_focus = self.root.tk.call('focus')
            if raw_focus and (('.popdown' in str(raw_focus).lower()) or ('.tk_choice_list' in str(raw_focus).lower())):
                debug_print(f"Focus Out prevented (focus on popdown: {raw_focus})", cfg=self.main_form.config)
                return
        except (KeyError, tk.TclError):
            pass

        # 4) If we are already faded, do not redo the fade
        beh = self.main_form.config.get("behaviour", {})
        target = beh.get("transparency_faded", 35) / 100
        try:
            current_alpha = float(self.root.attributes("-alpha"))
        except Exception:
            current_alpha = 1.0

        if current_alpha <= target + 0.01:
            debug_print("Focus Out prevented (already faded)", cfg=self.main_form.config)
            return

        debug_print(">>> REAL FOCUS OUT DETECTED <<<", cfg=self.main_form.config)
        fade_duration = beh.get("fade_duration_ms", 250)
        debug_print(f"Fading {current_alpha} -> {target} in {fade_duration} ms", cfg=self.main_form.config)

        self.main_form.fader.fade(
            start_alpha=current_alpha,
            end_alpha=target,
            duration_ms=fade_duration
        )

    def fade_then_minimize_to_tray(self):
        """Performs fade-out first and only then hides the window in tray."""
        if self.main_form.allow_fade:
            self.main_form._block_focus_out = True

            beh = self.main_form.config.get("behaviour", {})
            target = beh.get("transparency_faded", 35) / 100
            try:
                current_alpha = float(self.root.attributes("-alpha"))
            except Exception:
                current_alpha = 1.0

            fade_duration = beh.get("fade_duration_ms", 250)
            if current_alpha > target + 0.01:
                self.main_form.fader.fade(
                    start_alpha=current_alpha,
                    end_alpha=target,
                    duration_ms=fade_duration
                )

            self.root.after(fade_duration, self.main_form.minimize_to_tray)
        else:
            debug_print('Fading prevented. allow_fade = False', cfg=self.main_form.config)

    def _has_open_secondary_windows(self):
        """Check if any Toplevel windows (other than the main window) are visible."""
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    if widget.winfo_exists() and widget.winfo_viewable():
                        return True
        except Exception:
            pass
        return False
