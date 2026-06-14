import os
import sys
import copy
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import colorchooser, filedialog, messagebox

from config_manager import load_config, save_config
from effects import apply_background_picture, apply_theme_colors, get_active_theme
from forms.base_form import BaseForm
from josm_interface import (
    JOSM_CONTROL_GUI_AUTOMATION,
    JOSM_CONTROL_REMOTE,
    is_linux,
    resolve_control_method,
)


class OptionsForm(BaseForm):
    """
    Application options window.
    """

    def __init__(self, master, config, on_theme_toggle=None):
        # --- CONFIGURATION ---
        self.config = config
        self.on_theme_toggle = on_theme_toggle

        self.config_data = load_config()
        self.temp_config = copy.deepcopy(self.config_data)
        self._initial_dark_mode_enabled = bool(self.config_data.get("dark_theme_enabled", False))

        super().__init__(master, "options")
        self.resizable(False, False)
        self._ensure_defaults()

        # --- FONT & SCALE ---
        self.font_family = self.config_data.get("font_family", "Calibri")
        self.font_size = int(self.config_data.get("font_size", 11))
        self.ui_scale = float(self.config_data.get("ui_scale", 1.0))

        # --- WINDOW ---
        self.title("Preferences")
        self._configure_window_style()
        
        # --- TK VARIABLES ---
        self._init_variables()
        vcmd = (self.register(self._validate_percent), "%P")
        self._percent_validator = vcmd

        # --- UI ---
        self._build_ui()

        # --- APPLY INITIAL THEME ---
        self._apply_current_theme_to_form()
        apply_background_picture(self, self.config_data)

        # --- CLOSE EVENTS ---
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._place_near_pointer_with_parent_offset(master)
        self.focus_set()

    def _ensure_defaults(self):
        theme = self.temp_config.setdefault("theme", {})
        theme.setdefault("bg", "#f0f0f0")
        theme.setdefault("panel", "#e4e6ea")
        theme.setdefault("fg", "#101010")
        theme.setdefault("panel_fg", "#101010")
        theme.setdefault("picture", None)
        dark_theme = self.temp_config.setdefault("dark_theme", {})
        dark_theme.setdefault("bg", "#1e1f22")
        dark_theme.setdefault("panel", "#2a2e35")
        dark_theme.setdefault("fg", "#d8d8d8")
        dark_theme.setdefault("panel_fg", "#d8d8d8")
        dark_theme.setdefault("picture", None)
        self.temp_config.setdefault("dark_theme_enabled", False)
        self.temp_config.setdefault("josm_control_method", JOSM_CONTROL_GUI_AUTOMATION)
        if is_linux():
            self.temp_config["josm_control_method"] = JOSM_CONTROL_REMOTE

    def _configure_window_style(self):
        self.attributes("-topmost", True)
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
                    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]
                user32 = ctypes.windll.user32
                pt = POINT(int(x), int(y))
                monitor = user32.MonitorFromPoint(pt, 2)
                if monitor:
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                        return (int(info.rcWork.left), int(info.rcWork.top), int(info.rcWork.right), int(info.rcWork.bottom))
            except Exception: pass
        return 0, 0, int(self.winfo_screenwidth()), int(self.winfo_screenheight())

    def _clamp_to_monitor(self, x, y):
        self.update_idletasks()
        ww = max(1, int(self.winfo_width()))
        wh = max(1, int(self.winfo_height()))
        left, top, right, bottom = self._monitor_workarea_from_point(x, y)
        clamped_x = min(max(int(x), left), max(left, right - ww))
        clamped_y = min(max(int(y), top), max(top, bottom - wh))
        return clamped_x, clamped_y

    def _place_near_pointer_with_parent_offset(self, parent):
        self.update_idletasks()
        px = self.winfo_pointerx()
        py = self.winfo_pointery()
        ox = int(parent.winfo_width() * 0.30)
        oy = int(parent.winfo_height() * 0.30)
        x, y = self._clamp_to_monitor(px + ox, py + oy)
        self.geometry(f"+{x}+{y}")

    def _s(self, value):
        return int(round(value * self.ui_scale))

    def _init_variables(self):
        self.dark_mode_var = tk.BooleanVar(value=bool(self.temp_config.get("dark_theme_enabled", False)))
        self._current_theme_key = "dark_theme" if self.dark_mode_var.get() else "theme"
        theme = self.temp_config[self._current_theme_key]
        behaviour = self.temp_config.get("behaviour", {})

        self.bg_color_var = tk.StringVar(value=theme.get("bg", "#f0f0f0"))
        self.bg_picture_var = tk.StringVar(value=theme.get("picture") or "")
        self.fg_color_var = tk.StringVar(value=theme.get("fg", "#101010"))
        self.panel_color_var = tk.StringVar(value=theme.get("panel", "#e4e6ea"))

        self.on_focus_loss_map = {"do_nothing": "Do nothing", "fade_out": "Fade out"}
        self.on_focus_loss_rev = {v: k for k, v in self.on_focus_loss_map.items()}
        self.on_focus_loss_var = tk.StringVar(value=self.on_focus_loss_map.get(behaviour.get("on_focus_loss", "do_nothing"), "Do nothing"))

        self.on_apply_map = {"keep_visible": "Keep form visible", "minimize_to_tray": "Minimize to Tray"}
        self.on_apply_rev = {v: k for k, v in self.on_apply_map.items()}
        self.on_apply_var = tk.StringVar(value=self.on_apply_map.get(behaviour.get("on_apply", "keep_visible"), "Keep form visible"))

        self.on_close_map = {"minimize_to_tray": "Minimize to Tray", "exit_app": "Exit app"}
        self.on_close_rev = {v: k for k, v in self.on_close_map.items()}
        self.on_close_var = tk.StringVar(value=self.on_close_map.get(behaviour.get("on_close", "minimize_to_tray"), "Minimize to Tray"))

        self.transparency_active_var = tk.IntVar(value=max(10, min(100, int(behaviour.get("transparency_active", 100)))))
        self.transparency_faded_var = tk.IntVar(value=max(10, min(100, int(behaviour.get("transparency_faded", 35)))))
        self.josm_control_method_map = {
            JOSM_CONTROL_GUI_AUTOMATION: "GUI Automation",
            JOSM_CONTROL_REMOTE: "Remote Control",
        }
        self.josm_control_method_rev = {v: k for k, v in self.josm_control_method_map.items()}
        selected_method = resolve_control_method(self.temp_config.get("josm_control_method"))
        self.josm_control_method_var = tk.StringVar(
            value=self.josm_control_method_map[selected_method]
        )

    def _ensure_theme_bucket(self, key):
        bucket = self.temp_config.setdefault(key, {})
        bucket.setdefault("bg", "#f0f0f0" if key == "theme" else "#1e1f22")
        bucket.setdefault("panel", "#e4e6ea" if key == "theme" else "#2a2e35")
        bucket.setdefault("fg", "#101010" if key == "theme" else "#d8d8d8")
        bucket.setdefault("panel_fg", "#101010" if key == "theme" else "#d8d8d8")
        bucket.setdefault("picture", None)
        return bucket

    def _sync_theme_vars_to_bucket(self, key):
        bucket = self._ensure_theme_bucket(key)
        bucket["bg"] = self.bg_color_var.get().strip() or bucket.get("bg", "#f0f0f0")
        bucket["fg"] = self.fg_color_var.get().strip() or bucket.get("fg", "#101010")
        bucket["panel"] = self.panel_color_var.get().strip() or bucket.get("panel", bucket.get("bg", "#f0f0f0"))
        bucket["panel_fg"] = bucket["fg"] # Sincronizzazione base
        picture_val = self.bg_picture_var.get().strip()
        bucket["picture"] = picture_val if picture_val else None

    def _load_theme_vars_from_bucket(self, key):
        bucket = self._ensure_theme_bucket(key)
        self.bg_color_var.set(bucket.get("bg", "#f0f0f0"))
        self.fg_color_var.set(bucket.get("fg", "#101010"))
        self.panel_color_var.set(bucket.get("panel", bucket.get("bg", "#f0f0f0")))
        self.bg_picture_var.set(bucket.get("picture") or "")
        self._update_color_previews()

    def _update_color_previews(self):
        if hasattr(self, 'bg_color_preview'):
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
        panel_fg = theme.get("panel_fg", fg)

        # 1. Applica colori base tramite effects
        apply_theme_colors(self, self.config)
        apply_background_picture(self, self.config)

        # 2. Configura stili TTK (Clam per supporto Dark)
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        style.configure("TCheckbutton", background=bg, foreground=fg)
        
        # Pulsanti stilizzati
        style.configure("TButton", background=panel, foreground=panel_fg, borderwidth=1)
        style.map("TButton", 
                  background=[("active", "#0078d7")], 
                  foreground=[("active", "white")])

        # Input widgets
        style.configure("TEntry", fieldbackground=panel, foreground=panel_fg, insertcolor=panel_fg)
        style.configure("TCombobox", fieldbackground=panel, background=panel, foreground=panel_fg, arrowcolor=panel_fg)
        style.map("TCombobox", 
                  fieldbackground=[("readonly", panel), ("active", panel)],
                  foreground=[("readonly", panel_fg), ("active", panel_fg)])
        
        self.option_add("*TCombobox*Listbox.background", panel)
        self.option_add("*TCombobox*Listbox.foreground", panel_fg)

        # 3. Fix widget TK non-ttk e ripristino anteprime
        def fix_tk_widgets(widget):
            if isinstance(widget, (tk.Spinbox, tk.Entry, tk.Text)):
                try: widget.configure(bg=panel, fg=panel_fg, insertbackground=panel_fg)
                except: pass
            elif isinstance(widget, tk.Frame) and widget != self:
                try: widget.configure(bg=bg)
                except: pass
            elif isinstance(widget, tk.Label):
                # Se NON è una label di anteprima (rilevata tramite attributo specifico o nome)
                if not hasattr(widget, "_is_color_preview"):
                    try: widget.configure(bg=bg, fg=fg)
                    except: pass
            
            for child in widget.winfo_children(): fix_tk_widgets(child)
            
        fix_tk_widgets(self)
        
        # 4. Forza ripristino anteprime colore
        self._update_color_previews()

    def _validate_percent(self, value_if_allowed):
        if value_if_allowed == "": return True
        if not value_if_allowed.isdigit(): return False
        return 0 <= int(value_if_allowed) <= 100

    def _build_ui(self):
        pad = self._s(6)
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=pad, pady=pad)
        default_font = (self.font_family, self.font_size)

        # APPEARANCE
        appearance_frame = ttk.LabelFrame(main_frame, text="Appearance")
        appearance_frame.grid(row=0, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        appearance_frame.columnconfigure(1, weight=1)

        ttk.Label(appearance_frame, text="Background:", font=default_font).grid(row=0, column=0, sticky="w", padx=pad, pady=(pad, 0))
        ttk.Label(appearance_frame, text="Colour:", font=default_font).grid(row=1, column=0, sticky="e", padx=pad, pady=(pad, 0))
        self.bg_color_entry = ttk.Entry(appearance_frame, textvariable=self.bg_color_var, justify="center", font=default_font, width=10)
        self.bg_color_entry.grid(row=1, column=1, sticky="we", padx=(0, pad), pady=(pad, 0))
        ttk.Button(appearance_frame, text=">>", width=3, command=self._pick_bg_color).grid(row=1, column=2, sticky="w", padx=(0, pad), pady=(pad, 0))
        
        self.bg_color_preview = tk.Label(appearance_frame, width=self._s(2), height=1, bg=self.bg_color_var.get(), relief="solid", bd=1)
        self.bg_color_preview._is_color_preview = True # Flag per apply_theme
        self.bg_color_preview.grid(row=1, column=3, sticky="w", padx=(0, pad), pady=(pad, 0))

        ttk.Label(appearance_frame, text="Picture:", font=default_font).grid(row=2, column=0, sticky="e", padx=pad, pady=(pad, 0))
        self.bg_picture_entry = ttk.Entry(appearance_frame, textvariable=self.bg_picture_var, font=default_font)
        self.bg_picture_entry.grid(row=2, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))
        ttk.Button(appearance_frame, text=">>", width=3, command=self._pick_bg_picture).grid(row=2, column=3, sticky="w", padx=(0, pad), pady=(pad, 0))

        ttk.Label(appearance_frame, text="Foreground:", font=default_font).grid(row=3, column=0, sticky="w", padx=pad, pady=(self._s(10), 0))
        ttk.Label(appearance_frame, text="Colour:", font=default_font).grid(row=4, column=0, sticky="e", padx=pad, pady=pad)
        self.fg_color_entry = ttk.Entry(appearance_frame, textvariable=self.fg_color_var, justify="center", font=default_font, width=10)
        self.fg_color_entry.grid(row=4, column=1, sticky="we", padx=(0, pad), pady=pad)
        ttk.Button(appearance_frame, text=">>", width=3, command=self._pick_fg_color).grid(row=4, column=2, sticky="w", padx=(0, pad), pady=pad)
        
        self.fg_color_preview = tk.Label(appearance_frame, width=self._s(2), height=1, bg=self.fg_color_var.get(), relief="solid", bd=1)
        self.fg_color_preview._is_color_preview = True
        self.fg_color_preview.grid(row=4, column=3, sticky="w", padx=(0, pad), pady=pad)

        ttk.Label(appearance_frame, text="Panel:", font=default_font).grid(row=5, column=0, sticky="e", padx=pad, pady=(0, pad))
        self.panel_color_entry = ttk.Entry(appearance_frame, textvariable=self.panel_color_var, justify="center", font=default_font, width=10)
        self.panel_color_entry.grid(row=5, column=1, sticky="we", padx=(0, pad), pady=(0, pad))
        ttk.Button(appearance_frame, text=">>", width=3, command=self._pick_panel_color).grid(row=5, column=2, sticky="w", padx=(0, pad), pady=(0, pad))
        
        self.panel_color_preview = tk.Label(appearance_frame, width=self._s(2), height=1, bg=self.panel_color_var.get(), relief="solid", bd=1)
        self.panel_color_preview._is_color_preview = True
        self.panel_color_preview.grid(row=5, column=3, sticky="w", padx=(0, pad), pady=(0, pad))

        ttk.Checkbutton(appearance_frame, text="Dark mode", variable=self.dark_mode_var, command=self._on_dark_mode_toggle).grid(row=6, column=0, columnspan=2, sticky="w", padx=pad, pady=(0, pad))

        # BEHAVIOUR
        behaviour_frame = ttk.LabelFrame(main_frame, text="Behaviour")
        behaviour_frame.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        behaviour_frame.columnconfigure(1, weight=1)
        
        ttk.Label(behaviour_frame, text="On Focus loss:", font=default_font).grid(row=0, column=0, sticky="e", padx=pad, pady=(pad, 0))
        self.ofl_combobox = ttk.Combobox(behaviour_frame, textvariable=self.on_focus_loss_var, values=list(self.on_focus_loss_map.values()), state="readonly", font=default_font)
        self.ofl_combobox.grid(row=0, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        ttk.Label(behaviour_frame, text="On Apply:", font=default_font).grid(row=1, column=0, sticky="e", padx=pad, pady=(pad, 0))
        self.oa_combobox = ttk.Combobox(behaviour_frame, textvariable=self.on_apply_var, values=list(self.on_apply_map.values()), state="readonly", font=default_font)
        self.oa_combobox.grid(row=1, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        ttk.Label(behaviour_frame, text="On Close:", font=default_font).grid(row=2, column=0, sticky="e", padx=pad, pady=(pad, 0))
        self.oc_combobox = ttk.Combobox(behaviour_frame, textvariable=self.on_close_var, values=list(self.on_close_map.values()), state="readonly", font=default_font)
        self.oc_combobox.grid(row=2, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=(pad, 0))

        ttk.Label(behaviour_frame, text="Transparency:", font=default_font).grid(row=3, column=0, sticky="w", padx=pad, pady=(self._s(10), 0))
        
        # Active Row
        ttk.Label(behaviour_frame, text="Active:", font=default_font).grid(row=4, column=0, sticky="e", padx=pad, pady=(pad, 0))
        active_cont = tk.Frame(behaviour_frame)
        active_cont.grid(row=4, column=1, sticky="w", pady=(pad, 0))
        self.tr_active_spin = tk.Spinbox(active_cont, from_=10, to=100, textvariable=self.transparency_active_var, width=4, justify="right", font=default_font)
        self.tr_active_spin.pack(side="left")
        ttk.Label(active_cont, text="%", font=default_font).pack(side="left", padx=self._s(4))

        # Faded Row
        ttk.Label(behaviour_frame, text="Faded:", font=default_font).grid(row=5, column=0, sticky="e", padx=pad, pady=pad)
        faded_cont = tk.Frame(behaviour_frame)
        faded_cont.grid(row=5, column=1, sticky="w", pady=pad)
        self.tr_faded_spin = tk.Spinbox(faded_cont, from_=10, to=100, textvariable=self.transparency_faded_var, width=4, justify="right", font=default_font)
        self.tr_faded_spin.pack(side="left")
        ttk.Label(faded_cont, text="%", font=default_font).pack(side="left", padx=self._s(4))

        # JOSM INTERFACE
        josm_frame = ttk.LabelFrame(main_frame, text="JOSM Interface")
        josm_frame.grid(row=2, column=0, sticky="nsew", padx=pad, pady=(0, pad))
        josm_frame.columnconfigure(1, weight=1)

        ttk.Label(josm_frame, text="Method:", font=default_font).grid(
            row=0, column=0, sticky="e", padx=pad, pady=pad
        )
        self.josm_method_combobox = ttk.Combobox(
            josm_frame,
            textvariable=self.josm_control_method_var,
            values=list(self.josm_control_method_map.values()),
            state="readonly",
            font=default_font,
        )
        self.josm_method_combobox.grid(
            row=0, column=1, columnspan=2, sticky="we", padx=(0, pad), pady=pad
        )

        if is_linux():
            self.josm_method_combobox.state(["disabled"])

        # BUTTONS
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, sticky="e", padx=pad, pady=(0, pad))
        ttk.Button(buttons_frame, text="OK", command=self._on_ok).grid(row=0, column=0, padx=(0, self._s(4)))
        ttk.Button(buttons_frame, text="Cancel", command=self._on_cancel).grid(row=0, column=1)

    def _pick_bg_color(self):
        color = colorchooser.askcolor(color=self.bg_color_var.get(), parent=self)
        if color[1]:
            self.bg_color_var.set(color[1])
            self.bg_color_preview.configure(bg=color[1])

    def _pick_fg_color(self):
        color = colorchooser.askcolor(color=self.fg_color_var.get(), parent=self)
        if color[1]:
            self.fg_color_var.set(color[1])
            self.fg_color_preview.configure(bg=color[1])

    def _pick_panel_color(self):
        color = colorchooser.askcolor(color=self.panel_color_var.get(), parent=self)
        if color[1]:
            self.panel_color_var.set(color[1])
            self.panel_color_preview.configure(bg=color[1])

    def _pick_bg_picture(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        res_dir = os.path.join(base_dir, "resources")
        path = filedialog.askopenfilename(parent=self, title="Select background picture", initialdir=res_dir, filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All", "*.*")])
        if path:
            if os.path.abspath(path).startswith(os.path.abspath(res_dir)):
                self.bg_picture_var.set(os.path.relpath(path, res_dir))
            else:
                messagebox.showerror("Error", "Select a file inside /resources", parent=self)

    def _on_ok(self):
        self._sync_theme_vars_to_bucket(self._current_theme_key)
        beh = self.temp_config.setdefault("behaviour", {})
        beh["on_focus_loss"] = self.on_focus_loss_rev.get(self.on_focus_loss_var.get(), "do_nothing")
        beh["on_apply"] = self.on_apply_rev.get(self.on_apply_var.get(), "keep_visible")
        beh["on_close"] = self.on_close_rev.get(self.on_close_var.get(), "minimize_to_tray")
        beh["transparency_active"] = int(self.transparency_active_var.get())
        beh["transparency_faded"] = int(self.transparency_faded_var.get())
        self.temp_config["josm_control_method"] = resolve_control_method(
            self.josm_control_method_rev.get(
                self.josm_control_method_var.get(),
                self.temp_config.get("josm_control_method"),
            )
        )
        self.config.update(self.temp_config)
        save_config(self.config)
        messagebox.showinfo("Restart Recommended", "Some options may require an application restart to take full effect.", parent=self)
        self.destroy()

    def _on_cancel(self):
        self.config["dark_theme_enabled"] = self._initial_dark_mode_enabled
        if callable(self.on_theme_toggle): self.on_theme_toggle()
        self.destroy()