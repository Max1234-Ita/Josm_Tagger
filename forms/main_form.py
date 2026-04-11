import os
import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
import threading
import keyboard

from config_manager import load_config, save_config
from codes_manager import load_codes
from josm_interface import send_tags
from forms.tag_editor_form import TagEditorForm
from forms.font_selector_form import FontSelectorForm


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


class Tooltip:
    """Simple tooltip widget for Tkinter"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.showtip)
        widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 8)
        )
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class MainForm:

    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.codes = load_codes()

        root.title("JOSM Tagger")
        root.attributes("-topmost", True)

        # --- THEME ---
        theme = self.config.get("theme", {})
        self.bg_color = theme.get("bg", "#2b2b2b")
        self.fg_color = theme.get("fg", "#ffffff")
        self.root.configure(bg=self.bg_color)

        # --- APP ICON ---
        try:
            icon_path = resource_path("resources/josm_tagger.ico")
            root.iconbitmap(icon_path)
        except:
            pass

        # --- MIN FORM SIZE ---
        self.root.minsize(256, 160)

        # --- DISABLE MAXIMIZE BUTTON ---
        try:
            self.root.attributes("-toolwindow", True)
        except:
            pass

        # --- GEOMETRY ---
        self.apply_geometry()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Declare attributes
        self.filtered_codes = []
        self._trace_id = None
        self.code_var = None
        self.entry = None
        self.apply_button = None
        self.code_list = None
        self.preview = None
        self.context_menu = None
        self.menubar = None
        self.preview_frame = None
        self.paned = None
        self.toggle_button = None
        self.expand_image = None
        self.collapse_image = None

        # Stato pannello inferiore
        self.preview_expanded = self.config.get("preview_expanded", True)
        self.preview_expanded_height = self.config.get("preview_expanded_height", 120)
        self.preview_height = self.config.get("preview_height", 150)
        self.upper_height = self.config.get("upper_height", None)

        self.build_menu()
        self.build_ui()
        self.register_hotkey()
        self.apply_font()
        self.update_list()

    # ---------------------------------------------------------
    # GEOMETRY
    # ---------------------------------------------------------
    def apply_geometry(self):
        geom = self.config.get("geometry", {}).get("main_form")
        if geom:
            try:
                x = geom.get("x", 100)
                y = geom.get("y", 100)
                w = geom.get("w", 560)
                h = geom.get("h", 520)
                self.root.geometry(f"{w}x{h}+{x}+{y}")
                return
            except:
                pass
        self.root.geometry("560x520")

    def save_geometry(self):
        """
        Salva solo la geometria della finestra principale (posizione e dimensioni).
        Non modifica altre impostazioni del config.
        """
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        if "geometry" not in self.config:
            self.config["geometry"] = {}

        self.config["geometry"]["main_form"] = {
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def save_config(self):
        """
        Salva lo stato del pannello inferiore e le altezze dei pannelli.
        """
        self.config["preview_expanded"] = self.preview_expanded
        self.config["preview_height"] = self.preview_height
        self.config["upper_height"] = self.upper_height

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

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

        about_menu = tk.Menu(self.menubar, tearoff=0)
        about_menu.add_command(label='About', command=self.show_about)

        self.menubar.add_cascade(label="File", menu=file_menu)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        self.menubar.add_cascade(label="View", menu=view_menu)
        self.menubar.add_cascade(label="   ?", menu=about_menu)

        self.root.config(menu=self.menubar)

    # ---------------- UI ----------------
    def build_ui(self):
        # --- TOP PANEL ---
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=6, pady=6)

        tk.Label(top, text="Code:").pack(side="left")

        self.code_var = tk.StringVar()
        self._trace_id = self.code_var.trace_add("write", self.filter_codes)

        self.entry = ttk.Combobox(top, textvariable=self.code_var, width=10)
        self.entry.pack(fill="x", expand=True, side="left", padx=(4, 4))
        self.entry.bind("<Return>", self.apply_code)
        self.entry.bind("<Down>", self.focus_list)
        self.entry.bind("<Escape>", self.clear_input)

        self.apply_button = tk.Button(top, text="Apply", command=self.apply_code, width=6)
        self.apply_button.pack(side="right")

        # --- PANED WINDOW (SOLO 2 PANNELLI) ---
        self.paned = tk.PanedWindow(self.root, orient="vertical", sashrelief="raised")
        self.paned.pack(fill="both", expand=True, padx=6, pady=6)

        # --- PANNELLO SUPERIORE (lista codici + header preview) ---
        upper_frame = tk.Frame(self.paned)

        # LISTA CODICI
        list_frame = tk.Frame(upper_frame)
        list_frame.pack(fill="both", expand=True)

        self.code_list = tk.Listbox(list_frame, height=4)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.code_list.pack(fill="both", expand=True, side="left")
        self.code_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.code_list.yview)

        self.code_list.bind("<<ListboxSelect>>", self.update_preview)
        self.code_list.bind("<Double-Button-1>", self.apply_from_list)
        self.code_list.bind("<Return>", self.apply_from_list)
        self.code_list.bind("<Button-3>", self.show_context_menu)

        # HEADER PREVIEW (ora sotto la lista codici)
        preview_header = tk.Frame(upper_frame, height=28)
        preview_header.pack(fill="x")
        preview_header.pack_propagate(False)

        self.preview_label = tk.Label(preview_header, text="Tag preview", anchor="w", pady=4)
        self.preview_label.pack(side="left", fill="x", expand=True)

        self._load_icons()
        symbol = self.collapse_symbol if self.preview_expanded else self.expand_symbol

        self.toggle_button = tk.Button(
            preview_header,
            text=symbol,
            command=self.toggle_preview,
            width=2,
            height=1,
            pady=2,
            bd=0
        )
        self.toggle_button.pack(side="right", padx=(4, 0))

        Tooltip(self.toggle_button, "Expand/collapse tag preview")

        # AGGIUNTA DEL PANNELLO SUPERIORE AL PANED
        self.paned.add(upper_frame, minsize=80)

        # --- PANNELLO INFERIORE (preview) ---
        self.preview_frame = tk.Frame(self.paned)

        preview_inner = tk.Frame(self.preview_frame)
        preview_inner.pack(fill="both", expand=True)

        self.preview = tk.Listbox(preview_inner, height=4)
        scrollbar_preview = tk.Scrollbar(preview_inner)
        scrollbar_preview.pack(side="right", fill="y")
        self.preview.pack(fill="both", expand=True, side="left")
        self.preview.config(yscrollcommand=scrollbar_preview.set)
        scrollbar_preview.config(command=self.preview.yview)

        # BLOCCA IL CLICK SULLA LISTA DEI TAG
        self.preview.bind("<Button-1>", lambda e: "break")

        # Altezza iniziale del pannello inferiore
        minsize_preview = 80 if self.preview_expanded else 0
        self.paned.add(self.preview_frame, minsize=minsize_preview)

        # --- CONTEXT MENU ---
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Use", command=self.context_use)
        self.context_menu.add_command(label="Edit", command=self.context_edit)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.context_delete)

    def on_close(self):
        """Gestisce la chiusura della finestra salvando la geometria."""
        self.save_geometry()
        self.root.destroy()

    def _load_icons(self):
        """Inizializza i simboli del pulsante di espansione/collasso."""
        self.expand_symbol = "▼"
        self.collapse_symbol = "▲"
        self.expand_image = None
        self.collapse_image = None

    # ---------------- TOGGLE PREVIEW ----------------
    def toggle_preview(self):
        """
        Collassa o espande il pannello inferiore seguendo la logica richiesta:

        - In chiusura:
            * misura upper e lower
            * salva nel config
            * imposta la finestra all'altezza del solo pannello superiore

        - In apertura:
            * misura l'upper attuale
            * recupera upper e lower dal config
            * imposta la finestra alla somma
            * riaggiunge il pannello inferiore
            * ripristina l'upper salvato
        """

        self.preview_expanded = not self.preview_expanded
        print("preview_expanded =", self.preview_expanded)

        # Aggiorna icona
        self.toggle_button.config(
            text=self.collapse_symbol if self.preview_expanded else self.expand_symbol
        )

        self.root.update_idletasks()

        # Misura finestra attuale
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        if not self.preview_expanded:
            # ---------------------------------------------------------
            # 🔻 COLLASSO
            # ---------------------------------------------------------
            self.root.update_idletasks()

            # 1. Misura altezza pannello superiore
            try:
                self.upper_height = self.paned.sash_coord(0)[1]
            except Exception:
                self.upper_height = self.paned.winfo_height()

            # 2. Misura altezza pannello inferiore
            try:
                self.preview_height = self.preview_frame.winfo_height()
            except Exception:
                self.preview_height = 150

            # 3. Imposta la finestra all'altezza del solo pannello superiore
            # new_h = self.upper_height
            new_h = h - self.preview_height
            if new_h < 200:
                new_h = 200

            self.root.geometry(f"{w}x{new_h}")
            self.root.update_idletasks()

            # 4. Rimuove il pannello inferiore
            try:
                self.paned.forget(self.preview_frame)
            except tk.TclError:
                pass

            # 5. Salva tutto
            self.save_config()
            return

        else:
            # ---------------------------------------------------------
            # 🔺 ESPANSIONE
            # ---------------------------------------------------------
            self.root.update_idletasks()

            # 1. Misura l'altezza attuale del pannello superiore
            try:
                current_upper = self.paned.sash_coord(0)[1]
            except Exception:
                current_upper = self.paned.winfo_height()

            # 2. Recupera dal config le altezze salvate
            upper_h = self.upper_height if self.upper_height else current_upper
            lower_h = self.preview_height if self.preview_height else 150

            # 3. Imposta la finestra alla somma
            # new_h = upper_h + lower_h
            new_h = h + lower_h  # Aggiusta altezza attuale con altezza pannello inferiore
            self.root.geometry(f"{w}x{new_h}")
            self.root.update_idletasks()

            # 4. Riaggiunge il pannello inferiore
            try:
                self.paned.add(self.preview_frame, minsize=80)
            except tk.TclError:
                pass

            self.root.update_idletasks()

            # 5. Ripristina upper_height tramite sash
            try:
                # self.paned.sash_place(0, 0, upper_h)
                self.paned.sash_place(0, 0, current_upper)
            except Exception:
                pass

            # 6. Salva tutto
            self.save_config()
            return

    # ---------------- CONTEXT MENU ----------------
    def show_context_menu(self, event):
        index = self.code_list.nearest(event.y)
        if index < 0:
            return
        self.code_list.selection_clear(0, tk.END)
        self.code_list.selection_set(index)
        self.update_preview()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def show_about(self):
        from forms.about_form import AboutForm
        AboutForm(self.root, self.config)

    def context_use(self):
        self.apply_from_list()

    def context_edit(self):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        TagEditorForm(self.root, self.codes, preload_code=code)

    def context_delete(self):
        import tkinter.messagebox as messagebox
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        confirm = messagebox.askyesno("Delete", f"Delete code '{code}'?")
        if not confirm:
            return
        if code in self.codes:
            del self.codes[code]
            from codes_manager import save_codes
            save_codes(self.codes)
            self.update_list()
            self.preview.delete(0, tk.END)

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

    # ---------------- CODES LOGIC ----------------
    def update_list(self):
        self.code_list.delete(0, tk.END)
        self.filtered_codes = sorted(self.codes)
        for c in self.filtered_codes:
            self.code_list.insert(tk.END, c)
        self.entry['values'] = self.filtered_codes

    def filter_codes(self, *args):
        text = self.code_var.get().lower()
        self.code_list.delete(0, tk.END)
        self.filtered_codes = sorted(
            [c for c in self.codes if c.lower().startswith(text)]
        )
        for c in self.filtered_codes:
            self.code_list.insert(tk.END, c)
        self.entry['values'] = self.filtered_codes
        self.update_preview()

    def focus_list(self, event):
        if self.code_list.size() == 0:
            return
        self.code_list.focus_set()
        self.code_list.selection_set(0)
        self.update_preview()

    def update_preview(self, event=None):
        sel = self.code_list.curselection()
        if not sel:
            return

        code = self.code_list.get(sel[0])

        self.preview.delete(0, tk.END)
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

    def clear_input(self, event=None):
        self._reset_input()

    def send(self, code):
        threading.Thread(
            target=send_tags,
            args=(self.codes[code],),
            daemon=True
        ).start()

    # ---------------- OTHER ----------------
    def reload_codes(self):
        self.codes = load_codes()
        self.update_list()

    def open_editor(self):
        TagEditorForm(self.root, self.codes)
