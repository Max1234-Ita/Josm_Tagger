# window_mgmt_linux.py

import sys
import time
import subprocess
import shutil
import tkinter as tk

from window_mgmt import BaseWindowManager
from config_manager import debug_print
import effects


class WindowManagerLinux(BaseWindowManager):
    def disable_maximize(self):
        """On Linux, we generally don't disable maximize button via API.
        We rely on window manager hints or just let it be."""
        pass

    def prevent_maximize(self, event):
        """On Linux, we don't typically prevent maximize in the same way as Windows.
        The window manager handles this."""
        pass

    def force_focus(self):
        """Force focus on the window and entry box using Linux commands."""
        try:
            self.root.update_idletasks()
            self.root.focus_force()
            self.main_form._activate_entry_for_next_command()

            # Try to bring the window to the foreground using wmctrl or xdotool
            # This part is adapted from josm_interface.py focus_josm for Linux
            
            # Get the window ID of the current Tkinter window
            window_id = self.root.winfo_id()
            
            # Attempt to activate/raise using wmctrl
            if shutil.which("wmctrl"):
                try:
                    debug_print(f"Activating window {window_id} via wmctrl", cfg=self.main_form.config)
                    subprocess.run(["wmctrl", "-ia", str(window_id)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(0.1) # Give WM time to react
                    return
                except Exception as e:
                    debug_print(f"Error activating window via wmctrl: {e}", cfg=self.main_form.config)

            # Fallback to xdotool if wmctrl fails or is not available
            if shutil.which("xdotool"):
                try:
                    debug_print(f"Activating window {window_id} via xdotool", cfg=self.main_form.config)
                    subprocess.run(
                        ["xdotool", "windowactivate", "--sync", str(window_id)],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.5,
                    )
                    subprocess.run(
                        ["xdotool", "windowraise", str(window_id)],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.5,
                    )
                    time.sleep(0.1) # Give WM time to react
                    return
                except Exception as e:
                    debug_print(f"Error activating window via xdotool: {e}", cfg=self.main_form.config)
            
            debug_print("Could not aggressively force focus on Linux (wmctrl/xdotool not found or failed).", cfg=self.main_form.config)

        except Exception as e:
            debug_print(f"Error forcing focus on Linux: {e}", cfg=self.main_form.config)

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
        if abs(current_alpha - target) < 0.01:
            debug_print("Fading", current_alpha, "->", target, "in", self.main_form.fade_duration_ms, "ms\n -> (skipped)", cfg=self.main_form.config)
            return

        debug_print(f"Fading {current_alpha} -> {target} in {self.main_form.fade_duration_ms} ms", cfg=self.main_form.config)

        self.main_form.fader.fade(
            start_alpha=current_alpha,
            end_alpha=target,
            duration_ms=self.main_form.fade_duration_ms
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
        debug_print(f"Fading {current_alpha} -> {target} in {self.main_form.fade_duration_ms} ms", cfg=self.main_form.config)

        self.main_form.fader.fade(
            start_alpha=current_alpha,
            end_alpha=target,
            duration_ms=self.main_form.fade_duration_ms
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

            if current_alpha > target + 0.01:
                self.main_form.fader.fade(
                    start_alpha=current_alpha,
                    end_alpha=target,
                    duration_ms=self.main_form.fade_duration_ms
                )

            self.root.after(self.main_form.fade_duration_ms, self.main_form.minimize_to_tray)
        else:
            debug_print('Fading prevented. allow_fade = False', cfg=self.main_form.config)
