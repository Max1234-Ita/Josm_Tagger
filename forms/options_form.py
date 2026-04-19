import os
import copy
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import colorchooser, filedialog, messagebox

from config_manager import load_config, save_config


class OptionsForm(tk.Toplevel):
    """
    Finestra di opzioni dell'applicazione.

    - Nessuna opzione viene applicata o salvata immediatamente.
    - Tutte le modifiche restano in self.temp_config finché l'utente non preme OK.
    - Con OK: self.temp_config -> config.json (via save_config).
    - Con Cancel o [X]: nessuna modifica, nessun salvataggio.
    """

    def __init__(self, master=None):
        super().__init__(master)

        # --- CONFIGURAZIONE ---
        self.config_data = load_config()
        self.temp_config = copy.deepcopy(self.config_data)

        # Blocca il ridimensionamento del form
        self.resizable(False, False)

        # Assicura la presenza delle nuove chiavi
        self._ensure_defaults()

        # --- FONT & SCALA ---
        self.font_family = self.config_data.get("font_family", "Calibri")
        self.font_size = int(self.config_data.get("font_size", 11))
        self.ui_scale = float(self.config_data.get("ui_scale", 1.0))

        # --- FINESTRA ---
        self.title("Preferences")
        self._configure_window_style()

        # --- VARIABILI TK ---
        self._init_variables()
        vcmd = (self.register(self._validate_percent), "%P")
        self._percent_validator = vcmd

        # --- UI ---
        self._build_ui()

        # --- EVENTI CHIUSURA ---
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Focus iniziale
        self.transient(master)
        self.grab_set()
        self.focus_set()

    # --------------------------------------------------------------------- #
    #  CONFIG / DEFAULTS
    # --------------------------------------------------------------------- #

    def _ensure_defaults(self):
        theme = self.temp_config.setdefault("theme", {})
        theme.setdefault("bg", "#f0f0f0")
        theme.setdefault("fg", "#101010")
        theme.setdefault("picture", None)

        behaviour = self.temp_config.setdefault("behaviour", {})
        behaviour.setdefault("on_focus_loss", "do_nothing")
        behaviour.setdefault("on_apply", "keep_visible")
        behaviour.setdefault("transparency_active", 100)
        behaviour.setdefault("transparency_faded", 35)

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
        theme = self.temp_config["theme"]
        behaviour = self.temp_config["behaviour"]

        # Appearance - Background
        self.bg_color_var = tk.StringVar(value=theme.get("bg", "#f0f0f0"))
        self.bg_picture_var = tk.StringVar(
            value=theme.get("picture") or ""
        )

        # Appearance - Foreground
        self.fg_color_var = tk.StringVar(value=theme.get("fg", "#101010"))

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

        # Behaviour - Transparency
        # Limiti: 10–100 per evitare invisibilità
        ta = max(10, min(100, int(behaviour.get("transparency_active", 100))))
        tf = max(10, min(100, int(behaviour.get("transparency_faded", 35))))

        self.transparency_active_var = tk.IntVar(value=ta)
        self.transparency_faded_var = tk.IntVar(value=tf)

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

        # Transparency
        tr_label = ttk.Label(behaviour_frame, text="Transparency:", font=default_font)
        tr_label.grid(row=2, column=0, sticky="w", padx=(pad, pad), pady=(self._s(10), 0))

        # Active
        tr_active_label = ttk.Label(behaviour_frame, text="Active:", font=default_font)
        tr_active_label.grid(row=3, column=0, sticky="e", padx=(pad, pad), pady=(pad, 0))

        self.tr_active_spin = tk.Spinbox(
            behaviour_frame,
            from_=10,
            to=100,
            textvariable=self.transparency_active_var,
            width=4,
            justify="right",
            font=default_font,
        )
        self.tr_active_spin.grid(row=3, column=1, sticky="w", padx=(0, 0), pady=(pad, 0))

        tr_active_pct = ttk.Label(behaviour_frame, text="%", font=default_font)
        tr_active_pct.grid(row=3, column=2, sticky="w", padx=(self._s(4), 0), pady=(pad, 0))

        # Faded
        tr_faded_label = ttk.Label(behaviour_frame, text="Faded:", font=default_font)
        tr_faded_label.grid(row=4, column=0, sticky="e", padx=(pad, pad), pady=(pad, pad))

        self.tr_faded_spin = tk.Spinbox(
            behaviour_frame,
            from_=10,
            to=100,
            textvariable=self.transparency_faded_var,
            width=4,
            justify="right",
            font=default_font,
        )
        self.tr_faded_spin.grid(row=4, column=1, sticky="w", padx=(0, 0), pady=(pad, pad))

        tr_faded_pct = ttk.Label(behaviour_frame, text="%", font=default_font)
        tr_faded_pct.grid(row=4, column=2, sticky="w", padx=(self._s(4), 0), pady=(pad, pad))

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
        theme = self.temp_config.setdefault("theme", {})
        behaviour = self.temp_config.setdefault("behaviour", {})

        # Appearance
        theme["bg"] = self.bg_color_var.get().strip() or "#f0f0f0"
        theme["fg"] = self.fg_color_var.get().strip() or "#101010"
        picture_val = self.bg_picture_var.get().strip()
        theme["picture"] = picture_val if picture_val else None

        # Behaviour
        ofl_display = self.on_focus_loss_var.get()
        behaviour["on_focus_loss"] = self.on_focus_loss_rev.get(ofl_display, "do_nothing")

        oa_display = self.on_apply_var.get()
        behaviour["on_apply"] = self.on_apply_rev.get(oa_display, "keep_visible")

        # Trasparenze (clamp 10–100 per sicurezza)
        ta = max(10, min(100, int(self.transparency_active_var.get())))
        tf = max(10, min(100, int(self.transparency_faded_var.get())))
        behaviour["transparency_active"] = ta
        behaviour["transparency_faded"] = tf

        # Copia temp_config -> config_data e salva
        self.config_data = copy.deepcopy(self.temp_config)
        save_config(self.config_data)

        self.destroy()

    def _on_cancel(self):
        # Nessuna modifica, nessun salvataggio
        self.destroy()


if __name__ == "__main__":
    # Esempio di test standalone
    root = tk.Tk()
    root.withdraw()
    OptionsForm(root)
    root.mainloop()
