
import tkinter as tk
from tkinter import font
from config_manager import save_config
from effects import apply_background_picture, get_active_theme, apply_theme_colors
from forms.base_form import BaseForm


class FontSelectorForm(BaseForm):

    _instance = None

    def __init__(self, root, config, apply_callback):

        if FontSelectorForm._instance and FontSelectorForm._instance.winfo_exists():
            FontSelectorForm._instance.deiconify()
            FontSelectorForm._instance.lift()
            FontSelectorForm._instance.focus_force()
            return

        FontSelectorForm._instance = self

        import os
        import sys

        self.config = config
        self.apply_callback = apply_callback
        
        # Carica tema
        self.theme = get_active_theme(self.config)
        self.bg_color = self.theme.get("bg", "#f0f0f0")
        self.fg_color = self.theme.get("fg", "#101010")
        self.panel_color = self.theme.get("panel", self.bg_color)
        self.panel_fg = self.theme.get("panel_fg", self.fg_color)

        super().__init__(root, "font_selector")
        self.title("Font Selector")
        self.configure(bg=self.bg_color)
        self.attributes("-topmost", True)
        
        # Scala UI
        scale = float(self.config.get("ui_scale", 1.0))
        self.minsize(int(420 * scale), int(360 * scale))
        self.resizable(True, True)

        apply_background_picture(self, config)

        # Font base per i controlli
        self._font = (self.config.get("font_family", "Segoe UI"), int(self.config.get("font_size", 10) * scale))

        # ---------------- WINDOW STYLE ----------------
        try:
            if os.name == "nt":
                self.attributes("-toolwindow", True)
        except:
            pass
        # ---------------------------------------------

        # ---------------- ICON ----------------
        try:
            base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
            icon_path_win = os.path.join(base_path, "resources", "josm_tagger.ico")
            icon_path_linux = os.path.join(base_path, "resources", "josm_tagger.png")

            if os.name == "nt" and os.path.exists(icon_path_win):
                self.iconbitmap(icon_path_win)
            elif os.path.exists(icon_path_linux):
                icon_img = tk.PhotoImage(file=icon_path_linux)
                self.iconphoto(True, icon_img)
                self._icon_img = icon_img
        except:
            pass
        # --------------------------------------

        self.font_var = tk.StringVar(value=self.config.get("font_family", "Segoe UI"))
        self.size_var = tk.IntVar(value=self.config.get("font_size", 10))

        # Declare attributes
        self.fonts = []
        self._icon_img = None

        # Declare UI attributes
        self.entry = None
        self.size_spin = None
        self.font_list = None
        self.preview_label = None

        self.build_ui()
        self.load_fonts()
        
        # Applica tema globale
        apply_theme_colors(self, self.config)
        self._apply_custom_styles()

        self.font_var.trace_add("write", self._on_font_var_changed)
        self.size_var.trace_add("write", self._on_size_var_changed)

        self.update_preview()

        # ---------------- FOCUS ----------------
        self.lift()
        self.focus_force()
        self.after(10, self.focus_force)
        # --------------------------------------

    def _apply_custom_styles(self):
        """Applica panel_fg e font scalato ai widget specifici."""
        def apply(widget):
            try:
                # Applica font scalato a tutti i widget che lo supportano
                widget.configure(font=self._font)
            except:
                pass
            
            # Applica colori specifici per i controlli di input
            if isinstance(widget, (tk.Entry, tk.Listbox, tk.Spinbox)):
                try:
                    widget.configure(bg=self.panel_color, fg=self.panel_fg, 
                                     insertbackground=self.panel_fg, # Cursore per Entry/Spinbox
                                     highlightbackground=self.bg_color,
                                     highlightcolor="#0078d7")
                except:
                    pass
            
            # Colore selezione per Listbox
            if isinstance(widget, tk.Listbox):
                try:
                    widget.configure(selectbackground="#0078d7", selectforeground="white")
                except:
                    pass

            for child in widget.winfo_children():
                apply(child)
        
        apply(self)

    def build_ui(self):

        top = tk.Frame(self, bg=self.bg_color)
        top.pack(fill="x", padx=8, pady=6)

        top.grid_columnconfigure(1, weight=1)

        tk.Label(top, text="Font Family:", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, sticky="w")

        self.entry = tk.Entry(top, textvariable=self.font_var)
        self.entry.grid(row=0, column=1, sticky="we", padx=4)

        tk.Label(top, text="Size:", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=2, sticky="w", padx=(10, 0))

        self.size_spin = tk.Spinbox(
            top,
            from_=1,
            to=200,
            textvariable=self.size_var,
            width=6
        )
        self.size_spin.grid(row=0, column=3, sticky="w")

        # ---------------- FONT LIST ----------------

        list_frame = tk.Frame(self, bg=self.bg_color)
        list_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.font_list = tk.Listbox(list_frame)

        # Scrollbar standard (tk) per coerenza con gli altri form
        scrollbar = tk.Scrollbar(list_frame, command=self.font_list.yview, bg=self.bg_color)
        self.font_list.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.font_list.pack(side="left", fill="both", expand=True)

        self.font_list.bind("<<ListboxSelect>>", self.on_list_select)

        # ---------------- PREVIEW ----------------

        tk.Label(self, text="Preview:", bg=self.bg_color, fg=self.fg_color).pack(anchor="w", padx=8)

        self.preview_label = tk.Label(
            self,
            text="The quick brown fox jumps over the lazy dog",
            bg=self.panel_color,
            fg=self.panel_fg,
            relief="solid",
            borderwidth=1,
            pady=10
        )
        self.preview_label.pack(fill="x", padx=(12, 8), pady=(0, 8))

        # ---------------- BUTTONS ----------------

        btn_frame = tk.Frame(self, bg=self.bg_color)
        btn_frame.pack(pady=6)

        tk.Button(btn_frame, text="Apply", command=self.apply, width=10).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=4)

    # --------------------------------------------------

    def load_fonts(self):

        try:
            self.fonts = sorted(set(font.families()))
        except Exception as e:
            print(f"Error loading fonts: {e}")
            self.fonts = ["Arial", "Courier New", "Times New Roman", "Segoe UI"]

        if not self.fonts:
            self.fonts = ["Arial", "Courier New", "Times New Roman", "Segoe UI"]

        for f in self.fonts:
            self.font_list.insert(tk.END, f)

        # select initial font
        current = self.font_var.get()

        if current in self.fonts:
            idx = self.fonts.index(current)
            self.center_list_on(idx)
            self.font_list.selection_set(idx)

    # --------------------------------------------------

    def center_list_on(self, index):

        visible = 10 # Valore approssimativo
        total = len(self.fonts)

        start = max(0, index - visible // 2)

        if total > 0:
            self.font_list.yview_moveto(start / total)

    # --------------------------------------------------

    def _on_font_var_changed(self, name, index, mode):
        self.on_font_entry_changed()

    def _on_size_var_changed(self, name, index, mode):
        self.update_preview()

    def on_font_entry_changed(self):

        self.font_list.selection_clear(0, tk.END)

        typed = self.font_var.get().lower()

        if not typed:
            self.update_preview()
            return

        for idx, f in enumerate(self.fonts):

            if f.lower().startswith(typed):

                self.font_list.selection_set(idx)

                self.center_list_on(idx)

                break

        self.update_preview()

    # --------------------------------------------------

    def on_list_select(self, event):

        sel = self.font_list.curselection()

        if sel:
            name = self.font_list.get(sel[0])
            self.font_var.set(name)
            self.font_list.selection_clear(0, tk.END)
            self.update_preview()

    # --------------------------------------------------

    def update_preview(self):

        try:
            f = (self.font_var.get(), int(self.size_var.get()))
            self.preview_label.configure(font=f)
        except:
            pass

    # -------------------------------------------------

    def apply(self):

        self.config["font_family"] = self.font_var.get()
        self.config["font_size"] = int(self.size_var.get())

        save_config(self.config)

        if self.apply_callback:
            self.apply_callback(self.config)


        self.destroy()
