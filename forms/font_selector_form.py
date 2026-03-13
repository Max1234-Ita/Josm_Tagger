import tkinter as tk
from tkinter import font
from forms.base_form import BaseForm


class FontSelectorForm(BaseForm):

    def __init__(self, parent, config, callback):

        super().__init__(parent, "font_selector")

        self.title("Font")

        self.config = config
        self.callback = callback

        self.build_ui()

    def build_ui(self):

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(frame, text="Font family").pack(anchor="w")

        self.search = tk.StringVar()
        self.search.trace_add("write", self.filter_fonts)

        entry = tk.Entry(frame, textvariable=self.search)
        entry.pack(fill="x", pady=4)

        list_frame = tk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_frame)

        scrollbar = tk.Scrollbar(list_frame)

        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True, side="left")

        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        tk.Label(frame, text="Font size").pack(anchor="w", pady=(10,0))

        self.size = tk.Spinbox(frame, from_=6, to=40)
        self.size.delete(0, "end")
        self.size.insert(0, self.config["font_size"])
        self.size.pack(anchor="w")

        apply_btn = tk.Button(frame, text="Apply", command=self.apply_font)
        apply_btn.pack(pady=8)

        self.all_fonts = sorted(font.families())
        self.filtered = self.all_fonts.copy()

        for f in self.filtered:
            self.listbox.insert("end", f)

    def filter_fonts(self, *args):

        text = self.search.get().lower()

        self.listbox.delete(0, "end")

        self.filtered = []

        for f in self.all_fonts:
            if text in f.lower():
                self.filtered.append(f)
                self.listbox.insert("end", f)

    def apply_font(self):

        sel = self.listbox.curselection()

        if not sel:
            return

        family = self.listbox.get(sel[0])
        size = int(self.size.get())

        self.config["font_family"] = family
        self.config["font_size"] = size

        self.callback(self.config)

        self.destroy()