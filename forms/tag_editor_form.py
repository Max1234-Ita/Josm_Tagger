import tkinter as tk
from forms.base_form import BaseForm


class TagEditorForm(BaseForm):

    def __init__(self, parent, codes):

        super().__init__(parent, "tag_editor")

        self.title("Tags & Codes")

        self.codes = codes

        self.build_ui()

    def build_ui(self):

        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(main, text="Codes").pack(anchor="w")

        list_frame = tk.Frame(main)
        list_frame.pack(fill="both", expand=True)

        self.code_list = tk.Listbox(list_frame)

        scrollbar = tk.Scrollbar(list_frame)

        scrollbar.pack(side="right", fill="y")
        self.code_list.pack(fill="both", expand=True, side="left")

        self.code_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.code_list.yview)

        for c in sorted(self.codes):
            self.code_list.insert("end", c)