import tkinter as tk
from tkinter import font, messagebox
from config_manager import save_config


class FontSelectorForm:

    _instance = None

    def __init__(self, root, config, apply_callback):

        if FontSelectorForm._instance and FontSelectorForm._instance.root.winfo_exists():
            FontSelectorForm._instance.root.deiconify()
            FontSelectorForm._instance.root.lift()
            return

        FontSelectorForm._instance = self

        import os
        import sys

        self.root = tk.Toplevel(root)
        self.root.title("Font Selector")
        self.root.attributes("-topmost", True)
        self.root.minsize(420, 340)

        # ---------------- ICON ----------------
        try:
            # base path = directory of main.py
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
            icon_path_win = os.path.join(base_path, "resources", "josm_tagger.ico")
            icon_path_linux = os.path.join(base_path, "resources", "josm_tagger.png")

            if os.name == "nt" and os.path.exists(icon_path_win):
                self.root.iconbitmap(icon_path_win)
            elif os.path.exists(icon_path_linux):
                icon_img = tk.PhotoImage(file=icon_path_linux)
                self.root.iconphoto(True, icon_img)
                self._icon_img = icon_img  # avoid GC
        except:
            pass
        # --------------------------------------

        self.config = config
        self.apply_callback = apply_callback

        self.font_var = tk.StringVar(value=self.config.get("font_family", "Segoe UI"))
        self.size_var = tk.IntVar(value=self.config.get("font_size", 10))

        self.build_ui()
        self.load_fonts()

        self.font_var.trace_add("write", self._on_font_var_changed)
        self.size_var.trace_add("write", self._on_size_var_changed)

        self.update_preview()

    # --------------------------------------------------

    def build_ui(self):

        top = tk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=6)

        tk.Label(top, text="Font Family:").pack(anchor="w")

        self.entry = tk.Entry(top, textvariable=self.font_var)
        self.entry.pack(fill="x")

        tk.Label(top, text="Font Size:").pack(anchor="w", pady=(6, 0))

        self.size_spin = tk.Spinbox(
            top,
            from_=1,
            to=200,
            textvariable=self.size_var,
            width=6
        )
        self.size_spin.pack(anchor="w")

        # ---------------- FONT LIST ----------------

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.font_list = tk.Listbox(list_frame)

        scrollbar = tk.Scrollbar(list_frame, command=self.font_list.yview)
        self.font_list.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.font_list.pack(side="left", fill="both", expand=True)

        self.font_list.bind("<<ListboxSelect>>", self.on_list_select)

        # ---------------- PREVIEW ----------------

        tk.Label(self.root, text="Preview:").pack(anchor="w", padx=8)

        self.preview_label = tk.Label(
            self.root,
            text="The quick brown fox jumps over the lazy dog"
        )
        self.preview_label.pack(fill="x", padx=8, pady=(0, 8))

        # ---------------- BUTTONS ----------------

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=6)

        tk.Button(btn_frame, text="Apply", command=self.apply).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", command=self.root.destroy).pack(side="left", padx=4)

    # --------------------------------------------------

    def load_fonts(self):

        self.fonts = sorted(set(font.families()))

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

        visible = int(self.font_list['height'])
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

        typed = self.font_var.get().lower()

        if not typed:
            self.update_preview()
            return

        for idx, f in enumerate(self.fonts):

            if f.lower().startswith(typed):

                self.font_list.selection_clear(0, tk.END)
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
            self.update_preview()

    # --------------------------------------------------

    def update_preview(self):

        try:
            f = (self.font_var.get(), int(self.size_var.get()))
            self.preview_label.configure(font=f)
        except:
            pass

    # --------------------------------------------------

    def apply(self):

        self.config["font_family"] = self.font_var.get()
        self.config["font_size"] = int(self.size_var.get())

        save_config(self.config)

        if self.apply_callback:
            self.apply_callback(self.config)


        self.root.destroy()