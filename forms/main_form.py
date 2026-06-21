import os
import sys
import json
import time
import threading
import queue
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

# ---------------------------------------------------------------------------
# NOTE ON PYSTRAY (IMPORTANT)
#
# PyPI only distributes pystray 0.19.5, which does NOT support correctly:
# - detach=True
# - run_detached()
# - global hotkey when window is hidden
#
# To get the correct version (development), install from GitHub:
#
#   pip uninstall pystray -y
#   pip install git+https://github.com/moses-palmer/pystray.git
#
# The GitHub version still claims "0.19.5", but includes:
# - run_detached()
# - fix for Windows
# - fix for hotkey
# - fix for fading
# ---------------------------------------------------------------------------

import pystray

from PIL import Image

from config_manager import debug_print, load_config, save_config
from codes_manager import load_codes
from hotkeys import start_hotkeys
if sys.platform.startswith("linux"):
    from linux_hotkeys import (
        start_hotkeys as start_linux_hotkeys,
        linux_global_hotkeys_status,
        linux_hotkey_matches,
    )
    try:
        from linux_instance_control import INSTANCE_SOCKET_PATH, LinuxInstanceServer
    except ImportError:
        # Fallback if linux_instance_control is not available (e.g., during development on non-merged branch)
        LinuxInstanceServer = None
        INSTANCE_SOCKET_PATH = None
else:
    start_linux_hotkeys = None
    LinuxInstanceServer = None
    INSTANCE_SOCKET_PATH = None

    def linux_global_hotkeys_status():
        return "n/a"

    def linux_hotkey_matches(event=None, spec="ctrl+0"):
        return False
import effects
from effects import TransparencyFader, get_active_theme, apply_theme_colors, apply_background_picture
from josm_interface import send_tags, focus_josm
from update_checker import check_for_updates # Re-added import
from url_launcher import open_url_in_default_browser # Re-added import
from forms.tag_editor_form import TagEditorForm
from forms.font_selector_form import FontSelectorForm
from forms.search_form import SearchForm
from window_mgmt import get_window_manager


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent
    return os.path.join(base_path, relative_path)


class Tooltip:
    """Simple tooltip widget for Tkinter."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.showtip)
        widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 8)
        )
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class MainForm:

    def __init__(self, root):
        self.root = root
        self.root.main_form_instance = self
        self.config = load_config()
        self.codes = load_codes()
        self.win_mgmt = get_window_manager(self) # Initialize window manager

        root.title("JOSM Tagger")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 1)

        # --- TRAY STATE ---
        self.tray_icon = None
        self.tray_thread = None
        self.tray_running = False
        self._is_exiting = False
        self._last_normal_geometry = None
        self._save_geometry_job = None
        self._tray_minimize_notice_shown = False

        # --- THEME ---
        # Initial theme application handled by apply_theme() later
        self.bg_color = None # Will be set by apply_theme
        self.fg_color = None # Will be set by apply_theme

        # --- APP ICON ---
        try:
            icon_path = resource_path("resources/josm_tagger.ico")
            root.iconbitmap(icon_path)
        except:
            pass

        # --- MIN FORM SIZE ---
        self.root.minsize(256, 160)

        # --- GEOMETRY ---
        self.apply_geometry()
        self.root.bind("<Configure>", self.win_mgmt.prevent_maximize)
        self.root.bind("<Configure>", self._on_main_configure, add="+")

        # X → minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self._on_main_window_close)

        # --- WINDOW STATE ---
        self.allow_minimize = True
        self.allow_fade = True
        self._fade_in_progress = False
        self.allow_focus_out = False
        self.root.after(500, lambda: setattr(self, "allow_focus_out", True))
        self._is_faded = False
        self.fader = TransparencyFader(self)
        self._sending_in_progress = False
        self._block_focus_out = False
        # fade_duration_ms will be set by apply_theme or _apply_runtime_theme

        # --- WINDOW MANAGER (OS Specific Focus & Maximize) ---
        self.win_mgmt.setup_window_behavior()

        # Track send() state
        self._update_check_in_progress = False
        self._hotkey_events = queue.Queue()
        self._linux_instance_server = None
        self._linux_shortcut_helper_path = Path.home() / "josmtagger.sh"
        if sys.platform.startswith("linux"):
            print(f"Linux pynput status: {linux_global_hotkeys_status()}")

        # Keyboard shortcuts
        self.root.bind("<Control-f>", self.open_search)
        self.root.bind("<Control-F>", self.open_search)
        self.root.bind("<Alt-F4>", lambda e: self._exit_app())

        # Declared attributes
        self.filtered_codes = []
        self._trace_id = None
        self.code_var = None
        self.entry = None
        self.apply_button = None
        self.code_list = None
        self.preview = None
        self.context_menu = None
        self.history_menu = None
        self.menubar = None
        self.preview_frame = None
        self.paned = None
        self.toggle_button = None
        self.expand_image = None
        self.collapse_image = None

        # Panel state
        self.preview_expanded = self.config.get("preview_expanded", True)
        self.preview_height = max(160, self.config.get("preview_height", 160))
        self.upper_height = self.config.get("upper_height", None)

        # Build GUI
        self.build_menu()
        self.build_ui()
        self._init_command_history()
        self.register_hotkey()
        self.root.after(100, self._process_hotkey_events)
        self.apply_font()
        self.apply_theme() # Initial theme application
        self.update_list()
        self._start_linux_instance_server()
        self.root.after(800, self._ensure_linux_shortcut_helper)
        self._start_tray_icon()
        self.root.after(2000, self._auto_check_for_updates)

        # Tooltip
        self._list_tooltip_window = None
        self._list_tooltip_last_index = None

        # Dropdown initial: only available codes (sorted)
        self.entry["values"] = sorted(self.codes.keys())

        # Restore panes layout after Tk has stabilized geometry
        self.root.after_idle(self._restore_panes_layout)
        self.root.after(120, self.win_mgmt.force_focus)

    # ---------------------------------------------------------
    # GEOMETRY
    # ---------------------------------------------------------
    def apply_geometry(self):
        geom = self.config.get("geometry", {}).get("main_form")
        if geom:
            try:
                x = geom.get("x", 100)
                y = geom.get("y", 100)
                w = geom.get("w", 560)
                h = geom.get("h", 520)
                self.root.geometry(f"{w}x{h}+{x}+{y}")
                self._last_normal_geometry = {"x": x, "y": y, "w": w, "h": h}
                return
            except:
                pass
        self.root.geometry("560x520")
        self._last_normal_geometry = {"x": 100, "y": 100, "w": 560, "h": 520}

    def save_geometry(self):
        """
        Save only the main window geometry (position and size).
        Does not modify other config settings.
        """
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        if "geometry" not in self.config:
            self.config["geometry"] = {}

        self.config["geometry"]["main_form"] = {
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def _capture_current_normal_geometry(self):
        try:
            if str(self.root.state()) == "zoomed":
                return
        except Exception:
            pass

        try:
            x = int(self.root.winfo_x())
            y = int(self.root.winfo_y())
            w = int(self.root.winfo_width())
            h = int(self.root.winfo_height())
            if w > 100 and h > 80:
                self._last_normal_geometry = {"x": x, "y": y, "w": w, "h": h}
        except Exception:
            pass

    def _on_main_configure(self, _event=None):
        if self._is_exiting:
            return
        self._capture_current_normal_geometry()
        if self._save_geometry_job is not None:
            try:
                self.root.after_cancel(self._save_geometry_job)
            except Exception:
                pass
        self._save_geometry_job = self.root.after(250, self._flush_geometry_to_config)

    def _flush_geometry_to_config(self):
        self._save_geometry_job = None
        if not self._last_normal_geometry:
            return

        self.config.setdefault("geometry", {})
        current = self.config["geometry"].get("main_form", {})
        if current != self._last_normal_geometry:
            self.config["geometry"]["main_form"] = dict(self._last_normal_geometry)
            save_config(self.config)

    def save_config(self):
        """
        Save preview panel state and pane heights.
        """
        self.config["preview_expanded"] = self.preview_expanded
        self.config["preview_height"] = self.preview_height
        self.config["upper_height"] = self.upper_height

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    # ---------------- MENU ----------------
    def build_menu(self):
        """Creates a custom menu bar with non-blocking dropdown logic."""
        self.menubar_frame = tk.Frame(self.root, bd=0, relief="flat", height=28)
        self.menubar_frame.pack(side="top", fill="x")
        
        self.menu_buttons = []
        self._menu_data = {}
        self._menu_active = False
        self._active_dropdown = None
        self._active_button = None
        self._close_job = None

        class MenuProxy:
            def __init__(self): self.items = []
            def add_command(self, label, command=None, accelerator=None):
                self.items.append({"label": label, "command": command, "accel": accelerator})
            def add_separator(self):
                self.items.append({"label": "---", "command": None, "accel": None})

        def create_menu_item(label, setup_func):
            btn = tk.Label(self.menubar_frame, text=label, padx=12, pady=5, cursor="hand2")
            btn.pack(side="left")
            
            proxy = MenuProxy()
            setup_func(proxy)
            self._menu_data[btn] = proxy.items
            
            # Bindings
            btn.bind("<Button-1>", lambda e, b=btn: self._toggle_menu(b))
            btn.bind("<Enter>", lambda e, b=btn: self._on_menu_hover(b))
            btn.bind("<Leave>", lambda e: self._on_menu_leave())
            
            self.menu_buttons.append(btn)
            return btn

        # 1. FILE
        create_menu_item("File", lambda m: (
            m.add_command("Reload tags", self.reload_codes),
            m.add_separator(),
            m.add_command("Exit", self._exit_app, "Alt+F4")
        ))
        # 2. EDIT
        create_menu_item("Edit", lambda m: (
            m.add_command("Tag groups", self.open_editor),
            m.add_command("Search", self.open_search, "Ctrl+F"),
            m.add_separator(),
            m.add_command("Preferences", self.open_preferences)
        ))
        # 3. VIEW
        create_menu_item("View", lambda m: (
            m.add_command("Font", self.select_font),
            m.add_separator(),
            m.add_command("Minimize to tray", self.minimize_to_tray)
        ))
        # 4. ABOUT / HELP
        def setup_help_menu(m):
            m.add_command("Help", self.open_help)
            m.add_separator()
            if sys.platform.startswith("linux"):
                m.add_command("Linux shortcut helper", self._show_linux_shortcut_helper_message)
                m.add_separator()
            m.add_command("Check for updates", self.check_for_updates_menu)
            m.add_separator()
            m.add_command("About", self.show_about)

        create_menu_item("   ?   ", setup_help_menu)

        # Reset if I click outside (only if NOT a menu widget)
        self.root.bind("<Button-1>", self._check_menu_click_outside, add="+")

    def _on_menu_leave(self):
        """Starts the timer for closing, but only if we are not already in a protected area."""
        if self._active_dropdown:
            if self._close_job: self.root.after_cancel(self._close_job)
            # Increase the time slightly to give room for movement
            self._close_job = self.root.after(500, self._close_dropdown)

    def _cancel_close(self, e=None):
        """Cancel any pending close operation."""
        if self._close_job:
            self.root.after_cancel(self._close_job)
            self._close_job = None

    def _toggle_menu(self, btn):
        self._cancel_close() # Immediate protection
        if self._active_button == btn:
            self._close_dropdown()
            self._menu_active = False
        else:
            self._menu_active = True
            self._show_dropdown(btn)

    def _on_menu_hover(self, btn):
        if self._menu_active:
            self._cancel_close() # Prevents closing while moving between buttons
            self._show_dropdown(btn)

    def _show_dropdown(self, btn):
        # If the menu for this button is already active, just cancel the close
        if self._active_button == btn and self._active_dropdown:
            self._cancel_close()
            return
            
        self._close_dropdown()
        self._active_button = btn
        
        # Create dropdown window
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        self._active_dropdown = top
        
        # The menu itself must cancel the close when the mouse enters it
        top.bind("<Enter>", self._cancel_close)
        top.bind("<Leave>", lambda e: self._on_menu_leave())

        # Colors and Font
        theme = get_active_theme(self.config)
        p_bg = theme.get("panel")
        p_fg = theme.get("panel_fg")
        f = (self.config.get("font_family", "Calibri"), int(self.config.get("font_size", 10)))
        
        inner = tk.Frame(top, bg=p_bg, highlightthickness=1, highlightbackground=theme.get("fg"))
        inner.pack(fill="both", expand=True)
        
        # Recursive binding to cancel close on every part of the menu
        inner.bind("<Enter>", self._cancel_close)

        items = self._menu_data[btn]
        for item in items:
            if item["label"] == "---":
                tk.Frame(inner, height=1, bg=theme.get("fg"), pady=2).pack(fill="x", padx=5)
                continue
            
            lbl_text = item["label"]
            if item["accel"]: lbl_text += f"   ({item['accel']})"
            
            l = tk.Label(inner, text=lbl_text, bg=p_bg, fg=p_fg, font=f, 
                         padx=20, pady=6, anchor="w", cursor="hand2")
            l.pack(fill="x")
            
            # Each row actively cancels the close timer
            l.bind("<Enter>", lambda e, w=l: (self._cancel_close(), w.configure(bg="#0078d7", fg="white")))
            l.bind("<Leave>", lambda e, w=l: w.configure(bg=p_bg, fg=p_fg))
            l.bind("<Button-1>", lambda e, cmd=item["command"]: self._exec_menu_cmd(cmd))

        # Positioning: OVERLAP of 2px to eliminate dead zones
        self.root.update_idletasks()
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height() - 2
        top.geometry(f"+{x}+{y}")
        
        # Final protection: after showing, cancel any spurious timers again
        self.root.after(10, self._cancel_close)

    def _exec_menu_cmd(self, cmd):
        self._close_dropdown()
        self._menu_active = False
        self._block_focus_out = True
        if cmd:
            self.root.after(10, cmd)
            self.root.after(1000, lambda: setattr(self, "_block_focus_out", False))

    def _close_dropdown(self):
        if self._active_dropdown:
            try: self._active_dropdown.destroy()
            except: pass
            self._active_dropdown = None
        self._active_button = None
        self._close_job = None

    def _check_menu_click_outside(self, event):
        if not self._menu_active: return
        
        # If I click on the menu bar or the dropdown, DO NOT close
        w = event.widget
        if w in self.menu_buttons or w == self.menubar_frame:
            return
            
        # Check if the clicked widget is inside the active dropdown
        if self._active_dropdown:
            try:
                if str(w).startswith(str(self._active_dropdown)):
                    return
            except: pass

        # If we are here, the click is truly "outside"
        self._close_dropdown()
        self._menu_active = False

    # ---------------- UI ----------------
    def build_ui(self):
        # --- TOP PANEL ---
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=6, pady=6)

        tk.Label(top, text="Code:").pack(side="left")

        self.code_var = tk.StringVar()
        self._trace_id = self.code_var.trace_add("write", self.filter_codes)

        self.entry = ttk.Combobox(top, textvariable=self.code_var, width=10)
        self.entry.pack(fill="x", expand=True, side="left", padx=(4, 4))
        
        # Prevents fading when opening the dropdown
        self.entry.bind("<Button-1>", lambda e: setattr(effects, "fade_away", False))
        self.entry.bind("<<ComboboxSelected>>", lambda e: self.root.after(100, self._restore_fade_away))

        self.entry.bind("<Return>", self.apply_code)
        self.entry.bind("<Down>", self.focus_list)
        self.entry.bind("<Up>", self.show_history_menu_keyboard)
        self.entry.bind("<Escape>", self.clear_input)
        self.entry.bind("<Button-3>", self.show_history_menu)
        self.entry.bind("<Menu>", self.show_history_menu_keyboard)
        self.entry.bind("<Shift-F10>", self.show_history_menu_keyboard)
        self.root.bind_all("<Menu>", self._on_global_menu_key, add="+")
        self.root.bind_all("<Shift-F10>", self._on_global_menu_key, add="+")
        self.root.bind_all("<KeyPress>", self._on_global_keypress, add="+")

        self.apply_button = tk.Button(top, text="Apply", command=self.apply_code, width=6)
        self.apply_button.pack(side="right")

        # --- PANED WINDOW ---
        self.paned = tk.PanedWindow(self.root, orient="vertical", sashrelief="raised")
        self.paned.pack(fill="both", expand=True, padx=6, pady=6)

        # --- UPPER PANEL ---
        upper_frame = tk.Frame(self.paned)

        list_frame = tk.Frame(upper_frame)
        list_frame.pack(fill="both", expand=True)

        self.code_list = tk.Listbox(list_frame, height=4)
        self.code_list.bind("<Motion>", self._on_list_motion)
        self.code_list.bind("<Leave>", self._on_list_leave)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.code_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.code_list.pack(fill="both", expand=True, side="left")
        self.code_list.config(yscrollcommand=scrollbar.set)

        self.code_list.bind("<<ListboxSelect>>", self.update_preview)
        self.code_list.bind("<Double-Button-1>", self.apply_from_list)
        self.code_list.bind("<Return>", self.apply_from_list)
        self.code_list.bind("<Button-3>", self.show_context_menu)

        # Preview header
        preview_header = tk.Frame(upper_frame, height=28)
        preview_header.pack(fill="x")
        preview_header.pack_propagate(False)

        self.preview_label = tk.Label(preview_header, text="Tag preview", anchor="w", pady=4)
        self.preview_label.pack(side="left", fill="x", expand=True)

        self._load_icons()
        symbol = self.collapse_symbol if self.preview_expanded else self.expand_symbol

        self.toggle_button = tk.Button(
            preview_header,
            text=symbol,
            command=self.toggle_preview,
            width=2,
            height=1,
            pady=2,
            bd=0
        )
        self.toggle_button.pack(side="right", padx=(4, 0))

        Tooltip(self.toggle_button, "Expand/collapse tag preview")

        # Fixed minimum height for upper panel
        self.MIN_UPPER = 160
        self.paned.add(upper_frame, minsize=self.MIN_UPPER)

        # --- LOWER PANEL (PREVIEW) ---
        self.preview_frame = tk.Frame(self.paned)

        preview_inner = tk.Frame(self.preview_frame)
        preview_inner.pack(fill="both", expand=True)

        self.preview = tk.Listbox(preview_inner, height=4)
        scrollbar_preview = ttk.Scrollbar(preview_inner, orient="vertical", command=self.preview.yview)
        scrollbar_preview.pack(side="right", fill="y")
        self.preview.pack(fill="both", expand=True, side="left")
        self.preview.config(yscrollcommand=scrollbar_preview.set)

        # Make preview read-only to mouse clicks
        self.preview.bind("<Button-1>", lambda e: "break")

        if self.preview_expanded:
            self.paned.add(self.preview_frame, minsize=0)
        else:
            self.paned.add(self.preview_frame, minsize=0)
            self.paned.forget(self.preview_frame)

        # --- CONTEXT MENU ---
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Use", command=self.context_use)
        self.context_menu.add_command(label="Edit", command=self.context_edit)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.context_delete)

    def on_close(self):
        """Handle window close, saving geometry."""
        self.save_geometry()
        self.root.destroy()

    def _on_list_motion(self, event):
        """Show tooltip with tag preview when hovering over a code."""
        index = self.code_list.nearest(event.y)

        # Out of bounds → hide tooltip
        if index < 0 or index >= self.code_list.size():
            self._hide_list_tooltip()
            self._list_tooltip_last_index = None
            return

        # Same row → do nothing
        if self._list_tooltip_last_index == index:
            # Update position only
            if self._list_tooltip_window:
                self._list_tooltip_window.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            return

        self._list_tooltip_last_index = index
        code = self.code_list.get(index)
        tags = self.codes.get(code, [])

        if not tags:
            self._hide_list_tooltip()
            return

        # Build preview text
        lines = [f"{t['key']} = {t['value']}" for t in tags]
        text = "\n".join(lines)

        # Show tooltip near cursor
        self._show_list_tooltip(event.x_root + 10, event.y_root + 10, text)

    def _on_list_leave(self, event):
        """Hide tooltip when leaving the listbox."""
        self._hide_list_tooltip()
        self._list_tooltip_last_index = None

    def _on_preferences_close(self):
        form = getattr(self, "_preferences_form", None)
        self._preferences_form = None
        if form is not None:
            try:
                form.destroy()
            except Exception:
                pass

    def _show_list_tooltip(self, x, y, text):
        self._hide_list_tooltip()

        tw = tk.Toplevel(self.code_list)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)  # required because main window is topmost

        label = tk.Label(
            tw,
            text=text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 8)
        )
        label.pack(ipadx=4, ipady=2)

        self._list_tooltip_window = tw

    def _hide_list_tooltip(self):
        """Destroy tooltip window if present."""
        if self._list_tooltip_window is not None:
            try:
                self._list_tooltip_window.destroy()
            except:
                pass
        self._list_tooltip_window = None

    def _load_icons(self):
        """Initialize expand/collapse symbols for the preview toggle button."""
        self.expand_symbol = "▼"
        self.collapse_symbol = "▲"
        self.expand_image = None
        self.collapse_image = None

    # ---------------- TOGGLE PREVIEW ----------------
    def toggle_preview(self):
        self.preview_expanded = not self.preview_expanded
        self.toggle_button.config(
            text=self.collapse_symbol if self.preview_expanded else self.expand_symbol
        )

        if not self.preview_expanded:
            self._collapse_preview()
        else:
            self._expand_preview()

    def _collapse_preview(self):
        self.root.update_idletasks()

        # Capture current upper pane height once, clamp to minimum
        try:
            self.upper_height = self.paned.sash_coord(0)[1]
        except:
            self.upper_height = self.MIN_UPPER

        self.upper_height = max(self.upper_height, self.MIN_UPPER)

        # Remove preview panel
        try:
            self.paned.forget(self.preview_frame)
        except:
            pass

        # Fix upper pane minimum height so it does not shrink
        try:
            self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
        except:
            pass

        # Optionally adjust window height to match upper pane
        w = self.root.winfo_width()
        self.root.geometry(f"{w}x{self.upper_height}")

        self.save_config()

    def _expand_preview(self):
        self.root.update_idletasks()

        # Fallback if upper_height was never set
        if self.upper_height is None:
            try:
                self.upper_height = self.paned.sash_coord(0)[1]
            except:
                self.upper_height = self.MIN_UPPER

        self.upper_height = max(self.upper_height, self.MIN_UPPER)
        self.preview_height = max(160, self.preview_height)

        # Re-add preview panel if missing
        if self.preview_frame not in self.paned.panes():
            try:
                self.paned.add(self.preview_frame, minsize=0)
            except:
                pass

        self.root.update_idletasks()

        # Place sash so upper pane has fixed height
        try:
            self.paned.sash_place(0, 0, self.upper_height)
        except:
            pass

        try:
            self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
        except:
            pass

        # Adjust window height to match saved layout
        w = self.root.winfo_width()
        total_h = self.upper_height + self.preview_height
        self.root.geometry(f"{w}x{total_h}")

        self.root.update_idletasks()
        try:
            self.preview_height = max(160, self.preview_frame.winfo_height())
        except:
            self.preview_height = 160

        self.save_config()

    def _restore_panes_layout(self):
        """
        Restore the split layout after window creation, using saved heights.
        """
        self.root.update_idletasks()

        # Ensure minimum upper height
        if self.upper_height is None:
            try:
                self.upper_height = self.paned.sash_coord(0)[1]
            except:
                self.upper_height = self.MIN_UPPER

        self.upper_height = max(self.upper_height, self.MIN_UPPER)
        self.preview_height = max(160, self.preview_height)

        if not self.preview_expanded:
            # Collapsed: ensure preview is removed and upper pane fixed
            try:
                self.paned.forget(self.preview_frame)
            except:
                pass
            try:
                self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
            except:
                pass
            w = self.root.winfo_width()
            self.root.geometry(f"{w}x{self.upper_height}")
            self.save_config()
            return

        # Expanded: ensure preview is present
        if self.preview_frame not in self.paned.panes():
            try:
                self.paned.add(self.preview_frame, minsize=0)
            except:
                pass

        self.root.update_idletasks()

        # Place sash so upper pane has fixed height
        try:
            self.paned.sash_place(0, 0, self.upper_height)
        except:
            pass

        try:
            self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
        except:
            pass

        # Adjust window height to match saved layout
        w = self.root.winfo_width()
        total_h = self.upper_height + self.preview_height
        self.root.geometry(f"{w}x{total_h}")

        self.root.update_idletasks()
        try:
            self.preview_height = max(160, self.preview_frame.winfo_height())
        except:
            self.preview_height = 160

        self.save_config()

    # ---------------- CONTEXT MENU ----------------
    def show_context_menu(self, event):
        index = self.code_list.nearest(event.y)
        if index < 0:
            return
        self.code_list.selection_clear(0, tk.END)
        self.code_list.selection_set(index)
        self.update_preview()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def show_about(self):
        from forms.about_form import AboutForm
        effects.fade_away = False
        AboutForm(self.root, self.config)
        self.root.after(1500, self._restore_fade_away)

    def open_help(self):
        """Open the user guide markdown file in the default browser."""
        effects.fade_away = False
        try:
            from pathlib import Path
            import subprocess
            
            help_file = resource_path("resources/doc/josm_tagger.md")
            file_url = Path(help_file).as_uri()
            
            # Try to open with Firefox explicitly on all platforms
            try:
                if sys.platform.startswith("win"):
                    subprocess.Popen(["firefox", file_url])
                else:  # Linux/Mac
                    subprocess.Popen(["firefox", file_url])
            except FileNotFoundError:
                # Firefox not found, fallback to default browser
                open_url_in_default_browser(file_url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open help file:\n{e}", parent=self.root)
        finally:
            self.root.after(1500, self._restore_fade_away)

    def context_use(self):
        self.apply_from_list()

    def context_edit(self):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        self.open_editor(code)

    def context_delete(self):
        import tkinter.messagebox as messagebox
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        confirm = messagebox.askyesno("Delete", f"Delete code '{code}'?")
        if not confirm:
            return
        if code in self.codes:
            del self.codes[code]
            from codes_manager import save_codes
            save_codes(self.codes)
            self.update_list()
            self.preview.delete(0, tk.END)

    def _restore_fade_away(self):
        effects.fade_away = True

    # ---------------- THEME ----------------
    def apply_theme(self):
        """Apply the active theme to compatible Tk widgets."""
        # Use the centralized theme application from effects.py
        apply_theme_colors(self.root, self.config)
        
        # Update main_form's bg_color and fg_color attributes
        theme = get_active_theme(self.config)
        self.bg_color = theme.get("bg", "#2b2b2b")
        self.fg_color = theme.get("fg", "#ffffff")
        self.fade_duration_ms = int(self.config.get("behaviour", {}).get("fade_duration_ms", 300)) # Update fade duration

    def _apply_runtime_theme(self):
        # Reload config to get latest theme settings
        self.config = load_config() 
        self.apply_theme() # Re-apply theme immediately

        # Apply theme to any open Toplevel windows (like preferences, editor, etc.)
        for child in self.root.winfo_children():
            try:
                if isinstance(child, tk.Toplevel):
                    effects.apply_theme_colors(child, self.config)
                    effects.apply_background_picture(child, self.config)
            except Exception:
                pass

    # ---------------- FONT ----------------
    def apply_font(self):
        f = (
            self.config.get("font_family", "Segoe UI"),
            int(self.config.get("font_size", 10))
        )
        self.root.option_add("*Font", f)

        def apply(widget):
            try:
                widget.configure(font=f)
            except:
                pass
            for c in widget.winfo_children():
                apply(c)

        apply(self.root)

    def select_font(self):
        effects.fade_away = False
        FontSelectorForm(self.root, self.config, self.apply_font_config)
        self.root.after(1500, self._restore_fade_away)

    def apply_font_config(self, new_config):
        self.config = new_config
        save_config(self.config)
        self.apply_font()

    # ---------------- HOTKEY ----------------
    def register_hotkey(self):
        hotkey_str = self.config.get("hotkey", "ctrl+0")
        self._linux_hotkey_spec = hotkey_str

        if sys.platform.startswith("linux"):
            start_linux_hotkeys(self._queue_hotkey_trigger, hotkey_str)
            print(f"Hotkey registration requested (Linux): {hotkey_str}")
            return

        start_hotkeys(self._queue_hotkey_trigger, hotkey_str)
        print(f"Hotkey registration requested: {hotkey_str}")

    def _queue_hotkey_trigger(self):
        try:
            self._hotkey_events.put_nowait(True)
        except Exception:
            pass

    def _linux_shortcut_helper_content(self):
        socket_path = str(INSTANCE_SOCKET_PATH or (Path.home() / ".josm_tagger_socket"))
        return f"""#!/bin/sh
set -eu

SOCKET_PATH="{socket_path}"

if [ ! -S "$SOCKET_PATH" ]; then
  exit 1
fi

python3 - "$SOCKET_PATH" <<'PY'
import socket
import sys

sock_path = sys.argv[1]
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(0.25)
sock.connect(sock_path)
sock.sendall(b"RESTORE\\n")
try:
    sock.shutdown(socket.SHUT_WR)
except OSError:
    pass
sock.close()
PY
"""

    def _ensure_linux_shortcut_helper(self):
        if not sys.platform.startswith("linux"):
            return

        helper_path = self._linux_shortcut_helper_path
        helper_content = self._linux_shortcut_helper_content()
        needs_message = False

        try:
            current = helper_path.read_text(encoding="utf-8") if helper_path.exists() else None
            if current != helper_content:
                helper_path.write_text(helper_content, encoding="utf-8")
                needs_message = True
            helper_path.chmod(0o755)
        except Exception as e:
            print(f"Warning: could not create Linux shortcut helper {helper_path}: {e}")
            return

        updates_cfg = self.config.setdefault("linux", {})
        if not updates_cfg.get("shortcut_helper_notice_shown"):
            needs_message = True
            updates_cfg["shortcut_helper_notice_shown"] = True
            save_config(self.config)

        if needs_message:
            self.root.after(200, self._show_linux_shortcut_helper_message)

    def _show_linux_shortcut_helper_message(self):
        helper_path = self._linux_shortcut_helper_path
        messagebox.showinfo(
            "Linux shortcut helper",
            (
                "JOSM Tagger has created a helper for quick launching:\n\n"
                f"  {helper_path}\n\n"
                "Set up your system shortcut to run that file.\n"
                "Recommended flow:\n"
                "1. Start JOSM Tagger once with the normal launcher.\n"
                "2. Bind the system shortcut to ~/josmtagger.sh.\n"
                "3. From then on, the shortcut reactivates the already open instance\n"
                "   and does not create a new one."
            ),
            parent=self.root,
        )

    def _start_linux_instance_server(self):
        if not sys.platform.startswith("linux"):
            return
        if LinuxInstanceServer is None:
            debug_print("Linux instance restore IPC unavailable.", cfg=self.config)
            return
        try:
            self._linux_instance_server = LinuxInstanceServer(
                self._queue_hotkey_trigger
            ).start()
            debug_print("Linux instance restore IPC: active", cfg=self.config)
        except Exception as e:
            debug_print(f"Warning: Linux instance restore IPC failed: {e}", cfg=self.config)

    def _process_hotkey_events(self):
        if self._is_exiting:
            return

        triggered = False
        while True:
            try:
                self._hotkey_events.get_nowait()
                triggered = True
            except queue.Empty:
                break

        if triggered:
            self.hotkey_trigger()

        self.root.after(100, self._process_hotkey_events)

    def hotkey_trigger(self):
        self.restore_main_form()

    def restore_main_form(self):
        if self.tray_running or str(self.root.state()) in ("withdrawn", "iconic"):
            self._on_tray_restore()
            return

        self.root.deiconify()
        self.root.update_idletasks()
        self.root.lift()
        self.root.attributes("-topmost", True)

        if not self._should_keep_form_visible():
            self.root.after(25, lambda: self.root.attributes("-topmost", False))
        
        # Aggressive focus: multiple attempts with increasing delays for .exe compatibility
        self.root.after(0, self.win_mgmt.force_focus)
        self.root.after(5, self.win_mgmt.force_focus)
        self.root.after(15, self.win_mgmt.force_focus)
        self.root.after(30, self.win_mgmt.force_focus)
        self.root.after(60, self.win_mgmt.force_focus)
        self.root.after(100, self.win_mgmt.force_focus)
        self.root.after(150, self.win_mgmt.force_focus)
        
        self.flash_window()

    def focus_input(self):
        self.restore_main_form()

    def _activate_entry_for_next_command(self):
        """Put focus back on the command textbox and prepare it for typing."""
        try:
            if self.entry is None or not self.entry.winfo_exists():
                return
            self.entry.focus_set()
            self.entry.icursor(tk.END)
            self.entry.select_range(0, tk.END)
        except Exception:
            pass

    def _force_focus(self):
        self.win_mgmt.force_focus()

    def flash_window(self):
        try:
            self.root.configure(highlightthickness=3, highlightbackground="red")
            self.root.after(200, lambda: self.root.configure(highlightthickness=0))
        except:
            pass

    # ---------------- CODES LOGIC ----------------
    def update_list(self):
        """Rebuild the Listbox using alphabetical order, but DO NOT touch the combobox."""
        self.code_list.delete(0, tk.END)

        # Alphabetical list for the Listbox
        sorted_values = sorted(self.codes)

        for c in sorted_values:
            self.code_list.insert(tk.END, c)

        # filtered_codes = alphabetical (OK)
        self.filtered_codes = sorted_values

    def filter_codes(self, *args):
        text = self.code_var.get().lower()

        # Filter codes alphabetically (Listbox view)
        self.filtered_codes = sorted(
            [c for c in self.codes if c.lower().startswith(text)]
        )

        # Rebuild Listbox
        self.code_list.delete(0, tk.END)
        for c in self.filtered_codes:
            self.code_list.insert(tk.END, c)

        # Dropdown combobox: live suggestions startswith (no MRU)
        if text:
            self.entry["values"] = self.filtered_codes
        else:
            self.entry["values"] = sorted(self.codes.keys())

        # Update preview with the first visible code
        if self.filtered_codes:
            first = self.filtered_codes[0]
            self._render_preview(first)
        else:
            self.preview.delete(0, tk.END)

    def focus_list(self, event):
        if self.code_list.size() == 0:
            return
        self.code_list.focus_set()
        self.code_list.selection_set(0)
        self.update_preview()

    def update_preview(self, event=None):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        self._render_preview(code)

    # ---------------- APPLY ----------------
    def apply_from_list(self, event=None):
        self.allow_minimize = False
        self.allow_fade = False

        sel = self.code_list.curselection()
        if not sel:
            self.allow_minimize = True
            self.allow_fade = True
            return

        code = self.code_list.get(sel[0])
        self.send(code)

    def apply_code(self, event=None):
        """Apply the typed code or the selected one."""
        self.allow_minimize = False  # block minimize during sending
        self.allow_fade = False  # block fade during sending

        typed = self.code_var.get().strip().lower()

        # Case 1: typed valid code
        if typed in self.codes:
            self.send(typed)
            return

        # Case 2: selected code from list
        sel = self.code_list.curselection()
        if sel:
            code = self.code_list.get(sel[0])
            self.send(code)
            return

        # Case 3: invalid → restore flags
        self.allow_minimize = True
        self.allow_fade = True

    def _promote_code(self, code):
        self._update_command_history(code)

    def _reset_input(self):
        self.code_var.set("")
        self.preview.delete(0, tk.END)

    def clear_input(self, event=None):
        self._reset_input()

    def _show_generic_tags_warning(self):
        from tkinter import messagebox

        previous_topmost = None
        try:
            previous_topmost = bool(self.root.attributes("-topmost"))
        except Exception:
            previous_topmost = None

        try:
            self.root.deiconify()
        except Exception:
            pass

        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.update_idletasks()
        except Exception:
            pass

        try:
            messagebox.showwarning(
                "Warning",
                "Tags with generic values were added. "
                "Please review the edited element manually before uploading.",
                parent=self.root,
            )
        finally:
            if previous_topmost is not None:
                try:
                    self.root.attributes("-topmost", previous_topmost)
                except Exception:
                    pass

    def _should_keep_form_visible(self):
        beh = self.config.get("behaviour", {})
        return beh.get("on_apply", "keep_visible") == "keep_visible"

    def _show_josm_remote_control_warning(self, details=None):
        message = (
            "JOSM did not accept the Remote Control request.\n\n"
            "Make sure JOSM is running and Remote Control is enabled, then try again later."
        )
        if details:
            message += f"\n\nDetails: {details}"

        messagebox.showwarning(
            "JOSM unavailable",
            message,
            parent=self.root,
        )

    def send(self, code):

        self._sending_in_progress = True
        self._block_focus_out = True
        self._render_preview(code)
        sent_ok = False
        send_error = None
        send_aborted = False

        def worker():
            nonlocal sent_ok, send_error, send_aborted
            # Conditional import of pyautogui for Windows only
            if sys.platform.startswith("win"):
                import pyautogui
                pyautogui.FAILSAFE = False
                control_method = self.config.get("josm_control_method")
            else:
                # On Linux, force "Remote Control" and skip pyautogui
                control_method = "remote_control"
                debug_print("Running on Linux, forcing JOSM control method to 'Remote Control'.", cfg=self.config)

            debug_print('Send Worker started', cfg=self.config)

            # --- Normalize tags into a dict ---
            raw_tags = self.codes.get(code, {})
            tags_dict = {}

            if isinstance(raw_tags, dict):
                tags_dict = raw_tags
            elif isinstance(raw_tags, list):
                for item in raw_tags:
                    if isinstance(item, dict) and "key" in item and "value" in item:
                        tags_dict[item["key"]] = item["value"]
                    elif isinstance(item, (list, tuple)) and len(item) == 2:
                        tags_dict[item[0]] = item[1]

            # Convert to list of dicts
            tags_list = [{"key": k, "value": v} for k, v in tags_dict.items()]

            # --- Detect generic values ---
            generic_found = False
            for item in tags_list:
                v = item["value"]
                if isinstance(v, str):
                    stripped = v.strip()
                    if stripped and (len(set(stripped)) == 1 and not stripped[0].isalnum()):
                        generic_found = True
                    elif stripped and all(not ch.isalnum() for ch in stripped):
                        generic_found = True

            generic_warning_shown = False
            if generic_found and control_method == "remote_control":
                self._show_generic_tags_warning()
                generic_warning_shown = True

            # --- Send tags ---
            try:
                if not tags_list:
                    debug_print("WARNING: tags_list empty, nothing to send", cfg=self.config)
                    self._sending_in_progress = False
                    self.allow_minimize = True
                    self.allow_fade = True
                    self._block_focus_out = False
                    send_aborted = True
                    return

                sent_ok = send_tags(
                    tags_list,
                    main_root=self.root,
                    control_method=control_method, # Use the determined control_method
                )
            except Exception as e:
                sent_ok = False
                send_error = e
                debug_print(f"Send failed: {e}", cfg=self.config)

            finally:

                # HERE: done() sees generic_found and tags_list because it's in the same scope
                def done():
                    if send_aborted:
                        return

                    if sent_ok:
                        self._promote_code(code)
                        self._reset_input()

                        if generic_found and not generic_warning_shown:
                            self._show_generic_tags_warning()

                        try:
                            focus_josm(main_root=self.root)
                        except Exception as e:
                            debug_print(f"Could not refocus JOSM after send: {e}", cfg=self.config)
                    else:
                        if control_method == "remote_control":
                            details = str(send_error) if send_error else None
                            self._show_josm_remote_control_warning(details=details)

                    self._sending_in_progress = False
                    self.allow_minimize = True
                    self.allow_fade = True

                    # Minimize ONLY after send is done
                    beh = self.config.get("behaviour", {})
                    if beh.get("on_apply") == "minimize_to_tray":
                        hide_delay = int(beh.get("hide_delay", 150))
                        if control_method == "remote_control":
                            hide_delay = min(hide_delay, int(beh.get("remote_control_hide_delay", 50)))
                        self.root.after(hide_delay, self._fade_then_minimize_to_tray)
                        self.root.after(hide_delay + self.fade_duration_ms + 100, lambda: setattr(self, "_block_focus_out", False))
                    else:
                        self._block_focus_out = False

                self.root.after(0, done)

            debug_print(f"Applying code '{code}'", cfg=self.config)
        # threading.Thread(target=worker, daemon=True).start()
        worker()
        pass

    def _render_preview(self, code):
        """Render the tag preview for a given code."""
        self.preview.delete(0, tk.END)

        tags = self.codes.get(code, [])
        for t in tags:
            self.preview.insert(tk.END, f"{t['key']} = {t['value']}")

    # ---------------- OTHER ----------------
    def reload_codes(self):
        self.codes = load_codes()
        self.update_list()
        self.entry["values"] = sorted(self.codes.keys())

    def _init_command_history(self):
        self.config.setdefault("command_history_items", 20)
        raw_history = self.config.get("command_history", [])
        if not isinstance(raw_history, list):
            raw_history = []
        self.command_history = []
        for item in raw_history:
            if isinstance(item, str) and item.strip():
                self.command_history.append(item.strip())
        self.history_menu = tk.Menu(self.root, tearoff=0)

    def _get_history_limit(self):
        try:
            return max(1, int(self.config.get("command_history_items", 20)))
        except Exception:
            return 20

    def _update_command_history(self, code):
        if not isinstance(code, str):
            return
        code = code.strip()
        if not code:
            return

        self.command_history = [c for c in self.command_history if c != code]
        self.command_history.insert(0, code)
        self.command_history = self.command_history[: self._get_history_limit()]
        self.config["command_history"] = list(self.command_history)
        save_config(self.config)

    def show_history_menu(self, event):
        if self.history_menu is None:
            self.history_menu = tk.Menu(self.root, tearoff=0)

        self.history_menu.delete(0, tk.END)
        added = set()
        for code in self.command_history:
            if code in added:
                continue
            added.add(code)
            self.history_menu.add_command(
                label=code,
                command=lambda c=code: self._select_history_code(c)
            )

        if not added:
            self.history_menu.add_command(label="(empty)", state="disabled")

        try:
            self.history_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def show_history_menu_keyboard(self, _event=None):
        self.entry.update_idletasks()
        x = self.entry.winfo_rootx() + 12
        y = self.entry.winfo_rooty() + self.entry.winfo_height() - 2

        class _Evt:
            pass

        evt = _Evt()
        evt.x_root = x
        evt.y_root = y
        self.show_history_menu(evt)
        return "break"

    def _focus_is_on_code_combobox(self):
        try:
            focused = self.root.focus_get()
            if focused is None:
                return False
            focused_path = str(focused)
            entry_path = str(self.entry)
            return focused_path == entry_path or focused_path.startswith(entry_path + ".")
        except Exception:
            return False

    def _on_global_menu_key(self, event=None):
        if not self._focus_is_on_code_combobox():
            return None
        return self.show_history_menu_keyboard(event)

    def _on_global_keypress(self, event=None):
        if sys.platform.startswith("linux") and linux_hotkey_matches(event, getattr(self, "_linux_hotkey_spec", "ctrl+0")):
            self._queue_hotkey_trigger()
            return "break"

        if not self._focus_is_on_code_combobox():
            return None
        keysym = str(getattr(event, "keysym", "") or "")
        keycode = int(getattr(event, "keycode", -1))
        normalized = keysym.lower()
        if (
            normalized in ("menu", "app", "apps")
            or "menu" in normalized
            or "app" in normalized
            or keycode in (93, 135)
        ):
            return self.show_history_menu_keyboard(event)
        return None

    def _select_history_code(self, code):
        self.code_var.set(code)
        self.entry.focus_set()
        self.entry.icursor(tk.END)

    def open_editor(self, code=None):
        effects.fade_away = False
        TagEditorForm(
            self.root,
            self.codes,
            on_save_callback=self.reload_codes,
            config=self.config,
            preload_code=code
        )
        self.root.after(1500, self._restore_fade_away)

    def open_preferences(self):
        if getattr(self, "_preferences_form", None) is not None:
            try:
                self._preferences_form.lift()
                return
            except:
                self._preferences_form = None

        from forms.options_form import OptionsForm
        effects.fade_away = False
        self._preferences_form = OptionsForm(
            self.root,
            self.config,
            on_theme_toggle=self._apply_runtime_theme,
        )
        self._preferences_form.protocol("WM_DELETE_WINDOW", self._on_preferences_close)
        self.root.after(1500, self._restore_fade_away)

    def open_search(self, event=None):
        from forms.search_form import SearchForm
        effects.fade_away = False
        SearchForm(self, self.codes, self.config)
        self.root.after(1500, self._restore_fade_away)

    # ---------------- SYSTEM TRAY SUPPORT (pystray) ----------------
    def minimize_to_tray(self):
        """Hides the window and starts the tray using pystray."""
        if self._is_exiting:
            return
        if self.allow_minimize:
            debug_print('main_form -> Minimize to tray', cfg=self.config)
            self._capture_current_normal_geometry()
            if not self.tray_running:
                self._start_tray_icon()

            # Disable fading ONLY here (pystray crashes if alpha changes)
            self.root.attributes("-alpha", 1.0)
            self.root.withdraw()
            self._notify_first_minimize_to_tray()
        else:
            debug_print('Minimize prevented. allow_minimize = False', cfg=self.config)

    def _resolve_appname(self):
        try:
            main_mod = sys.modules.get("__main__")
            if main_mod is not None and hasattr(main_mod, "appname"):
                return str(getattr(main_mod, "appname"))
        except Exception:
            pass
        try:
            from main import appname as appname_from_main
            return str(appname_from_main)
        except Exception:
            pass
        return self.root.title() or "Application"

    def _notify_first_minimize_to_tray(self):
        if self._tray_minimize_notice_shown:
            return
        if not self.tray_running or self.tray_icon is None:
            return

        app_name = self._resolve_appname()
        try:
            self.tray_icon.notify(f"{app_name} is minimized to tray", title=app_name)
            self._tray_minimize_notice_shown = True
        except Exception:
            pass

    def _resolve_appversion(self):
        try:
            main_mod = sys.modules.get("__main__")
            if main_mod is not None and hasattr(main_mod, "appversion"):
                return str(getattr(main_mod, "appversion"))
        except Exception:
            pass
        try:
            from main import appversion as appversion_from_main
            return str(appversion_from_main)
        except Exception:
            pass
        return "0.0.0"

    def _should_auto_check_for_updates(self):
        updates_cfg = self.config.setdefault("updates", {})
        updates_cfg.setdefault("auto_check", True)
        if not updates_cfg.get("auto_check", True):
            return False

        raw_last_check = updates_cfg.get("last_check_utc")
        if not raw_last_check:
            return True

        try:
            last_check = datetime.fromisoformat(raw_last_check)
        except Exception:
            return True

        now_utc = datetime.now(timezone.utc)
        if last_check.tzinfo is None:
            last_check = last_check.replace(tzinfo=timezone.utc)

        return (now_utc - last_check) >= timedelta(hours=24)

    def _mark_update_check_now(self):
        updates_cfg = self.config.setdefault("updates", {})
        updates_cfg["last_check_utc"] = datetime.now(timezone.utc).isoformat()
        save_config(self.config)

    def _auto_check_for_updates(self):
        if not self._should_auto_check_for_updates():
            return
        print("Startup update check: starting")
        self._perform_update_check(interactive=False)

    def check_for_updates_menu(self):
        self._perform_update_check(interactive=True)

    def _perform_update_check(self, interactive):
        if self._update_check_in_progress:
            return

        self._update_check_in_progress = True
        self._mark_update_check_now()
        current_version = self._resolve_appversion()

        def worker():
            result = check_for_updates(current_version)

            def finish():
                self._update_check_in_progress = False
                status = result.get("status")

                if status == "error":
                    if interactive:
                        messagebox.showwarning(
                            "Update check failed",
                            "Could not contact GitHub to check for updates.\n\n"
                            f"Details: {result.get('message', 'Unknown error')}",
                            parent=self.root,
                        )
                    return

                if status == "no_published_versions":
                    if interactive:
                        messagebox.showinfo(
                            "No published updates",
                            "No GitHub releases or tags are currently published for this repository.\n\n"
                            "Publish a release or a version tag to enable update detection.",
                            parent=self.root,
                        )
                    return

                if status == "up_to_date":
                    if interactive:
                        messagebox.showinfo(
                            "Up to date",
                            f"You are already using the latest published version ({result.get('latest_version')}).",
                            parent=self.root,
                        )
                    return

                if status == "update_available":
                    latest_version = result.get("latest_version", "")
                    source = result.get("source", "release")
                    prompt = (
                        f"A newer version is available on GitHub.\n\n"
                        f"Installed: {current_version}\n"
                        f"Available: {latest_version}\n"
                        f"Source: {source}\n\n"
                        f"Open the download page now?"
                    )
                    should_open = messagebox.askyesno(
                        "Update available",
                        prompt,
                        parent=self.root,
                    )
                    if should_open:
                        open_url_in_default_browser(result.get("url"))
                elif status == "newer_than_available":
                    if interactive:
                        messagebox.showinfo(
                            "Newer than available",
                            f"Your installed version ({current_version}) is newer than the latest published version ({result.get('latest_version')}).",
                            parent=self.root,
                        )

            self.root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _on_main_window_close(self):
        beh = self.config.get("behaviour", {})
        action = beh.get("on_close", "minimize_to_tray")
        if action == "exit_app":
            self._exit_app()
            return
        self.minimize_to_tray()

    def _fade_then_minimize_to_tray(self):
        self.win_mgmt.fade_then_minimize_to_tray()

    def _move_to_main_display(self):
        """Moves the main window to coordinates (40, 40) on the primary display."""
        confirm = messagebox.askyesno(
            "Move to main display",
            "Move the window to the main display?",
            parent=self.root,
        )
        if not confirm:
            return

        self.root.geometry(f"+40+40")
        self.restore_main_form() # Ensure it's visible and focused

    def _start_tray_icon(self):
        """Creates the tray icon using run_detached() from the GitHub version."""
        if self.tray_running:
            return

        icon_image = Image.open(resource_path("resources/josm_tagger.ico"))

        self.tray_icon = pystray.Icon(
            "josm_tagger",
            icon_image,
            "JOSM Tagger",
            menu=pystray.Menu(
                pystray.MenuItem("Show", self._on_tray_restore, default=True),
                pystray.MenuItem("Move to main display", self._move_to_main_display), # New option
                pystray.MenuItem("Exit", self._on_tray_exit)
            )
        )

        # On Windows backend, pystray triggers default action on single left click.
        # Override notify handler: restore only on double click, keep right click menu.
        try:
            from pystray._util import win32 as pystray_win32
            original_notify = self.tray_icon._message_handlers.get(pystray_win32.WM_NOTIFY)
            wm_lbutton_dblclk = getattr(pystray_win32, "WM_LBUTTONDBLCLK", 0x0203)

            def _notify_double_click_only(wparam, lparam):
                if lparam == wm_lbutton_dblclk:
                    self._on_tray_restore()
                    return 0
                if lparam == pystray_win32.WM_RBUTTONUP and callable(original_notify):
                    return original_notify(wparam, lparam)
                return 0

            self.tray_icon._message_handlers[pystray_win32.WM_NOTIFY] = _notify_double_click_only
        except Exception:
            pass

        self.tray_running = True
        self.tray_icon.run_detached()

    def _on_tray_restore(self, icon=None, item=None):
        # Block focus-out during entire restore
        self._block_focus_out = True

        self.root.deiconify()
        self.root.update_idletasks()
        self.root.lift()
        self.root.attributes("-topmost", True)

        if not self._should_keep_form_visible():
            self.root.after(50, lambda: self.root.attributes("-topmost", False))

        # Aggressive focus: multiple attempts with increasing delays for .exe compatibility
        self.root.after(0, self.win_mgmt.force_focus)
        self.root.after(5, self.win_mgmt.force_focus)
        self.root.after(15, self.win_mgmt.force_focus)
        self.root.after(30, self.win_mgmt.force_focus)
        self.root.after(60, self.win_mgmt.force_focus)
        self.root.after(100, self.win_mgmt.force_focus)
        self.root.after(150, self.win_mgmt.force_focus)

        # Non-blocking fade-in
        try:
            beh = self.config.get("behaviour", {})
            target = beh.get("transparency_active", 100) / 100
            duration = int(beh.get("fade_duration_ms", 300))
            current_alpha = float(self.root.attributes("-alpha"))

            if current_alpha < target - 0.01:
                self.fader.fade(
                    start_alpha=current_alpha,
                    end_alpha=target,
                    duration_ms=duration
                )
            else:
                self.root.attributes("-alpha", target)
        except Exception:
            self.root.attributes("-alpha", 1)

        # Unblock focus-out when window is stable
        self.root.after(500, lambda: setattr(self, "_block_focus_out", False))

    def _on_tray_exit(self, icon, item):
        self.root.after(0, self._exit_app)

    def _force_focus_on_entry(self):
        """Force focus on the textbox after restore."""
        self.win_mgmt.force_focus()

    def _on_focus_in(self, event=None):
        self.win_mgmt.on_focus_in(event)

    def _on_focus_out(self, event=None):
        self.win_mgmt.on_focus_out(event)

    def _prevent_maximize(self, event):
        self.win_mgmt.prevent_maximize(event)

    def _disable_maximize(self):
        self.win_mgmt.disable_maximize()

    def _exit_app(self):
        self._is_exiting = True
        self._capture_current_normal_geometry()
        if self._save_geometry_job is not None:
            try:
                self.root.after_cancel(self._save_geometry_job)
            except Exception:
                pass
            self._save_geometry_job = None
        self._flush_geometry_to_config()

        # Reload config updated from OptionsForm
        try:
            self.config = load_config()
        except Exception:
            pass  # in case of problems, at least we don't overwrite

        # Close the persistent tray icon, then terminate the UI
        try:
            if self.tray_icon is not None:
                self.tray_icon.visible = False
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            if self._linux_instance_server is not None:
                self._linux_instance_server.stop()
        except Exception:
            pass
        self.tray_running = False

        self.root.destroy()
