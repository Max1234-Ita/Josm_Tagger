import os
import sys
import copy
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import colorchooser, filedialog, messagebox

from config_manager import load_config, save_config
from effects import apply_background_picture, apply_theme_colors, get_active_theme


class OptionsForm(tk.Toplevel):
    """
    Application options window.

    - No option is applied or saved immediately.
    - All changes remain in self.temp_config until the user presses OK.
    - On OK: self.temp_config -> config.json (via save_config).
    - On Cancel or [X]: no changes, no save.
    """

    def __init__(self, master, config, on_theme_toggle=None):
        super().__init__(master)

        # --- CONFIGURATION ---
        # config is the global config passed by MainForm
        self.config = config
        self.on_theme_toggle = on_theme_toggle

        # Deep copy → working copy
        self.config_data = load_config()
        self.temp_config = copy.deepcopy(self.config_data)
        self._initial_dark_mode_enabled = bool(self.config_data.get("dark_theme_enabled", False))

        # Prevent resizing
        self.resizable(False, False)

        # Ensure new keys exist
        self._ensure_defaults()

        # --- FONT & SCALE ---
        self.font_family = self.config_data.get("font_family", "Calibri")
        self.font_size = int(self.config_data.get("font_size", 11))
        self.ui_scale = float(self.config_data.get("ui_scale", 1.0))

        # --- WINDOW ---
        self.title("Preferences")
        self._configure_window_style()
        self._apply_current_theme_to_form()
        apply_background_picture(self, self.config_data)

        # --- TK VARIABLES ---
        self._init_variables()
        vcmd = (self.register(self._validate_percent), "%P")
        self._percent_validator = vcmd

        # --- UI ---
        self._build_ui()

        # --- CLOSE EVENTS ---
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Initial focus
        self.transient(master)
        self.grab_set()
        self._place_near_pointer_with_parent_offset(master)
        self.focus_set()


    # --------------------------------------------------------------------- #
    #  CONFIG / DEFAULTS
    # --------------------------------------------------------------------- #

    def _ensure_defaults(self):
        theme = self.temp_config.setdefault("theme", {})
        theme.setdefault("bg", "#f0f0f0")
        theme.setdefault("panel", "#e4e6ea")
        theme.setdefault("fg", "#101010")
        theme.setdefault("picture", None)
        dark_theme = self.temp_config.setdefault("dark_theme", {})
        dark_theme.setdefault("bg", "#1e1f22")
        dark_theme.setdefault("panel", "#2a2e35")
        dark_theme.setdefault("fg", "#d8d8d8")
        dark_theme.setdefault("picture", None)
        self.temp_config.setdefault("dark_theme_enabled", False)

        behaviour = self.temp_config.setdefault("behaviour", {})
        behaviour.setdefault("on_focus_loss", "do_nothing")
        behaviour.setdefault("on_apply", "keep_visible")
        behaviour.setdefault("on_close", "minimize_to_tray")
        behaviour.setdefault("transparency_active", 100)
        behaviour.setdefault("transparency_faded", 35)
        behaviour.setdefault("hide_delay", 150)
        behaviour.setdefault("fade_delay", 120)

    # --------------------------------------------------------------------- #
    #  WINDOW STYLE
    # --------------------------------------------------------------------- #

    def _configure_window_style(self):
        # Topmost come gli altri form
        self.attributes("-topmost", True)

        # Toolwindow style (su Windows; ignorato altrove)
        try:
            self.attributes("-toolwindow", True)
        except Exception:
            pass

    def _monitor_workarea_from_point(self, x, y):
        if sys.platform.startswith("win"):
            try:
                import ctypes
                from ctypes import wintypes

                class POINT(ctypes.Structure):
                    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

                class RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", wintypes.LONG),
                        ("top", wintypes.LONG),
                        ("right", wintypes.LONG),
                        ("bottom", wintypes.LONG),
                    ]

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.DWORD),
                        ("rcMonitor", RECT),
                        ("rcWork", RECT),
                        ("dwFlags", wintypes.DWORD),
                    ]

                user32 = ctypes.windll.user32
                pt = POINT(int(x), int(y))
                monitor = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
                if monitor:
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                        return (
                            int(info.rcWork.left),
                            int(info.rcWork.top),
                            int(info.rcWork.right),
                            int(info.rcWork.bottom),
                        )
            except Exception:
                pass

        return 0, 0, int(self.winfo_screenwidth()), int(self.winfo_screenheight())

    def _clamp_to_monitor(self, x, y):
        self.update_idletasks()
        ww = max(1, int(self.winfo_width()))
        wh = max(1, int(self.winfo_height()))
        left, top, right, bottom = self._monitor_workarea_from_point(x, y)

        max_x = max(left, right - ww)
        max_y = max(top, bottom - wh)
        clamped_x = min(max(int(x), left), max_x)
        clamped_y = min(max(int(y), top), max_y)
        return clamped_x, clamped_y

    def _place_near_pointer_with_parent_offset(self, parent):
        self.update_idletasks()
        px = self.winfo_pointerx()
        py = self.winfo_pointery()
        ox = int(parent.winfo_width() * 0.30)
        oy = int(parent.winfo_height() * 0.30)
        x, y = self._clamp_to_monitor(px + ox, py + oy)
        self.geometry(f"+{x}+{y}")

    # --------------------------------------------------------------------- #
    #  SCALING HELPER
    # --------------------------------------------------------------------- #

    def _s(self, value):
        """Applica ui_scale a un valore intero."""
        return int(round(value * self.ui_scale))

    # --------------------------------------------------------------------- #
    #  TK VARIABLES
    # --------------------------------------------------------------------- #

    def _init_variables(self):
        self.dark_mode_var = tk.BooleanVar(value=bool(self.temp_config.get("dark_theme_enabled", False)))
        self._current_theme_key = "dark_theme" if self.dark_mode_var.get() else "theme"
        theme = self.temp_config[self._current_theme_key]
        behaviour = self.temp_config["behaviour"]

        # Appearance - Background
        self.bg_color_var = tk.StringVar(value=theme.get("bg", "#f0f0f0"))
        self.bg_picture_var = tk.StringVar(
            value=theme.get("picture") or ""
        )

        # Appearance - Foreground
        self.fg_color_var = tk.StringVar(value=theme.get("fg", "#101010"))
        self.panel_color_var = tk.StringVar(value=theme.get("panel", "#e4e6ea"))

        # Behaviour - On focus loss
        self.on_focus_loss_map = {
            "do_nothing": "Do nothing",
            "fade_out": "Fade out",
        }
        self.on_focus_loss_rev = {v: k for k, v in self.on_focus_loss_map.items()}
        current_ofl = behaviour.get("on_focus_loss", "do_nothing")
        self.on_focus_loss_var = tk.StringVar(
            value=self.on_focus_loss_map.get(current_ofl, "Do nothing")
        )

        # Behaviour - On apply
        self.on_apply_map = {
            "keep_visible": "Keep form visible",
            "minimize_to_tray": "Minimize to Tray",
        }
        self.on_apply_rev = {v: k for k, v in self.on_apply_map.items()}
        current_oa = behaviour.get("on_apply", "keep_visible")
        self.on_apply_var = tk.StringVar(
            value=self.on_apply_map.get(current_oa, "Keep form visible")
        )

        # Behaviour - On close
        self.on_close_map = {
            "minimize_to_tray": "Minimize to Tray",
            "exit_app": "Exit app",
        }
        self.on_close_rev = {v: k for k, v in self.on_close_map.items()}
        current_oc = behaviour.get("on_close", "minimize_to_tray")
        self.on_close_var = tk.StringVar(
            value=self.on_close_map.get(current_oc, "Minimize to Tray")
        )

        # Behaviour - Transparency
        # Limiti: 10–100 per evitare invisibilità
        ta = max(10, min(100, int(behaviour.get("transparency_active", 100))))
        tf = max(10, min(100, int(behaviour.get("transparency_faded", 35))))

        self.transparency_active_var = tk.IntVar(value=ta)
        self.transparency_faded_var = tk.IntVar(value=tf)

    def _ensure_theme_bucket(self, key):
        bucket = self.temp_config.setdefault(key, {})
        bucket.setdefault("bg", "#f0f0f0" if key == "theme" else "#1e1f22")
        bucket.setdefault("panel", "#e4e6ea" if key == "theme" else "#2a2e35")
        bucket.setdefault("fg", "#101010" if key == "theme" else "#d8d8d8")
        bucket.setdefault("picture", None)
        return bucket

    def _sync_theme_vars_to_bucket(self, key):
        bucket = self._ensure_theme_bucket(key)
        bucket["bg"] = self.bg_color_var.get().strip() or bucket.get("bg", "#f0f0f0")
        bucket["fg"] = self.fg_color_var.get().strip() or bucket.get("fg", "#101010")
        bucket["panel"] = self.panel_color_var.get().strip() or bucket.get("panel", bucket.get("bg", "#f0f0f0"))
        picture_val = self.bg_picture_var.get().strip()
        bucket["picture"] = picture_val if picture_val else None

    def _load_theme_vars_from_bucket(self, key):
        bucket = self._ensure_theme_bucket(key)
        self.bg_color_var.set(bucket.get("bg", "#f0f0f0"))
        self.fg_color_var.set(bucket.get("fg", "#101010"))
        self.panel_color_var.set(bucket.get("panel", bucket.get("bg", "#f0f0f0")))
        self.bg_picture_var.set(bucket.get("picture") or "")
        self.bg_color_preview.configure(bg=self.bg_color_var.get())
        self.fg_color_preview.configure(bg=self.fg_color_var.get())
        self.panel_color_preview.configure(bg=self.panel_color_var.get())

    def _on_dark_mode_toggle(self):
        self._sync_theme_vars_to_bucket(self._current_theme_key)
        self._current_theme_key = "dark_theme" if self.dark_mode_var.get() else "theme"
        self._load_theme_vars_from_bucket(self._current_theme_key)
        self.temp_config["dark_theme_enabled"] = bool(self.dark_mode_var.get())
        self.config["dark_theme_enabled"] = bool(self.dark_mode_var.get())
        self._apply_current_theme_to_form()
        if callable(self.on_theme_toggle):
            self.on_theme_toggle()

    def _apply_current_theme_to_form(self):
        theme = get_active_theme(self.config)
        bg = theme.get("bg", "#f0f0f0")
        panel = theme.get("panel", bg)
        fg = theme.get("fg", "#101010")

        # Tk widgets
        apply_theme_colors(self, self.config)
        apply_background_picture(self, self.config)

        # ttk widgets (OptionsForm uses many ttk controls)
        style = ttk.Style(self)
        style.configure("TFrame", background=panel)
        style.configure("TLabel", background=panel, foreground=fg)
        style.configure("TLabelframe", background=panel, foreground=fg)
        style.configure("TLabelframe.Label", background=panel, foreground=fg)
        style.configure("TCheckbutton", background=panel, foreground=fg)
        style.configure("TButton", background=panel, foreground=fg)
        # Do not force foreground on ttk input widgets:
        # on some Windows themes fieldbackground stays light, making light text unreadable.
        style.configure("TEntry", fieldbackground=panel)
        style.configure("TCombobox", fieldbackground=panel)
        style.map("TCombobox", fieldbackground=[("readonly", panel)])

    def _validate_percent(self, value_if_allowed):
        """Ritorna True solo se il valore è un intero 0–100."""
        if value_if_allowed == "":
            return True  # permette la digitazione
        if not value_if_allowed.isdigit():
            return False
        v = int(value_if_allowed)
        return 0 <= v <= 100

    # --------------------------------------------------------------------- #
    #  UI BUILD
    # --------------------------------------------------------------------- #

    def _build_ui(self):
        pad = self._s(6)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=pad, pady=pad)

        # Font globale
        default_font = (self.font_family, self.font_size)

        # Appearance frame
        appearance_frame = ttk.LabelFrame(main_frame, text="Appearance")
        appearance_frame.grid(row=0, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        appearance_frame.columnconfigure(1, weight=1)

        # Behaviour frame
        behaviour_frame = ttk.LabelFrame(main_frame, text="Behaviour")
        behaviour_frame.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        behaviour_frame.columnconfigure(1, weight=1)

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, sticky="e", padx=pad, pady=(0, pad))

        # ------------------------------------------------------------------ #
        #  APPEARANCE
        # ------------------------------------------------------------------ #

        # Background - Colour
        bg_colour_label = ttk.Label(appearance_frame, text="Background:", font=default_font)
        bg_colour_label.grid(row=0, column=0, sticky="w", padx=(pad, pad), pady=(pad, 0))

        bg_colour_text_label = ttk.Label(appearance_frame, text="Colour:", font=default_font)
        bg_colour_text_label.grid(row=1, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.bg_color_entry = ttk.Entry(
            appearance_frame,
            textvariable=self.bg_color_var,
            justify="center",
            font=default_font,
            width=10,
        )
        self.bg_color_entry.grid(row=1, column=1, sticky="we", padx=(0, pad), pady=(pad, 0))

        self.bg_color_button = ttk.Button(
            appearance_frame,
            text=">>",
            width=3,
            command=self._pick_bg_color
        )
        self.bg_color_button.grid(row=1, column=2, sticky="w", padx=(0, pad), pady=(pad, 0))

        self.bg_color_preview = tk.Label(
            appearance_frame,
            width=self._s(2),
            height=1,
            bg=self.bg_color_var.get(),
            relief="solid",
            bd=1,
        )
        self.bg_color_preview.grid(row=1, column=3, sticky="w", padx=(0, pad), pady=(pad, 0))

        # Background - Picture
        bg_picture_label = ttk.Label(appearance_frame, text="Picture:", font=default_font)
        bg_picture_label.grid(row=2, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.bg_picture_entry = ttk.Entry(
            appearance_frame,
            textvariable=self.bg_picture_var,
            font=default_font,
        )
        self.bg_picture_entry.grid(row=2, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        self.bg_picture_button = ttk.Button(
            appearance_frame,
            text=">>",
            width=3,
            command=self._pick_bg_picture
        )
        self.bg_picture_button.grid(row=2, column=3, sticky="w", padx=(0, pad), pady=(pad, 0))

        # Foreground - Colour
        fg_colour_label = ttk.Label(appearance_frame, text="Foreground:", font=default_font)
        fg_colour_label.grid(row=3, column=0, sticky="w", padx=(pad, pad), pady=(self._s(10), 0))

        fg_colour_text_label = ttk.Label(appearance_frame, text="Colour:", font=default_font)
        fg_colour_text_label.grid(row=4, column=0, sticky="e", padx=(pad, pad), pady=(pad, pad))

        self.fg_color_entry = ttk.Entry(
            appearance_frame,
            textvariable=self.fg_color_var,
            justify="center",
            font=default_font,
            width=10,
        )
        self.fg_color_entry.grid(row=4, column=1, sticky="we", padx=(0, pad), pady=(pad, pad))

        self.fg_color_button = ttk.Button(
            appearance_frame,
            text=">>",
            width=3,
            command=self._pick_fg_color
        )
        self.fg_color_button.grid(row=4, column=2, sticky="w", padx=(0, pad), pady=(pad, pad))

        self.fg_color_preview = tk.Label(
            appearance_frame,
            width=self._s(2),
            height=1,
            bg=self.fg_color_var.get(),
            relief="solid",
            bd=1,
        )
        self.fg_color_preview.grid(row=4, column=3, sticky="w", padx=(0, pad), pady=(pad, pad))

        # Panel - Colour
        panel_colour_label = ttk.Label(appearance_frame, text="Panel:", font=default_font)
        panel_colour_label.grid(row=5, column=0, sticky="e", padx=(pad, pad), pady=(0, pad))

        self.panel_color_entry = ttk.Entry(
            appearance_frame,
            textvariable=self.panel_color_var,
            justify="center",
            font=default_font,
            width=10,
        )
        self.panel_color_entry.grid(row=5, column=1, sticky="we", padx=(0, pad), pady=(0, pad))

        self.panel_color_button = ttk.Button(
            appearance_frame,
            text=">>",
            width=3,
            command=self._pick_panel_color
        )
        self.panel_color_button.grid(row=5, column=2, sticky="w", padx=(0, pad), pady=(0, pad))

        self.panel_color_preview = tk.Label(
            appearance_frame,
            width=self._s(2),
            height=1,
            bg=self.panel_color_var.get(),
            relief="solid",
            bd=1,
        )
        self.panel_color_preview.grid(row=5, column=3, sticky="w", padx=(0, pad), pady=(0, pad))

        self.dark_mode_check = ttk.Checkbutton(
            appearance_frame,
            text="Dark mode",
            variable=self.dark_mode_var,
            command=self._on_dark_mode_toggle,
        )
        self.dark_mode_check.grid(row=6, column=0, columnspan=2, sticky="w", padx=(pad, pad), pady=(0, pad))

        # ------------------------------------------------------------------ #
        #  BEHAVIOUR
        # ------------------------------------------------------------------ #

        # On Focus Loss
        ofl_label = ttk.Label(behaviour_frame, text="On Focus loss:", font=default_font)
        ofl_label.grid(row=0, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.ofl_combobox = ttk.Combobox(
            behaviour_frame,
            textvariable=self.on_focus_loss_var,
            values=list(self.on_focus_loss_map.values()),
            state="readonly",
            font=default_font,
        )
        self.ofl_combobox.grid(row=0, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        # On Apply
        oa_label = ttk.Label(behaviour_frame, text="On Apply:", font=default_font)
        oa_label.grid(row=1, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.oa_combobox = ttk.Combobox(
            behaviour_frame,
            textvariable=self.on_apply_var,
            values=list(self.on_apply_map.values()),
            state="readonly",
            font=default_font,
        )
        self.oa_combobox.grid(row=1, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        # On Close
        oc_label = ttk.Label(behaviour_frame, text="On Close:", font=default_font)
        oc_label.grid(row=2, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.oc_combobox = ttk.Combobox(
            behaviour_frame,
            textvariable=self.on_close_var,
            values=list(self.on_close_map.values()),
            state="readonly",
            font=default_font,
        )
        self.oc_combobox.grid(row=2, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        # Transparency
        tr_label = ttk.Label(behaviour_frame, text="Transparency:", font=default_font)
        tr_label.grid(row=3, column=0, sticky="w", padx=(pad, pad), pady=(self._s(10), 0))

        # Active
        tr_active_label = ttk.Label(behaviour_frame, text="Active:", font=default_font)
        tr_active_label.grid(row=4, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.tr_active_spin = tk.Spinbox(
            behaviour_frame,
            from_=10,
            to=100,
            textvariable=self.transparency_active_var,
            width=4,
            justify="right",
            font=default_font,
        )
        self.tr_active_spin.grid(row=4, column=1, sticky="w", padx=(0, 0), pady=(pad, 0))

        tr_active_pct = ttk.Label(behaviour_frame, text="%", font=default_font)
        tr_active_pct.grid(row=4, column=2, sticky="w", padx=(self._s(4), 0), pady=(pad, 0))

        # Faded
        tr_faded_label = ttk.Label(behaviour_frame, text="Faded:", font=default_font)
        tr_faded_label.grid(row=5, column=0, sticky="e", padx=(pad, pad), pady=(pad, pad))

        self.tr_faded_spin = tk.Spinbox(
            behaviour_frame,
            from_=10,
            to=100,
            textvariable=self.transparency_faded_var,
            width=4,
            justify="right",
            font=default_font,
        )
        self.tr_faded_spin.grid(row=5, column=1, sticky="w", padx=(0, 0), pady=(pad, pad))

        tr_faded_pct = ttk.Label(behaviour_frame, text="%", font=default_font)
        tr_faded_pct.grid(row=5, column=2, sticky="w", padx=(self._s(4), 0), pady=(pad, pad))

        # ------------------------------------------------------------------ #
        #  BUTTONS
        # ------------------------------------------------------------------ #

        ok_button = ttk.Button(buttons_frame, text="OK", command=self._on_ok)
        ok_button.grid(row=0, column=0, padx=(0, self._s(4)))

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self._on_cancel)
        cancel_button.grid(row=0, column=1)

    # --------------------------------------------------------------------- #
    #  COLOR PICKERS
    # --------------------------------------------------------------------- #

    def _pick_bg_color(self):
        initial = self.bg_color_var.get() or "#f0f0f0"
        color = colorchooser.askcolor(color=initial, parent=self)
        if color and color[1]:
            hex_color = color[1]
            self.bg_color_var.set(hex_color)
            self.bg_color_preview.configure(bg=hex_color)

    def _pick_fg_color(self):
        initial = self.fg_color_var.get() or "#101010"
        color = colorchooser.askcolor(color=initial, parent=self)
        if color and color[1]:
            hex_color = color[1]
            self.fg_color_var.set(hex_color)
            self.fg_color_preview.configure(bg=hex_color)

    def _pick_panel_color(self):
        initial = self.panel_color_var.get() or "#e4e6ea"
        color = colorchooser.askcolor(color=initial, parent=self)
        if color and color[1]:
            hex_color = color[1]
            self.panel_color_var.set(hex_color)
            self.panel_color_preview.configure(bg=hex_color)

    # --------------------------------------------------------------------- #
    #  PICTURE PICKER
    # --------------------------------------------------------------------- #

    def _pick_bg_picture(self):
        # Cartella /resources relativa alla root del progetto
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        resources_dir = os.path.join(base_dir, "resources")

        if not os.path.isdir(resources_dir):
            messagebox.showerror(
                "Resources folder not found",
                f"Resources folder not found:\n{resources_dir}",
                parent=self,
            )
            return

        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tif *.tiff"),
            ("All files", "*.*"),
        ]

        path = filedialog.askopenfilename(
            parent=self,
            title="Select background picture",
            initialdir=resources_dir,
            filetypes=filetypes,
        )
        if not path:
            return

        abs_path = os.path.abspath(path)
        resources_dir_abs = os.path.abspath(resources_dir)

        if not abs_path.startswith(resources_dir_abs):
            messagebox.showerror(
                "Invalid selection",
                "Please select a file inside the /resources folder.",
                parent=self,
            )
            return

        rel_path = os.path.relpath(abs_path, resources_dir_abs)
        # Salviamo solo il percorso relativo alla cartella resources
        self.bg_picture_var.set(rel_path)

    # --------------------------------------------------------------------- #
    #  OK / CANCEL
    # --------------------------------------------------------------------- #

    def _on_ok(self):
        # Aggiorna temp_config con i valori delle variabili
        self._sync_theme_vars_to_bucket(self._current_theme_key)
        behaviour = self.temp_config.setdefault("behaviour", {})

        # Appearance
        self.temp_config["dark_theme_enabled"] = bool(self.dark_mode_var.get())

        # Behaviour
        ofl_display = self.on_focus_loss_var.get()
        behaviour["on_focus_loss"] = self.on_focus_loss_rev.get(ofl_display, "do_nothing")

        oa_display = self.on_apply_var.get()
        behaviour["on_apply"] = self.on_apply_rev.get(oa_display, "keep_visible")

        oc_display = self.on_close_var.get()
        behaviour["on_close"] = self.on_close_rev.get(oc_display, "minimize_to_tray")

        # Trasparenze (clamp 10–100 per sicurezza)
        ta = max(10, min(100, int(self.transparency_active_var.get())))
        tf = max(10, min(100, int(self.transparency_faded_var.get())))
        behaviour["transparency_active"] = ta
        behaviour["transparency_faded"] = tf

        # 🔥 PATCH: aggiorna la config globale invece di crearne una nuova
        self.config.update(self.temp_config)

        # 🔥 PATCH: salva la config globale aggiornata
        save_config(self.config)

        self.destroy()

    def _on_cancel(self):
        # Nessuna modifica, nessun salvataggio
        self.config["dark_theme_enabled"] = self._initial_dark_mode_enabled
        if callable(self.on_theme_toggle):
            self.on_theme_toggle()
        self.destroy()


if __name__ == "__main__":
    # Esempio di test standalone
    root = tk.Tk()
    root.withdraw()
    OptionsForm(root)
    root.mainloop()
