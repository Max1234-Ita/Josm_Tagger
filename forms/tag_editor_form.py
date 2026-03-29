import tkinter as tk
import tkinter.ttk as ttk
from tkinter import simpledialog, messagebox
from codes_manager import save_codes


class TagEditorForm:

    _instance = None

    def __init__(self, root, codes, on_save_callback=None, config=None, preload_code=None):
        if TagEditorForm._instance and TagEditorForm._instance.root.winfo_exists():
            inst = TagEditorForm._instance
            inst.root.deiconify()
            inst.root.lift()
            if preload_code:
                inst.load_code(preload_code)
            return

        TagEditorForm._instance = self

        self.root = tk.Toplevel(root)
        self.root.title("Tag Editor")
        self.root.attributes("-topmost", True)
        self.root.minsize(450, 300)

        # ---------------- Icon ----------------
        import os, sys

        # go up to project root (one folder above /forms)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        ico_path = os.path.join(base_dir, "resources", "josm_tagger.ico")
        png_path = os.path.join(base_dir, "resources", "josm_tagger.png")

        try:
            if sys.platform.startswith("win") and os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
            elif os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, self._icon_img)
        except Exception as e:
            print("Failed to set window icon:", e)

        self.codes = codes
        self.on_save_callback = on_save_callback
        self.config = config or {}
        self.preload_code = preload_code

        self.current_code = None

        # Declare attributes
        self._trace_id = None
        self._icon_img = None

        # Declare UI attributes
        self.code_var = None
        self.key_var = None
        self.value_var = None
        self.entry_code = None
        self.new_btn = None
        self.rename_btn = None
        self.tag_list = None
        self.entry_key = None
        self.entry_value = None
        self.add_btn = None
        self.update_btn = None
        self.remove_btn = None
        self.save_btn = None
        self.cancel_btn = None

        self.build_ui()
        self.apply_font()

        if self.preload_code:
            self.load_code(self.preload_code)

    # ---------------- UI ----------------
    def build_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=6, pady=6)

        tk.Label(top_frame, text="Code:").pack(side="left")

        self.code_var = tk.StringVar()
        self.entry_code = ttk.Combobox(top_frame, textvariable=self.code_var)
        self.entry_code.pack(side="left", fill="x", expand=True)

        self._trace_id = self.code_var.trace_add("write", self.auto_load_code)

        self.entry_code['values'] = sorted(self.codes.keys())

        self.new_btn = tk.Button(top_frame, text="New", command=self.new_code)
        self.new_btn.pack(side="right", padx=4)

        self.rename_btn = tk.Button(top_frame, text="Rename", command=self.rename_code)
        self.rename_btn.pack(side="right")

        frame_list = tk.Frame(self.root)
        frame_list.pack(fill="both", expand=True, padx=6, pady=6)

        self.tag_list = tk.Listbox(frame_list)
        self.tag_list.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side="right", fill="y")

        self.tag_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tag_list.yview)

        self.tag_list.bind("<<ListboxSelect>>", self.on_tag_select)

        entry_frame = tk.Frame(self.root)
        entry_frame.pack(fill="x", padx=6, pady=6)

        tk.Label(entry_frame, text="Key:").grid(row=0, column=0, sticky="w")

        self.key_var = tk.StringVar()
        self.entry_key = tk.Entry(entry_frame, textvariable=self.key_var)
        self.entry_key.grid(row=0, column=1, sticky="we", padx=4)

        tk.Label(entry_frame, text="Value:").grid(row=0, column=2, sticky="w")

        self.value_var = tk.StringVar()
        self.entry_value = tk.Entry(entry_frame, textvariable=self.value_var)
        self.entry_value.grid(row=0, column=3, sticky="we", padx=4)

        self.entry_value.bind("<Return>", lambda e: self.add_tag())

        entry_frame.columnconfigure(1, weight=1)
        entry_frame.columnconfigure(3, weight=1)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=6)

        self.add_btn = tk.Button(btn_frame, text="Add", command=self.add_tag)
        self.add_btn.pack(side="left", padx=4)

        self.update_btn = tk.Button(btn_frame, text="Update", command=self.update_tag)
        self.update_btn.pack(side="left", padx=4)

        self.remove_btn = tk.Button(btn_frame, text="Remove", command=self.remove_tag)
        self.remove_btn.pack(side="left", padx=4)

        self.save_btn = tk.Button(btn_frame, text="Save", command=self.save_all)
        self.save_btn.pack(side="left", padx=4)

        self.cancel_btn = tk.Button(btn_frame, text="Cancel", command=self.root.destroy)
        self.cancel_btn.pack(side="left", padx=4)

    # ---------------- Code management ----------------
    def new_code(self):
        code = self.code_var.get().strip()

        if not code:
            messagebox.showwarning(
                "Warning",
                "Enter a code name first",
                parent=self.root
            )
            return

        if code in self.codes:
            messagebox.showwarning(
                "Warning",
                "Code already exists",
                parent=self.root
            )
            return

        self.codes[code] = []
        self.current_code = code

        self.tag_list.delete(0, tk.END)
        self.key_var.set("")
        self.value_var.set("")

        self.entry_key.focus_set()

        # ✅ ADDITION NOTIFICATION
        messagebox.showinfo(
            "New Code",
            f"Code '{code}' created",
            parent=self.root
        )

    def load_code(self, code):
        if code not in self.codes:
            self.codes[code] = []

        self.current_code = code
        self.code_var.set(code)

        self.update_tag_list()
        self.entry_key.focus_set()

    def update_tag_list(self):
        self.tag_list.delete(0, tk.END)

        for t in self.codes.get(self.current_code, []):
            self.tag_list.insert(tk.END, f"{t['key']} = {t['value']}")

    # ---------------- Tag operations ----------------
    def add_tag(self):
        key = self.key_var.get().strip()
        value = self.value_var.get().strip()

        if not key or not value:
            return

        if not self.current_code:
            messagebox.showwarning(
                "No code",
                "Create or select a code first",
                parent=self.root
            )
            return

        if self.current_code not in self.codes:
            self.codes[self.current_code] = []

        for t in self.codes[self.current_code]:
            if t["key"] == key and t["value"] == value:
                messagebox.showwarning(
                    "Warning",
                    "Tag already exists!",
                    parent=self.root
                )
                return

        self.codes[self.current_code].append({"key": key, "value": value})
        self.update_tag_list()

        self.key_var.set("")
        self.value_var.set("")
        self.entry_key.focus_set()

    def update_tag(self):
        sel = self.tag_list.curselection()
        if not sel:
            return

        key = self.key_var.get().strip()
        value = self.value_var.get().strip()

        if not key or not value:
            return

        self.codes[self.current_code][sel[0]] = {"key": key, "value": value}
        self.update_tag_list()

    def remove_tag(self):
        sel = self.tag_list.curselection()
        if not sel:
            return

        self.codes[self.current_code].pop(sel[0])
        self.update_tag_list()

    def on_tag_select(self, event=None):
        sel = self.tag_list.curselection()
        if not sel:
            return

        if not self.current_code:
            return

        if sel[0] >= len(self.codes.get(self.current_code, [])):
            return

        tag = self.codes[self.current_code][sel[0]]
        self.key_var.set(tag["key"])
        self.value_var.set(tag["value"])

    # ---------------- Save ----------------
    def save_all(self):
        save_codes(self.codes)

        if self.on_save_callback:
            self.on_save_callback()

        messagebox.showinfo(
            "Info",
            "Changes saved",
            parent=self.root
        )

    def rename_code(self):
        if not self.current_code:
            messagebox.showwarning(
                "No code",
                "Load or create a code first",
                parent=self.root
            )
            return

        new_name = simpledialog.askstring(
            "Rename Code",
            "Enter new code name:",
            initialvalue=self.current_code,
            parent=self.root
        )

        if not new_name or new_name.strip() == "":
            return

        new_name = new_name.strip()

        if new_name == self.current_code:
            return

        if new_name in self.codes:
            messagebox.showwarning(
                "Warning",
                "Code name already exists",
                parent=self.root
            )
            return

        # Rename: move the tags to new name and delete old
        self.codes[new_name] = self.codes.pop(self.current_code)
        self.current_code = new_name
        self.code_var.set(new_name)

        # Save changes
        save_codes(self.codes)

        if self.on_save_callback:
            self.on_save_callback()

        messagebox.showinfo(
            "Info",
            f"Code renamed to '{new_name}'",
            parent=self.root
        )

    # ---------------- Font ----------------
    def apply_font(self):
        font_conf = (
            self.config.get("font_family", "Segoe UI"),
            self.config.get("font_size", 10)
        )

        self.root.option_add("*Font", font_conf)

        def apply(widget):
            try:
                widget.configure(font=font_conf)
            except:
                pass
            for child in widget.winfo_children():
                apply(child)

        apply(self.root)

    def auto_load_code(self, *args):
        code = self.code_var.get().strip()
        if not code:
            self.entry_code['values'] = sorted(self.codes.keys())
            return

        # Filter values
        filtered = sorted([c for c in self.codes if c.lower().startswith(code.lower())])
        self.entry_code['values'] = filtered

        # Load if exact
        if code in self.codes:
            self.load_code(code)

