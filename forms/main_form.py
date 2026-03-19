import tkinter as tk
import threading
import keyboard

from config_manager import load_config, save_config
from codes_manager import load_codes
from josm_interface import send_tags
from forms.tag_editor_form import TagEditorForm
from forms.font_selector_form import FontSelectorForm


class MainForm:

    def __init__(self, root):

        self.root = root
        self.config = load_config()
        self.codes = load_codes()

        root.title("JOSM Tagger")
        root.geometry("560x520")
        root.attributes("-topmost", True)

        self.filtered_codes = []

        self.build_menu()
        self.build_ui()
        self.register_hotkey()

        self.apply_font()
        self.update_list()

    # ---------------- MENU ----------------
    def build_menu(self):

        self.menubar = tk.Menu(self.root)

        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Reload tags", command=self.reload_codes)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Tags & Codes", command=self.open_editor)

        view_menu = tk.Menu(self.menubar, tearoff=0)
        view_menu.add_command(label="Font", command=self.select_font)

        self.menubar.add_cascade(label="File", menu=file_menu)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        self.menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=self.menubar)

    # ---------------- UI ----------------
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

        # --- LISTA CODICI ---
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

        # --- PREVIEW ---
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

    # ---------------- FONT ----------------
    def apply_font(self):

        f = (self.config.get("font_family", "Segoe UI"),
             int(self.config.get("font_size", 10)))

        self.root.option_add("*Font", f)

        def apply(widget):
            try:
                widget.configure(font=f)
            except:
                pass
            for c in widget.winfo_children():
                apply(c)

        apply(self.root)

    def select_font(self):
        FontSelectorForm(self.root, self.config, self.apply_font_config)

    def apply_font_config(self, new_config):
        self.config = new_config
        save_config(self.config)
        self.apply_font()

    # ---------------- HOTKEY ----------------
    def register_hotkey(self):
        keyboard.add_hotkey(
            self.config.get("hotkey", "ctrl+num 0"),
            lambda: self.root.after(0, self.hotkey_trigger)
        )

    def hotkey_trigger(self):
        self.focus_input()

    def focus_input(self):

        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

        self.root.after(10, self._force_focus)
        self.root.after(50, self._force_focus)

        self.flash_window()

    def _force_focus(self):
        try:
            self.root.focus_force()
            self.entry.focus_set()
            self.entry.icursor(tk.END)
            self.entry.select_range(0, tk.END)
        except:
            pass

    def flash_window(self):
        try:
            self.root.configure(highlightthickness=3, highlightbackground="red")
            self.root.after(200, lambda: self.root.configure(highlightthickness=0))
        except:
            pass

    # ---------------- LOGICA CODICI ----------------
    def update_list(self):

        self.code_list.delete(0, tk.END)

        self.filtered_codes = sorted(self.codes)

        for c in self.filtered_codes:
            self.code_list.insert(tk.END, c)

    def filter_codes(self, *args):

        text = self.code_var.get().lower()

        self.code_list.delete(0, tk.END)

        self.filtered_codes = sorted(
            [c for c in self.codes if text in c.lower()]
        )

        for c in self.filtered_codes:
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

        for t in self.codes.get(code, []):
            self.preview.insert(tk.END, f"{t['key']} = {t['value']}")

    # ---------------- APPLY ----------------
    def apply_from_list(self, event=None):

        sel = self.code_list.curselection()

        if not sel:
            return

        code = self.code_list.get(sel[0])
        self.send(code)
        self._reset_input()

    def apply_code(self, event=None):

        code = self.code_var.get().strip()

        if code in self.codes:
            self.send(code)
            self._reset_input()
            return

        sel = self.code_list.curselection()

        if sel:
            self.send(self.code_list.get(sel[0]))
            self._reset_input()
            return

        if self.filtered_codes:
            self.send(self.filtered_codes[0])
            self._reset_input()

    def _reset_input(self):
        self.code_var.set("")
        self.preview.delete(0, tk.END)

    def send(self, code):

        threading.Thread(
            target=send_tags,
            args=(self.codes[code],),
            daemon=True
        ).start()

    # ---------------- ALTRO ----------------
    def reload_codes(self):
        self.codes = load_codes()
        self.update_list()

    def open_editor(self):
        TagEditorForm(self.root, self.codes)