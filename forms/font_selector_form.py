import tkinter as tk
from tkinter import font


class FontSelectorForm(tk.Toplevel):

    def __init__(self, parent, config, save_callback):

        super().__init__(parent)

        self.config_data = config
        self.save_callback = save_callback

        self.title("Select Font")
        self.geometry("420x520")

        self.font_family = tk.StringVar(value=config["font_family"])
        self.font_size = tk.IntVar(value=config["font_size"])
        self.search_var = tk.StringVar()

        self.build_ui()
        self.populate_fonts()

    def build_ui(self):

        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", padx=8, pady=5)

        tk.Label(search_frame, text="Search").pack(anchor="w")

        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill="x")

        search_entry.bind("<KeyRelease>", self.filter_fonts)

        # font list

        list_frame = tk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=8)

        self.font_list = tk.Listbox(list_frame)

        scroll = tk.Scrollbar(list_frame)

        scroll.pack(side="right", fill="y")
        self.font_list.pack(side="left", fill="both", expand=True)

        self.font_list.config(yscrollcommand=scroll.set)
        scroll.config(command=self.font_list.yview)

        self.font_list.bind("<<ListboxSelect>>", self.update_preview)

        # size

        size_frame = tk.Frame(self)
        size_frame.pack(fill="x", padx=8, pady=6)

        tk.Label(size_frame, text="Size").pack(anchor="w")

        self.size_spin = tk.Spinbox(
            size_frame,
            from_=6,
            to=40,
            textvariable=self.font_size,
            width=5,
            command=self.update_preview
        )

        self.size_spin.pack(anchor="w")

        # preview

        preview_frame = tk.Frame(self)
        preview_frame.pack(fill="x", padx=8, pady=10)

        tk.Label(preview_frame, text="Preview").pack(anchor="w")

        self.preview_label = tk.Label(
            preview_frame,
            text="The quick brown fox jumps over the lazy dog"
        )

        self.preview_label.pack(fill="x")

        # buttons

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", pady=10, padx=8)

        tk.Button(btn_frame, text="Apply", command=self.apply).pack(side="right")

    def populate_fonts(self):

        self.all_fonts = list(font.families())
        self.all_fonts.sort()

        self.font_list.delete(0, tk.END)

        for f in self.all_fonts:
            self.font_list.insert(tk.END, f)

    def filter_fonts(self, event=None):

        text = self.search_var.get().lower()

        self.font_list.delete(0, tk.END)

        for f in self.all_fonts:

            if text in f.lower():
                self.font_list.insert(tk.END, f)

    def update_preview(self, event=None):

        sel = self.font_list.curselection()

        if sel:
            self.font_family.set(self.font_list.get(sel[0]))

        f = (self.font_family.get(), self.font_size.get())

        self.preview_label.config(font=f)

    def apply(self):

        sel = self.font_list.curselection()

        if sel:
            self.font_family.set(self.font_list.get(sel[0]))

        self.config_data["font_family"] = self.font_family.get()
        self.config_data["font_size"] = int(self.font_size.get())

        self.save_callback(self.config_data)

        self.destroy()