import sys
import tkinter as tk


class BaseWindowManager:
    def __init__(self, main_form):
        self.main_form = main_form
        self.root = main_form.root

    def setup_window_behavior(self):
        self.disable_maximize()

        try:
            self.root.bind("<FocusIn>", self.on_focus_in, add="+")
            self.root.bind("<FocusOut>", self.on_focus_out, add="+")
        except tk.TclError:
            pass

    def disable_maximize(self):
        pass

    def prevent_maximize(self, event):
        pass

    def force_focus(self):
        try:
            self.root.update_idletasks()
            self.root.lift()
            self.root.focus_force()
            self.main_form._activate_entry_for_next_command()
        except Exception:
            pass

    def on_focus_in(self, event=None):
        pass

    def on_focus_out(self, event=None):
        pass

    def fade_then_minimize_to_tray(self):
        self.main_form.minimize_to_tray()

    def _has_open_secondary_windows(self):
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.winfo_exists() and widget.winfo_viewable():
                    return True
        except Exception:
            pass
        return False


def get_window_manager(main_form):
    if sys.platform.startswith("linux"):
        from window_mgmt_linux import WindowManagerLinux

        return WindowManagerLinux(main_form)

    if sys.platform.startswith("win"):
        from window_mgmt_win import WindowManagerWin

        return WindowManagerWin(main_form)

    return BaseWindowManager(main_form)
