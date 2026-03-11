import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from codes_manager import save_codes


class TagEditorForm(tk.Toplevel):

    def __init__(self, parent, codes):

        super().__init__(parent)

        self.codes = codes

        self.title("Tags & Codes")
        self.geometry("650x420")

        self.build_ui()
        self.populate()

    def build_ui(self):

        left = tk.Frame(self)
        left.pack(side="left", fill="y", padx=5, pady=5)

        list_frame = tk.Frame(left)
        list_frame.pack(fill="y", expand=True)

        self.code_list = tk.Listbox(list_frame, width=25)

        scroll = tk.Scrollbar(list_frame)

        scroll.pack(side="right", fill="y")
        self.code_list.pack(side="left", fill="y", expand=True)

        self.code_list.config(yscrollcommand=scroll.set)
        scroll.config(command=self.code_list.yview)

        self.code_list.bind("<<ListboxSelect>>", self.load_code)

        right = tk.Frame(self)
        right.pack(fill="both", expand=True, padx=5, pady=5)

        tree_frame = tk.Frame(right)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("key", "value"),
            show="headings"
        )

        self.tree.heading("key", text="Key")
        self.tree.heading("value", text="Value")

        tree_scroll = tk.Scrollbar(tree_frame)

        tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.config(yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.tree.yview)

        bottom = tk.Frame(self)
        bottom.pack(fill="x", pady=5)

        tk.Button(bottom, text="Add Code", command=self.add_code).pack(side="left")
        tk.Button(bottom, text="Delete Code", command=self.delete_code).pack(side="left")
        tk.Button(bottom, text="Add Tag", command=self.add_tag).pack(side="left")
        tk.Button(bottom, text="Delete Tag", command=self.delete_tag).pack(side="left")

        tk.Button(bottom, text="Save", command=self.save).pack(side="right")

    def populate(self):

        self.code_list.delete(0, tk.END)

        for c in sorted(self.codes):
            self.code_list.insert(tk.END, c)

    def load_code(self, event):

        sel = self.code_list.curselection()

        if not sel:
            return

        code = self.code_list.get(sel[0])

        self.tree.delete(*self.tree.get_children())

        for t in self.codes[code]:
            self.tree.insert("", "end", values=(t["key"], t["value"]))

    def add_code(self):

        code = simpledialog.askstring("Code", "Mnemonic code:")

        if not code:
            return

        self.codes[code] = []
        self.populate()

    def delete_code(self):

        sel = self.code_list.curselection()

        if not sel:
            return

        code = self.code_list.get(sel[0])

        del self.codes[code]

        self.populate()
        self.tree.delete(*self.tree.get_children())

    def add_tag(self):

        key = simpledialog.askstring("Key", "Tag key:")
        value = simpledialog.askstring("Value", "Tag value:")

        if not key or not value:
            return

        sel = self.code_list.curselection()

        if not sel:
            return

        code = self.code_list.get(sel[0])

        self.codes[code].append({"key": key, "value": value})

        self.load_code(None)

    def delete_tag(self):

        item = self.tree.selection()

        if not item:
            return

        index = self.tree.index(item)

        sel = self.code_list.curselection()
        code = self.code_list.get(sel[0])

        del self.codes[code][index]

        self.load_code(None)

    def save(self):

        save_codes(self.codes)
        messagebox.showinfo("Saved", "codes.json updated")