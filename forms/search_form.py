import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Any, Optional, Tuple
import os
import sys
from pathlib import Path
from config_manager import debug_print
from effects import get_active_theme, apply_theme_colors, apply_background_picture
from forms.base_form import BaseForm


def _clamp_to_monitor(window, x: int, y: int) -> Tuple[int, int]:
    """Clamp x,y so the window stays on screen."""
    try:
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        window.update_idletasks()
        w = window.winfo_reqwidth() or 400
        h = window.winfo_reqheight() or 300
        final_x = max(0, min(x, sw - w))
        final_y = max(0, min(y, sh - h))
        return final_x, final_y
    except Exception:
        return x, y


class SearchForm(BaseForm):
    """
    SearchForm: finestra Toplevel singleton per cercare codici e tag.
    Uso:
        SearchForm(mainform_instance, codes_dict, config)
    Dove `codes_dict` è un dict: code -> list of {"key":..., "value":...}
    """

    _instance: Optional["SearchForm"] = None

    def __init__(self, parent, codes: Dict[str, List[Dict[str, str]]], config: Dict[str, Any]):
        # Singleton: se esiste e la finestra è ancora valida, la porta in primo piano
        if SearchForm._instance and SearchForm._instance.winfo_exists():
            try:
                inst = SearchForm._instance
                inst.deiconify()
                inst.lift()
                inst.focus_force()
                return
            except Exception:
                pass

        SearchForm._instance = self

        # riferimenti logici
        self.mainform = parent
        self.codes = codes or {}
        self.config = config or {}

        # crea Toplevel usando il root della mainform se disponibile
        master = getattr(parent, "root", None) or getattr(parent, "master", None) or parent

        super().__init__(master, "search")
        self.title("Search")
        
        # Carica configurazione e tema
        self.theme = get_active_theme(self.config)
        self.bg_color = self.theme.get("bg", "#f0f0f0")
        self.fg_color = self.theme.get("fg", "#101010")
        self.panel_color = self.theme.get("panel", self.bg_color)
        self.panel_fg = self.theme.get("panel_fg", self.fg_color)
        
        self.configure(bg=self.bg_color)
        
        # Applica Scala UI e Font
        self._apply_ui_scaling()

        # Applica Minsize scalata
        scale = float(self.config.get("ui_scale", 1.0))
        self.minsize(int(620 * scale), int(500 * scale))

        # Applica Icona (Windows/Linux)
        self._apply_icon()
        
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        # UI state
        self.filtered: List[str] = []

        # costruisci UI
        self._build_ui()

        # Applica tema e immagine di sfondo
        self.apply_theme()

        # popolamento iniziale
        self._update_results()

        # posiziona vicino alla mainform
        try:
            self._place_near_parent_offset()
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.focus_force()

    def _apply_ui_scaling(self):
        """Applica la scala UI e il font configurato."""
        family = self.config.get("font_family", "Calibri")
        size = int(self.config.get("font_size", 11))
        scale = float(self.config.get("ui_scale", 1.0))
        
        scaled_size = int(size * scale)
        self._font = (family, scaled_size)
        
        # Applica scaling a livello di Tk se possibile
        try:
            self.tk.call('tk', 'scaling', scale * 1.33) # 1.33 è il fattore tipico per 96 DPI
        except:
            pass

    def _apply_icon(self):
        """Applica l'icona alla finestra (ICO per Windows, PNG per Linux)."""
        try:
            # Risoluzione percorso base (compatibile con PyInstaller)
            if hasattr(sys, "_MEIPASS"):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).resolve().parent.parent
            
            if sys.platform.startswith("win"):
                icon_path = os.path.join(base_path, "resources", "josm_tagger.ico")
                if os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
            else:
                icon_path = os.path.join(base_path, "resources", "josm_tagger.png")
                if os.path.exists(icon_path):
                    img = tk.PhotoImage(file=icon_path)
                    self.iconphoto(True, img)
        except Exception as e:
            debug_print(f"DEBUG: Could not set icon: {e}", cfg=self.config)

    def apply_theme(self):
        """Applica i colori del tema e l'immagine di sfondo."""
        apply_theme_colors(self, self.config)
        apply_background_picture(self, self.config)
        
        # Correzioni specifiche per ttk
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("Search.Treeview", 
                        background=self.panel_color, 
                        fieldbackground=self.panel_color, 
                        foreground=self.panel_fg)
        
        # Tematizzazione HEADERS (Intestazioni colonne)
        style.configure("Search.Treeview.Heading", 
                        background=self.panel_color, 
                        foreground=self.panel_fg,
                        relief="flat",
                        font=self._font)
        style.map("Search.Treeview.Heading",
                  background=[('active', '#0078d7')],
                  foreground=[('active', 'white')])

        style.map("Search.Treeview", 
                  background=[('selected', '#0078d7')], 
                  foreground=[('selected', 'white')])

    # ---------------- UI BUILD ----------------
    def _build_ui(self):
        """Costruisce l'interfaccia completa secondo il mockup."""
        # stile per la treeview
        style = ttk.Style(self)
        style.theme_use("clam")
        try:
            style.configure("Search.Treeview", rowheight=int(25 * float(self.config.get("ui_scale", 1.0))))
            if self._font:
                style.configure("Search.Treeview", font=self._font)
                style.configure("Search.Treeview.Heading", font=self._font)
        except Exception:
            pass

        # Container principale con padding
        main_container = tk.Frame(self, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. ISTRUZIONI
        instr_text = "Search for any code, key, or value; Right-click any item in the results list for more options"
        self.instructions = tk.Label(main_container, text=instr_text, justify="left", 
                                     bg=self.bg_color, fg=self.fg_color, font=self._font,
                                     wraplength=500)
        self.instructions.pack(fill="x", pady=(0, 10))
        
        # Aggiorna wraplength dinamicamente
        def _update_wrap(event):
            self.instructions.config(wraplength=event.width - 20)
        main_container.bind("<Configure>", _update_wrap)

        # 2. AREA RICERCA E FILTRI
        search_area = tk.Frame(main_container, bg=self.bg_color)
        search_area.pack(fill="x", pady=(0, 15))

        tk.Label(search_area, text="Search for:", bg=self.bg_color, fg=self.fg_color, font=self._font).pack(side="left")

        self.query_var = tk.StringVar()
        self.query_var.trace_add("write", lambda *_: self._update_results())

        self.entry = tk.Entry(search_area, textvariable=self.query_var, bg=self.panel_color, fg=self.panel_fg,
                              relief="solid", borderwidth=1, font=self._font, insertbackground=self.panel_fg)
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 20))

        # Filtri
        filter_frame = tk.Frame(search_area, bg=self.bg_color)
        filter_frame.pack(side="left")
        
        tk.Label(filter_frame, text="Filters:", bg=self.bg_color, fg=self.fg_color, font=self._font).pack(side="left", padx=(0, 5))

        self.filter_codes = tk.BooleanVar(value=True)
        self.filter_keys = tk.BooleanVar(value=True)
        self.filter_values = tk.BooleanVar(value=True)

        for text, var in [("Codes", self.filter_codes), ("Keys", self.filter_keys), ("Values", self.filter_values)]:
            tk.Checkbutton(filter_frame, text=text, variable=var, bg=self.bg_color, fg=self.fg_color,
                           selectcolor=self.panel_color, activebackground=self.bg_color, activeforeground=self.fg_color,
                           command=self._update_results, font=self._font).pack(side="left", padx=2)

        # 3. PANNELLI CENTRALI
        self.paned = tk.PanedWindow(main_container, orient="horizontal", bg=self.bg_color, 
                                    sashwidth=4, sashrelief="flat")
        self.paned.pack(fill="both", expand=True)

        # LEFT: Results
        self.results_lf = tk.LabelFrame(self.paned, text="Results", bg=self.bg_color, fg=self.fg_color, font=self._font, padx=5, pady=5)
        self.paned.add(self.results_lf, minsize=300)

        tree_container = tk.Frame(self.results_lf, bg=self.panel_color, borderwidth=1, relief="solid")
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_container, columns=("code", "tags"), show="headings",
                                 style="Search.Treeview")
        self.tree.heading("code", text="Code")
        self.tree.column("code", width=100, minwidth=60, anchor="w", stretch=False)
        self.tree.heading("tags", text="Tags")
        self.tree.column("tags", width=400, minwidth=100, anchor="w", stretch=True)

        # Usiamo ttk.Scrollbar per supporto tema dinamico (tramite clam)
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.results_lf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        hsb.pack(fill="x")

        # RIGHT: Details
        self.details_lf = tk.LabelFrame(self.paned, text="Details", bg=self.bg_color, fg=self.fg_color, font=self._font, padx=5, pady=5)
        self.paned.add(self.details_lf, minsize=200)

        details_inner = tk.Frame(self.details_lf, bg=self.panel_color)
        details_inner.pack(fill="both", expand=True)

        self.details = tk.Listbox(details_inner, bg=self.panel_color, fg=self.panel_fg, 
                                  relief="solid", borderwidth=1, font=self._font, selectbackground="#0078d7")
        self.details.pack(side="left", fill="both", expand=True)

        vsb2 = ttk.Scrollbar(details_inner, orient="vertical", command=self.details.yview)
        vsb2.pack(side="right", fill="y")
        self.details.configure(yscrollcommand=vsb2.set)
        
        # 4. BOTTOM AREA
        bottom = tk.Frame(main_container, bg=self.bg_color)
        bottom.pack(fill="x", pady=(10, 0))

        self.close_btn = tk.Button(bottom, text="Close", command=self._close, width=10,
                                   bg="#e1e1e1", fg="black", relief="raised", borderwidth=1, font=self._font)
        self.close_btn.pack(side="right")

        # context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Use", command=self._context_use)
        self.context_menu.add_command(label="Edit", command=self._context_edit)

        # bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

    # ---------------- RESULTS POPULATION ----------------
    def _update_results(self):
        """Popola la tree con i risultati filtrati in ordine alfabetico per Code."""
        query = self.query_var.get().strip().lower()
        f_codes = self.filter_codes.get()
        f_keys = self.filter_keys.get()
        f_values = self.filter_values.get()

        self.tree.delete(*self.tree.get_children())
        self.filtered = []
        matches = []

        for code, tags in (self.codes.items() if isinstance(self.codes, dict) else []):
            code_l = code.lower()
            match = False

            if not query:
                match = True
            else:
                if f_codes and code_l.startswith(query):
                    match = True

                if not match and f_keys:
                    for t in tags:
                        if t.get("key", "").lower().startswith(query):
                            match = True
                            break

                if not match and f_values:
                    for t in tags:
                        if t.get("value", "").lower().startswith(query):
                            match = True
                            break

            if match:
                tag_str = "; ".join(f"{t.get('key','')}={t.get('value','')}" for t in tags)
                matches.append((code, tag_str))

        # Ordinamento alfabetico per Code
        matches.sort(key=lambda x: x[0].lower())

        for code, tag_str in matches:
            self.filtered.append(code)
            try:
                self.tree.insert("", "end", iid=code, values=(code, tag_str))
            except Exception:
                self.tree.insert("", "end", values=(code, tag_str))

    # ---------------- POSITIONING ----------------
    def _place_near_parent_offset(self):
        """Posiziona la finestra vicino alla mainform con un offset."""
        try:
            self.update_idletasks()
            parent_root = getattr(self.mainform, "root", None) or self.mainform
            px = parent_root.winfo_x()
            py = parent_root.winfo_y()
            pw = parent_root.winfo_width()
            ph = parent_root.winfo_height()

            cx = px + pw // 2
            cy = py + ph // 2

            ox = int(pw * 0.30)
            oy = int(ph * 0.30)

            target_x = cx + ox
            target_y = cy + oy

            final_x, final_y = _clamp_to_monitor(self, target_x, target_y)
            self.geometry(f"+{final_x}+{final_y}")
        except Exception:
            # Centra sullo schermo
            try:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                w = self.winfo_reqwidth() or 600
                h = self.winfo_reqheight() or 400
                self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
            except Exception:
                pass

    # ---------------- INTERACTIONS ----------------
    def _on_select(self, event=None):
        """Aggiorna il pannello Details con i tag della selezione."""
        try:
            sel = self.tree.selection()
            self.details.delete(0, tk.END)
            if not sel:
                self.details_lf.config(text="Details")
                return
            iid = sel[0]
            code = iid
            self.details_lf.config(text=f"{code} - Details")
            tags = self.codes.get(code, [])
            for t in tags:
                self.details.insert(tk.END, f"{t.get('key','')} = {t.get('value','')}")
        except Exception:
            pass

    def _on_double_click(self, event=None):
        """Usa il codice selezionato e chiude la finestra."""
        try:
            sel = self.tree.selection()
            if not sel:
                return
            code = sel[0]
            self._use_code(code)
        except Exception:
            pass

    def _on_right_click(self, event):
        """Mostra il menu contestuale sulla riga sotto il cursore."""
        try:
            row = self.tree.identify_row(event.y)
            if row:
                self.tree.selection_set(row)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    def _context_use(self):
        sel = self.tree.selection()
        if sel:
            self._use_code(sel[0])

    def _context_edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        code = sel[0]
        try:
            # Chiama l'editor sulla mainform passando il codice selezionato
            if hasattr(self.mainform, "open_editor"):
                self.mainform.open_editor(code)
        except Exception as e:
            debug_print(f"DEBUG: Error opening editor from search: {e}", cfg=self.config)

    # ---------------- USE / CLOSE ----------------
    def _use_code(self, code: str):
        """Copia il codice nella clipboard, chiude la search e prova a inserirlo nella mainform."""
        try:
            try:
                self.clipboard_clear()
                self.clipboard_append(code)
            except Exception:
                pass

            self._close()

            try:
                if hasattr(self.mainform, "deiconify"):
                    self.mainform.deiconify()
                if hasattr(self.mainform, "lift"):
                    self.mainform.lift()
            except Exception:
                pass

            try:
                if hasattr(self.mainform, "entry"):
                    self.mainform.entry.delete(0, tk.END)
                    self.mainform.entry.insert(0, code)
                    self.mainform.entry.focus_force()
                    self.mainform.entry.icursor("end")
            except Exception:
                pass
        except Exception:
            pass

    def _close(self):
        """Chiude la finestra SearchForm."""
        try:
            if self.winfo_exists():
                try:
                    self.withdraw()
                except Exception:
                    try:
                        self.destroy()
                    except Exception:
                        pass
        finally:
            pass
