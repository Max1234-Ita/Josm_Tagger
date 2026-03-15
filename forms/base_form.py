import tkinter as tk
from config_manager import load_config, save_config


class BaseForm(tk.Toplevel):

    def __init__(self, parent, form_id):

        super().__init__(parent)

        self.parent = parent
        self.form_id = form_id

        self.attributes("-topmost", True)
        self.transient(parent)

        self.after(10, self._restore_geometry)

        self.bind("<Configure>", self._save_geometry)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------------------
    # CONFIG KEY
    # --------------------------------

    def _geometry_key(self):

        return f"geometry_{self.form_id}"

    # --------------------------------
    # GEOMETRY RESTORE
    # --------------------------------

    def _restore_geometry(self):

        cfg = load_config()
        key = self._geometry_key()

        geom = cfg.get(key)

        if geom:
            try:
                self.geometry(geom)
                return
            except:
                pass

        # fallback: apri vicino al mainform
        self._place_near_parent()

    # --------------------------------
    # PLACE NEAR MAINFORM
    # --------------------------------

    def _place_near_parent(self):

        self.parent.update_idletasks()

        px = self.parent.winfo_x()
        py = self.parent.winfo_y()

        self.geometry(f"+{px+40}+{py+40}")

    # --------------------------------
    # SAVE GEOMETRY
    # --------------------------------

    def _save_geometry(self, event=None):

        geom = self.geometry()

        cfg = load_config()
        key = self._geometry_key()

        if cfg.get(key) != geom:
            cfg[key] = geom
            save_config(cfg)

    # --------------------------------
    # CLOSE
    # --------------------------------

    def _on_close(self):

        self.destroy()