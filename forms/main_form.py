import tkinter as tk
import threading
import keyboard

from config_manager import load_config
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

        self.tag_editor = None

        self.build_menu()
        self.build_ui()
        self.apply_font()
        self.update_list()
        self.register_hotkey()

        root.bind("<<Hotkey>>", self.focus_input_event)

    # ---------------- Menu ----------------
    def build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Reload codes", command=self.reload_codes)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Tags & Codes", command=self.open_editor)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Font", command=self.select_font)

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    # ---------------- UI ----------------
    def build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=6, pady=6)

        tk.Label(top, text="Code").pack(side="left")

        self.code_var = tk.StringVar()
        self.code_var.trace_add("write", self.filter_codes)

        self.entry = tk.Entry(top, textvariable=self.code_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        self.entry.bind("<Return>", self.apply_code)
        self.entry.bind("<Down>", self.focus_list)

        self.apply_btn = tk.Button(top, text="Apply", command=self.apply_code)
        self.apply_btn.pack(side="right")

        # Lista codici
        frame_list = tk.Frame(self.root)
        frame_list.pack(fill="both", expand=True, padx=6)

        self.code_list = tk.Listbox(frame_list)
        self.code_list.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side="right", fill="y")

        self.code_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.code_list.yview)

        self.code_list.bind("<<ListboxSelect>>", self.update_preview)
        self.code_list.bind("<Double-Button-1>", self.apply_from_list)
        self.code_list.bind("<Return>", self.apply_from_list)
        self.code_list.bind("<Button-3>", self.show_context_menu)

        # menu contestuale
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Use", command=self.context_use)
        self.context_menu.add_command(label="Edit", command=self.context_edit)

        # Preview
        frame_preview = tk.Frame(self.root)
        frame_preview.pack(fill="both", padx=6, pady=6)

        tk.Label(frame_preview, text="Tag preview").pack(anchor="w")

        frame_preview_list = tk.Frame(frame_preview)
        frame_preview_list.pack(fill="both", expand=True)

        self.preview = tk.Listbox(frame_preview_list, height=6)
        self.preview.pack(side="left", fill="both", expand=True)

        scroll_preview = tk.Scrollbar(frame_preview_list)
        scroll_preview.pack(side="right", fill="y")

        self.preview.config(yscrollcommand=scroll_preview.set)
        scroll_preview.config(command=self.preview.yview)

    # ---------------- Contestuale ----------------
    def show_context_menu(self, event):
        index = self.code_list.nearest(event.y)
        if index < 0:
            return
        self.code_list.selection_clear(0, tk.END)
        self.code_list.selection_set(index)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def context_use(self):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        self.send(code)

    def context_edit(self):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])

        if self.tag_editor and self.tag_editor.root.winfo_exists():
            self.tag_editor.root.deiconify()
            self.tag_editor.root.lift()
            self.tag_editor.load_code(code)
        else:
            self.tag_editor = TagEditorForm(
                self.root,
                self.codes,
                self.reload_codes,
                self.config,
                preload_code=code
            )

    # ---------------- Hotkey ----------------
    def register_hotkey(self):
        keyboard.add_hotkey(
            self.config.get("hotkey", "ctrl+num 0"),
            self.hotkey_trigger
        )

    def hotkey_trigger(self):
        self.root.event_generate("<<Hotkey>>", when="tail")

    def focus_input_event(self, event):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

    # ---------------- Lista e Preview ----------------
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

    def update_preview(self, event=None):
        self.preview.delete(0, tk.END)
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        for tag in self.codes.get(code, []):
            self.preview.insert(tk.END, f"{tag['key']} = {tag['value']}")

    def focus_list(self, event):
        if self.code_list.size() == 0:
            return
        self.code_list.focus_set()
        self.code_list.selection_set(0)

    # ---------------- Apply ----------------
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

    def send(self, code):
        threading.Thread(
            target=send_tags,
            args=(self.codes[code],),
            daemon=True
        ).start()
        self.code_var.set("")

    # ---------------- Reload / Editor ----------------
    def reload_codes(self):
        self.codes = load_codes()
        self.update_list()

    def open_editor(self):
        if self.tag_editor and self.tag_editor.root.winfo_exists():
            self.tag_editor.root.deiconify()
            self.tag_editor.root.lift()
        else:
            self.tag_editor = TagEditorForm(
                self.root,
                self.codes,
                self.reload_codes,
                self.config
            )

    # ---------------- Font ----------------
    def select_font(self):
        FontSelectorForm(
            self.root,
            self.config,
            self.apply_font
        )

    def apply_font(self, *args):
        font_conf = (self.config["font_family"], self.config["font_size"])
        self.root.option_add("*Font", font_conf)

        def apply(widget):
            try:
                widget.configure(font=font_conf)
            except:
                pass
            for child in widget.winfo_children():
                apply(child)

        apply(self.root)