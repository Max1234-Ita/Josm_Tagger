import tkinter as tk
from config_manager import load_config, save_config


class BaseForm(tk.Toplevel):

    def __init__(self, parent, form_id):

        super().__init__(parent)

        self.parent = parent
        self.form_id = form_id

        self.config_data = load_config()

        self.transient(parent)
        self.attributes("-topmost", True)

        self._restore_geometry()

        self.bind("<Configure>", self._save_geometry)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._internal_resize = False

    def _geometry_key(self):
        return f"geometry_{self.form_id}"

    def _restore_geometry(self):

        key = self._geometry_key()

        if key in self.config_data:
            self.geometry(self.config_data[key])

    def _save_geometry(self, event=None):

        if self._internal_resize:
            return

        geom = self.geometry()

        cfg = load_config()

        key = self._geometry_key()

        if cfg.get(key) != geom:
            cfg[key] = geom
            save_config(cfg)

        self.config_data = cfg

    def _on_close(self):
        self.destroy()