import tkinter as tk

from tkinter import font
from forms.font_selector_form import FontSelectorForm

import threading
import keyboard

from config_manager import load_config, save_config
from codes_manager import load_codes
from josm_interface import send_tags
from forms.tag_editor_form import TagEditorForm


class MainForm:

    def __init__(self, root):

        self.root = root
        self.config = load_config()
        self.codes = load_codes()

        root.title("JOSM Tagger")
        root.geometry("560x520")

        self.filtered_codes = []

        self.build_menu()
        self.build_ui()
        self.register_hotkey()

        self.apply_font()
        self.update_list()

    def build_menu(self):

        self.menubar = tk.Menu(self.root)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Reload tags", command=self.reload_codes)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.edit_menu.add_command(label="Tags & Codes", command=self.open_editor)

        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.view_menu.add_command(label="Font", command=self.select_font)
        self.view_menu.add_command(label="UI Scale", command=self.select_ui_scale)

        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menubar.add_cascade(label="View", menu=self.view_menu)

        self.root.config(menu=self.menubar)

    def build_ui(self):

        top = tk.Frame(self.root)
        top.pack(fill="x", padx=6, pady=6)

        tk.Label(top, text="Code:").pack(side="left")

        self.code_var = tk.StringVar()
        self.code_var.trace_add("write", self.filter_codes)

        self.entry = tk.Entry(top, textvariable=self.code_var)
        self.entry.pack(fill="x", expand=True, side="left", padx=4)

        self.entry.bind("<Return>", self.apply_code)
        self.entry.bind("<Down>", self.focus_list)

        self.apply_button = tk.Button(top, text="Apply", command=self.apply_code)
        self.apply_button.pack(side="right")

        # CODE LIST

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=6)

        self.code_list = tk.Listbox(list_frame)

        scrollbar = tk.Scrollbar(list_frame)

        scrollbar.pack(side="right", fill="y")
        self.code_list.pack(fill="both", expand=True, side="left")

        self.code_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.code_list.yview)

        self.code_list.bind("<<ListboxSelect>>", self.update_preview)
        self.code_list.bind("<Double-Button-1>", self.apply_from_list)
        self.code_list.bind("<Return>", self.apply_from_list)

        # PREVIEW

        preview_frame = tk.Frame(self.root)
        preview_frame.pack(fill="both", expand=False, padx=6, pady=6)

        tk.Label(preview_frame, text="Tag preview").pack(anchor="w")

        preview_inner = tk.Frame(preview_frame)
        preview_inner.pack(fill="both", expand=True)

        self.preview = tk.Listbox(preview_inner, height=6)

        scrollbar_preview = tk.Scrollbar(preview_inner)

        scrollbar_preview.pack(side="right", fill="y")
        self.preview.pack(fill="both", expand=True, side="left")

        self.preview.config(yscrollcommand=scrollbar_preview.set)
        scrollbar_preview.config(command=self.preview.yview)

    def apply_font(self):

        base_size = int(self.config["font_size"] * self.config.get("ui_scale", 1.0))
        f = (self.config["font_family"], base_size)

        # font globale
        self.root.option_add("*Font", f)

        # refresh widget già esistenti
        for w in self.root.winfo_children():
            self._refresh_widget_fonts(w)

    def _refresh_widget_fonts(self, widget):

        try:
            widget.configure(font=(self.config["font_family"], self.config["font_size"]))
        except:
            pass

        for child in widget.winfo_children():
            self._refresh_widget_fonts(child)

    def select_font(self):

        FontSelectorForm(
            self.root,
            self.config,
            self.apply_font_config
        )

    def apply_font_config(self, new_config):

        from config_manager import save_config

        self.config = new_config

        save_config(self.config)

        self.apply_font()

    def select_ui_scale(self):

        import tkinter.simpledialog as sd

        scale = sd.askfloat(
            "UI Scale",
            "Scale factor (0.5–3.0):",
            initialvalue=self.config.get("ui_scale", 1.0),
            minvalue=0.5,
            maxvalue=3.0
        )

        if scale is None:
            return

        self.config["ui_scale"] = scale
        from config_manager import save_config
        save_config(self.config)

        self.apply_font()  # applica font + scala

    def register_hotkey(self):

        keyboard.add_hotkey(
            self.config.get("hotkey", "ctrl+num 0"),
            self.hotkey_trigger
        )

    def hotkey_trigger(self):

        self.root.after(0, self.focus_input)

    def focus_input(self):

        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

    def update_list(self):

        self.code_list.delete(0, tk.END)

        self.filtered_codes = sorted(self.codes)

        for c in self.filtered_codes:
            self.code_list.insert(tk.END, c)

    def filter_codes(self, *args):

        text = self.code_var.get().lower()

        self.code_list.delete(0, tk.END)

        self.filtered_codes = []

        for c in sorted(self.codes):

            if text in c.lower():
                self.filtered_codes.append(c)
                self.code_list.insert(tk.END, c)

        self.update_preview()

    def focus_list(self, event):

        if self.code_list.size() == 0:
            return

        self.code_list.focus_set()
        self.code_list.selection_set(0)

        self.update_preview()

    def update_preview(self, event=None):

        self.preview.delete(0, tk.END)

        code = None

        sel = self.code_list.curselection()

        if sel:
            code = self.code_list.get(sel[0])

        elif self.filtered_codes:
            code = self.filtered_codes[0]

        if not code:
            return

        for t in self.codes[code]:
            self.preview.insert(tk.END, f"{t['key']} = {t['value']}")

    def apply_from_list(self, event=None):

        sel = self.code_list.curselection()

        if not sel:
            return

        code = self.code_list.get(sel[0])
        self.send(code)

    def apply_code(self, event=None):

        code = self.code_var.get().strip()

        if code in self.codes:
            self.send(code)
            return

        sel = self.code_list.curselection()

        if sel:
            self.send(self.code_list.get(sel[0]))
            return

        if self.filtered_codes:
            self.send(self.filtered_codes[0])

    def send(self, code):

        threading.Thread(
            target=send_tags,
            args=(self.codes[code],),
            daemon=True
        ).start()

    def reload_codes(self):

        self.codes = load_codes()
        self.update_list()

    def open_editor(self):

        TagEditorForm(self.root, self.codes)