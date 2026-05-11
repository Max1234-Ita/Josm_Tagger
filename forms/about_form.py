
import tkinter as tk
from config_manager import save_config
import os
import sys

from main import appinfo
from effects import apply_background_picture, apply_theme_colors, get_active_theme
from forms.base_form import BaseForm


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class AboutForm(BaseForm):

    _instance = None
    MAX_SIZE = 1200

    def __init__(self, root, config=None):
        if AboutForm._instance is not None:
            try:
                AboutForm._instance.lift()
                AboutForm._instance.focus_force()
                return
            except:
                AboutForm._instance = None

        self.config = config if config else {}

        super().__init__(root, "about")
        AboutForm._instance = self

        self.title("About")
        self.attributes("-topmost", True)
        
        # Tema
        theme = get_active_theme(self.config)
        self.bg_color = theme.get("bg", "#f0f0f0")
        self.fg_color = theme.get("fg", "#101010")
        self.configure(bg=self.bg_color)
        
        apply_background_picture(self, self.config)

        # Disable resize
        self.resizable(False, False)

        # Hide minimize and maximize (on Windows)
        try:
            self.attributes("-toolwindow", True)
        except:
            pass

        # Window icon
        try:
            icon_path = resource_path(os.path.join("resources", "josm_tagger.png"))
            self.raw_image = tk.PhotoImage(file=icon_path)
            self.iconphoto(True, self.raw_image)
        except:
            self.raw_image = None

        # Load geometry from config.json
        self._load_geometry()

        # Main frame
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Image label (initially empty)
        self.icon_label = tk.Label(main_frame, bg=self.bg_color)
        self.icon_label.pack(pady=(0, 10))

        # Appinfo text
        f = (self.config.get("font_family", "Calibri"), int(self.config.get("font_size", 11)))
        
        info_label = tk.Label(
            main_frame,
            text=appinfo,
            justify="center",
            wraplength=AboutForm.MAX_SIZE - 40,
            bg=self.bg_color,
            fg=self.fg_color,
            font=f
        )
        info_label.pack(anchor="center", pady=(10, 10))

        # Applica tema globale ricorsivamente
        apply_theme_colors(self, self.config)

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Update layout and scale image proportionally
        self.update_idletasks()
        self._update_scaled_image()

        # Set focus to the window
        self.focus_force()

    def _get_scaled_image(self, image):
        if not image:
            return None

        width = image.width()
        height = image.height()

        max_dim = AboutForm.MAX_SIZE - 100  # margin for text + padding

        if width <= max_dim and height <= max_dim:
            return image

        scale = min(max_dim / width, max_dim / height)

        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))

        # PhotoImage only supports integer subsample/zoom → workaround
        subsample_x = max(1, int(width / new_w))
        subsample_y = max(1, int(height / new_h))

        return image.subsample(subsample_x, subsample_y)

    def _enforce_max_size(self):
        w = self.winfo_width()
        h = self.winfo_height()

        w = min(w, AboutForm.MAX_SIZE)
        h = min(h, AboutForm.MAX_SIZE)

        self.geometry(f"{w}x{h}")

    def _on_close(self):
        try:
            self.destroy()
        finally:
            AboutForm._instance = None

    def _load_geometry(self):
        default_w = 320
        default_h = 260

        if not self.config:
            self.geometry(f"{default_w}x{default_h}")
            return

        geom = self.config.get("about_form_geometry")

        if geom:
            try:
                # Simple parsing WxH+X+Y
                size_part = geom.split("+")[0]
                w, h = map(int, size_part.split("x"))

                # Apply UI scale
                ui_scale = self.config.get("ui_scale", 1.0)
                w = int(w * ui_scale)
                h = int(h * ui_scale)

                # Limit to MAX_SIZE
                w = min(w, AboutForm.MAX_SIZE)
                h = min(h, AboutForm.MAX_SIZE)

                self.geometry(f"{w}x{h}")
            except:
                self.geometry(f"{default_w}x{default_h}")
        else:
            self.geometry(f"{default_w}x{default_h}")

    def _save_geometry(self):
        if not self.config:
            return

        self.config["about_form_geometry"] = self.geometry()
        save_config(self.config)

    def _update_scaled_image(self):
        if not self.raw_image:
            return

        # Available dimensions in the frame
        frame_w = self.winfo_width() - 40
        max_image_h = 200  # fixed max height for the image

        if frame_w <= 0:
            return

        img_w = self.raw_image.width()
        img_h = self.raw_image.height()

        scale = min(frame_w / img_w, max_image_h / img_h, 1.0)

        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        subsample_x = max(1, int(img_w / new_w))
        subsample_y = max(1, int(img_h / new_h))

        self.image = self.raw_image.subsample(subsample_x, subsample_y)

        theme = get_active_theme(self.config)
        self.icon_label.configure(image=self.image, bg=theme.get("bg"))
