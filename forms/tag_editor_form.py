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
            inst.root.focus_force()
            if preload_code:
                inst.load_code(preload_code)
            return

        TagEditorForm._instance = self

        self.root = tk.Toplevel(root)
        self.root.title("Tag Editor")
        self.root.attributes("-topmost", True)
        self.root.attributes("-toolwindow", True)
        self.root.minsize(450, 300)

        # Allow full resizing
        self.root.resizable(True, True)

        # ---------------- Icon ----------------
        import os, sys

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
        self._last_geometry = None

        # Declare UI attributes
        self.code_var = None
        self.key_var = None
        self.value_var = None
        self.entry_code = None
        self.new_btn = None
        self.rename_btn = None
        self.code_list = None
        self.context_menu = None
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
        self.apply_theme()

        # ---------------- Focus management ----------------
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # opzionale: mantiene il focus finché la finestra è attiva
        try:
            self.root.grab_set()
        except:
            pass

        if self.preload_code:
            self.load_code(self.preload_code)

    def _on_configure(self, event=None):
        """Prevent window maximize"""
        # Get current state
        state = self.root.state()

        # If window is zoomed (maximized), restore to normal
        if state == 'zoomed':
            if self._last_geometry:
                self.root.geometry(self._last_geometry)
            else:
                self.root.geometry("750x450")
        else:
            # Save geometry for restoration
            self._last_geometry = self.root.geometry()

    def _check_maximize(self):
        """Continuously check if window is maximized and prevent it"""
        try:
            if self.root.winfo_exists():
                state = self.root.state()
                if state == 'zoomed':
                    # Restore to last saved geometry
                    self.root.state('normal')
                    if self._last_geometry:
                        self.root.geometry(self._last_geometry)
                    else:
                        self.root.geometry("750x450")
                else:
                    # Save current geometry
                    self._last_geometry = self.root.geometry()

                # Check again in 50ms
                self.root.after(50, self._check_maximize)
        except:
            pass

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

        # Removed rename_btn as it's now in context menu

        # PanedWindow to split left and right
        paned = tk.PanedWindow(self.root, orient="horizontal", sashrelief="raised")
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        # Left side: Code list
        left_frame = tk.Frame(paned)

        tk.Label(left_frame, text="Codes").pack(anchor="w", padx=4)

        list_container = tk.Frame(left_frame)
        list_container.pack(fill="both", expand=True)

        self.code_list = tk.Listbox(list_container)
        self.code_list.pack(side="left", fill="both", expand=True)

        scrollbar_left = tk.Scrollbar(list_container, command=self.code_list.yview)
        scrollbar_left.pack(side="right", fill="y")
        self.code_list.config(yscrollcommand=scrollbar_left.set)

        self.code_list.bind("<<ListboxSelect>>", self.on_code_select)
        self.code_list.bind("<Button-3>", self.show_context_menu)

        paned.add(left_frame, minsize=150)

        # Right side: Existing controls
        right_frame = tk.Frame(paned)

        # Tag list
        frame_list = tk.Frame(right_frame)
        frame_list.pack(fill="both", expand=True)

        tk.Label(frame_list, text="Tags").pack(anchor="w", padx=4)

        tag_container = tk.Frame(frame_list)
        tag_container.pack(fill="both", expand=True)

        self.tag_list = tk.Listbox(tag_container)
        self.tag_list.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(tag_container, command=self.tag_list.yview)
        scrollbar.pack(side="right", fill="y")

        self.tag_list.config(yscrollcommand=scrollbar.set)

        self.tag_list.bind("<<ListboxSelect>>", self.on_tag_select)

        # Entry frame
        entry_frame = tk.Frame(right_frame)
        entry_frame.pack(fill="x", padx=4, pady=6)

        tk.Label(entry_frame, text="Key:").grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.key_var = tk.StringVar()
        self.entry_key = tk.Entry(entry_frame, textvariable=self.key_var)
        self.entry_key.grid(row=0, column=1, sticky="we", padx=(4, 4))

        tk.Label(entry_frame, text="Value:").grid(row=0, column=2, sticky="w", padx=(4, 4))

        self.value_var = tk.StringVar()
        self.entry_value = tk.Entry(entry_frame, textvariable=self.value_var)
        self.entry_value.grid(row=0, column=3, sticky="we", padx=(4, 0))

        self.entry_value.bind("<Return>", lambda e: self.add_tag())

        entry_frame.columnconfigure(1, weight=1)
        entry_frame.columnconfigure(3, weight=1)

        # Button frame
        btn_frame = tk.Frame(right_frame)
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

        paned.add(right_frame, minsize=300)

        # Context menu for code list
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Rename", command=self.context_rename)
        self.context_menu.add_command(label="Delete", command=self.context_delete)

        # Initialize code list
        self.update_code_list()

    # ---------------- Code list methods ----------------
    def update_code_list(self, filtered=None):
        self.code_list.delete(0, tk.END)
        codes = filtered if filtered is not None else sorted(self.codes.keys())
        for c in codes:
            self.code_list.insert(tk.END, c)

    def on_code_select(self, event=None):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        # Temporarily remove trace to avoid recursion
        self.code_var.trace_remove("write", self._trace_id)
        self.code_var.set(code)
        self._trace_id = self.code_var.trace_add("write", self.auto_load_code)
        self.load_code(code)

    def show_context_menu(self, event):
        index = self.code_list.nearest(event.y)
        if index < 0:
            return
        self.code_list.selection_clear(0, tk.END)
        self.code_list.selection_set(index)
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def context_rename(self):
        sel = self.code_list.curselection()
        if not sel:
            return
        old_code = self.code_list.get(sel[0])
        new_name = simpledialog.askstring(
            "Rename Code",
            "Enter new code name:",
            initialvalue=old_code,
            parent=self.root
        )
        if not new_name or new_name.strip() == "":
            return
        new_name = new_name.strip()
        if new_name == old_code:
            return
        if new_name in self.codes:
            messagebox.showwarning(
                "Warning",
                "Code name already exists",
                parent=self.root
            )
            return
        # Rename
        self.codes[new_name] = self.codes.pop(old_code)
        if self.current_code == old_code:
            self.current_code = new_name
            self.code_var.set(new_name)
        save_codes(self.codes)
        if self.on_save_callback:
            self.on_save_callback()
        self.update_code_list()
        messagebox.showinfo(
            "Info",
            f"Code renamed to '{new_name}'",
            parent=self.root
        )

    def context_delete(self):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        confirm = messagebox.askyesno(
            "Delete",
            f"Delete code '{code}'?",
            parent=self.root
        )
        if not confirm:
            return
        if code in self.codes:
            del self.codes[code]
            save_codes(self.codes)
            if self.on_save_callback:
                self.on_save_callback()
            self.update_code_list()
            if self.current_code == code:
                self.current_code = None
                self.tag_list.delete(0, tk.END)
                self.key_var.set("")
                self.value_var.set("")

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

        self.update_code_list()

    def load_code(self, code):
        if code not in self.codes:
            self.codes[code] = []

        self.current_code = code
        self.code_var.set(code)

        self.update_tag_list()
        # Keep focus on the code entry field instead of moving to key field
        self.entry_code.focus_set()

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

    # Removed rename_code method as it's now context_rename

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
            self.update_code_list()
            self.tag_list.delete(0, tk.END)
            self.key_var.set("")
            self.value_var.set("")
            return

        # Filter values
        filtered = sorted([c for c in self.codes if c.lower().startswith(code.lower())])
        self.entry_code['values'] = filtered
        self.update_code_list(filtered)

        # Load if exact match
        if code in self.codes:
            self.load_code(code)
        else:
            # Code doesn't exist - clear tags and fields
            self.tag_list.delete(0, tk.END)
            self.key_var.set("")
            self.value_var.set("")
            self.current_code = None
