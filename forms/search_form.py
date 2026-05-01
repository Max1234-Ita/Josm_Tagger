import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Any, Optional, Tuple


def _clamp_to_monitor(window: tk.Toplevel, x: int, y: int) -> Tuple[int, int]:
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


class SearchForm:
    """
    SearchForm: finestra Toplevel singleton per cercare codici e tag.
    Uso:
        SearchForm(mainform_instance, codes_dict, config)
    Dove `codes_dict` è un dict: code -> list of {"key":..., "value":...}
    """

    _instance: Optional["SearchForm"] = None

    def __init__(self, parent, codes: Dict[str, List[Dict[str, str]]], config: Dict[str, Any]):
        # Singleton: se esiste e la finestra è ancora valida, la porta in primo piano
        if SearchForm._instance and getattr(SearchForm._instance, "root", None):
            try:
                inst = SearchForm._instance
                if inst.root.winfo_exists():
                    inst.root.deiconify()
                    inst.root.lift()
                    inst.root.focus_force()
                    return
            except Exception:
                pass

        SearchForm._instance = self

        # riferimenti logici
        self.mainform = parent
        self.codes = codes or {}
        self.config = config or {}

        # crea Toplevel usando il root della mainform se disponibile
        master = getattr(parent, "root", None) or getattr(parent, "master", None) or None
        if master is None:
            # fallback: crea Toplevel senza master
            self.root = tk.Toplevel()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("Search Codes")
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        # font placeholder (se la mainform fornisce un font, usalo)
        self._font = getattr(self.mainform, "_font", None)

        # UI state
        self.filtered: List[str] = []

        # costruisci UI
        self._build_ui()

        # popolamento iniziale
        self._update_results()

        # posiziona vicino alla mainform
        try:
            self._place_near_parent_offset()
        except Exception:
            pass

        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.focus_force()

    # ---------------- UI BUILD ----------------
    def _build_ui(self):
        """Costruisce l'interfaccia completa."""
        # stile per la treeview
        style = ttk.Style(self.root)
        try:
            if self._font:
                style.configure("Search.Treeview", rowheight=20, font=self._font)
                style.configure("Search.Treeview.Heading", font=self._font)
            else:
                style.configure("Search.Treeview", rowheight=20)
        except Exception:
            style.configure("Search.Treeview", rowheight=20)

        # TOP: search + filters
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=6, pady=6)

        tk.Label(top, text="Search:").pack(side="left")

        self.query_var = tk.StringVar()
        self.query_var.trace_add("write", lambda *_: self._update_results())

        self.entry = tk.Entry(top, textvariable=self.query_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(4, 4))

        # filtri
        self.filter_codes = tk.BooleanVar(value=True)
        self.filter_keys = tk.BooleanVar(value=True)
        self.filter_values = tk.BooleanVar(value=True)

        tk.Checkbutton(top, text="Codes", variable=self.filter_codes,
                       command=self._update_results).pack(side="left", padx=4)
        tk.Checkbutton(top, text="Keys", variable=self.filter_keys,
                       command=self._update_results).pack(side="left", padx=4)
        tk.Checkbutton(top, text="Values", variable=self.filter_values,
                       command=self._update_results).pack(side="left", padx=4)

        # Paned principale (centro)
        self.paned = tk.PanedWindow(self.root, orient="horizontal", sashrelief="raised")
        self.paned.pack(fill="both", expand=True, padx=6, pady=6)

        # LEFT: risultati
        left = tk.Frame(self.paned)
        self.paned.add(left, minsize=250)

        # container per tree + scrollbar
        container = tk.Frame(left)
        container.pack(fill="both", expand=True)

        # tree_frame contiene canvas (griglia) e tree
        tree_frame = tk.Frame(container)
        tree_frame.grid(row=0, column=0, sticky="nsew")

        self._results_frame = tree_frame

        # canvas per la griglia (posizionato dentro tree_frame)
        self._grid_canvas = tk.Canvas(tree_frame, highlightthickness=0, bd=0)
        self._grid_canvas.grid(row=0, column=0, sticky="nsew")

        # Treeview con due colonne
        self.tree = ttk.Treeview(tree_frame, columns=("code", "tags"), show="headings",
                                 style="Search.Treeview")
        self.tree.heading("code", text="Code")
        self.tree.column("code", width=150, minwidth=100, anchor="w", stretch=False)
        self.tree.heading("tags", text="Tags")
        self.tree.column("tags", width=400, minwidth=100, anchor="w", stretch=True)

        # scrollbar (posizionate nel container per evitare sovrapposizioni)
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)

        # assegna scrollcommand che ridisegna la griglia
        self.tree.configure(yscrollcommand=lambda *a: (vsb.set(*a), self._draw_grid()),
                            xscrollcommand=lambda *a: (hsb.set(*a), self._draw_grid()))

        # posizionamento: tree_frame + scrollbar
        tree_frame.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # tree sopra il canvas
        self.tree.grid(row=0, column=0, sticky="nsew")
        try:
            self._grid_canvas.lower()
            self.tree.lift()
        except Exception:
            pass

        # rendi ridimensionabile
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # binding
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<ButtonRelease-2>", self._on_right_click)
        self.tree.bind("<Configure>", lambda e: self._draw_grid())
        self.tree.bind("<Expose>", lambda e: self._draw_grid())

        vsb.config(command=lambda *args: (self.tree.yview(*args), self._draw_grid()))
        hsb.config(command=lambda *args: (self.tree.xview(*args), self._draw_grid()))

        # RIGHT: details
        right = tk.Frame(self.paned)
        self.paned.add(right, minsize=200)

        self.details_label = tk.Label(right, text="Details")
        self.details_label.pack(anchor="w")

        details_container = tk.Frame(right)
        details_container.pack(fill="both", expand=True)

        self.details = tk.Listbox(details_container)
        self.details.pack(side="left", fill="both", expand=True)

        vsb2 = ttk.Scrollbar(details_container, orient="vertical", command=self.details.yview)
        vsb2.pack(side="right", fill="y")
        self.details.configure(yscrollcommand=vsb2.set)

        hsb2 = ttk.Scrollbar(right, orient="horizontal", command=self.details.xview)
        hsb2.pack(fill="x")
        self.details.configure(xscrollcommand=hsb2.set)

        # BOTTOM: pulsanti (fuori dal paned)
        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        btn_frame = tk.Frame(bottom)
        btn_frame.pack(side="right", padx=6, pady=6)

        self.close_btn = tk.Button(btn_frame, text="Close", command=self._close)
        self.close_btn.pack(side="right", padx=4)

        # context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Use", command=self._context_use)
        self.context_menu.add_command(label="Edit", command=self._context_edit)

        # funzione per fissare spazio bottom e aggiornare paned padding
        def _fix_bottom_and_paned():
            try:
                self.root.update_idletasks()
                btn_h = self.close_btn.winfo_reqheight() or 24
                reserved = max(int(btn_h * 1.2), int(btn_h + 8))
                bottom.config(height=reserved)
                try:
                    self.paned.pack_configure(padx=6, pady=(6, reserved))
                except Exception:
                    self.paned.pack_configure(padx=6, pady=reserved)
                try:
                    bottom.lift()
                    bottom.tkraise()
                except Exception:
                    pass
                self.root.update_idletasks()
                # se necessario, riduci minsize del primo pane
                try:
                    ph = self.paned.winfo_height()
                    rh = bottom.winfo_height()
                    if ph + rh > self.root.winfo_height():
                        panes = self.paned.panes()
                        if panes:
                            self.paned.paneconfig(panes[0], minsize=max(50, self.root.winfo_height() - rh - 12))
                except Exception:
                    pass
            except Exception:
                pass

        self.root.after_idle(_fix_bottom_and_paned)

        def _on_root_configure(event):
            self.root.after(10, _fix_bottom_and_paned)

        self.root.bind("<Configure>", _on_root_configure)

        # disegna griglia iniziale
        self.root.after_idle(self._draw_grid)

    # ---------------- RESULTS POPULATION ----------------
    def _update_results(self):
        """Popola la tree con i risultati filtrati."""
        query = self.query_var.get().strip().lower()
        f_codes = self.filter_codes.get()
        f_keys = self.filter_keys.get()
        f_values = self.filter_values.get()

        self.tree.delete(*self.tree.get_children())
        self.filtered = []

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
                self.filtered.append(code)
                try:
                    self.tree.insert("", "end", iid=code, values=(code, tag_str))
                except Exception:
                    self.tree.insert("", "end", values=(code, tag_str))

        self.filtered.sort()
        # assicurati che la griglia venga ridisegnata dopo il popolamento
        try:
            self.root.after_idle(self._draw_grid)
        except Exception:
            pass

    # ---------------- POSITIONING ----------------
    def _place_near_parent_offset(self):
        """Posiziona la finestra vicino alla mainform con un offset."""
        try:
            self.root.update_idletasks()
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

            final_x, final_y = _clamp_to_monitor(self.root, target_x, target_y)
            self.root.geometry(f"+{final_x}+{final_y}")
        except Exception:
            # fallback: centra sullo schermo
            try:
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                w = self.root.winfo_reqwidth() or 600
                h = self.root.winfo_reqheight() or 400
                self.root.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
            except Exception:
                pass

    # ------------------ apply minsize for the whole form ------------------
    def _apply_min_size(self):
        """
        Calcola e applica la minsize della toplevel:
        min_height = topY(results) + height(results) + height(close_btn) + 20px
        Deve essere chiamato dopo che il layout è stabilizzato (after_idle).
        """
        try:
            # assicurati che il layout sia aggiornato
            self.root.update_idletasks()

            # riferimento al frame dei risultati (fallback su self.tree)
            results_widget = getattr(self, "_results_frame", None) or getattr(self, "tree", None)
            if results_widget is None:
                return

            # se il widget non è ancora mappato, riprova dopo un breve delay
            if not results_widget.winfo_ismapped() or results_widget.winfo_height() < 8:
                try:
                    self.root.after(80, self._apply_min_size)
                except Exception:
                    pass
                return

            # coordinata Y relativa alla toplevel
            try:
                top_y = results_widget.winfo_rooty() - self.root.winfo_rooty()
            except Exception:
                top_y = results_widget.winfo_y()

            results_h = results_widget.winfo_height() or 0

            # altezza del pulsante Close (winfo_reqheight per altezza richiesta)
            try:
                close_h = getattr(self, "close_btn", None).winfo_reqheight() or 0
            except Exception:
                close_h = 0

            # calcola min height
            min_height = int(top_y + results_h + close_h + 20)

            # larghezza minima: manteniamo l'attuale larghezza richiesta o fallback 400
            try:
                current_w = max(self.root.winfo_reqwidth(), 400)
            except Exception:
                current_w = 400

            # applica la minsize alla toplevel
            try:
                self.root.minsize(current_w, min_height)
            except Exception:
                try:
                    # fallback: imposta geometry minima
                    self.root.geometry(f"{current_w}x{min_height}")
                except Exception:
                    pass

        except Exception:
            pass

    # ---------------- INTERACTIONS ----------------
    def _on_select(self, event=None):
        """Aggiorna il pannello Details con i tag della selezione."""
        try:
            sel = self.tree.selection()
            self.details.delete(0, tk.END)
            if not sel:
                return
            iid = sel[0]
            code = iid
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
        # se la mainform ha un metodo per aprire l'editor, chiamalo
        try:
            if hasattr(self.mainform, "open_tag_editor"):
                self.mainform.open_tag_editor(code)
            elif hasattr(self.mainform, "open_editor"):
                self.mainform.open_editor(code)
        except Exception:
            pass

    # ---------------- USE / CLOSE ----------------
    def _use_code(self, code: str):
        """Copia il codice nella clipboard, chiude la search e prova a inserirlo nella mainform."""
        try:
            # copia nella clipboard della toplevel
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(code)
            except Exception:
                pass

            # chiudi SearchForm
            self._close()

            # porta mainform in primo piano
            try:
                if hasattr(self.mainform, "deiconify"):
                    self.mainform.deiconify()
                if hasattr(self.mainform, "lift"):
                    self.mainform.lift()
                try:
                    self.mainform.attributes("-topmost", True)
                    self.mainform.after(50, lambda: self.mainform.attributes("-topmost", False))
                except Exception:
                    pass
            except Exception:
                pass

            # prova a inserire direttamente nella entry della mainform
            try:
                if hasattr(self.mainform, "entry"):
                    self.mainform.entry.delete(0, tk.END)
                    self.mainform.entry.insert(0, code)
                    self.mainform.entry.focus_force()
                    self.mainform.entry.icursor("end")
                else:
                    # fallback: genera evento di incolla se esiste una widget con focus
                    try:
                        self.mainform.event_generate("<<Paste>>")
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _close(self):
        """Chiude la finestra SearchForm (senza distruggere l'istanza singleton)."""
        try:
            if getattr(self, "root", None) and self.root.winfo_exists():
                try:
                    self.root.withdraw()
                except Exception:
                    try:
                        self.root.destroy()
                    except Exception:
                        pass
        finally:
            # non rimuoviamo l'istanza per permettere riaperture rapide
            pass

    # ---------------- GRID DRAW (semplice, robusto) ----------------
    def _draw_grid(self):
        """
        Disegna una griglia semplice sul canvas sottostante alla tree.
        Se la tree non è ancora mappata, riprova dopo un breve delay.
        Nota: la griglia è puramente decorativa.
        """
        try:
            tree = self.tree
            canvas = self._grid_canvas

            # se la tree non è mappata o troppo piccola, riprova
            if not tree.winfo_ismapped() or tree.winfo_width() < 10 or tree.winfo_height() < 10:
                try:
                    self.root.after(80, self._draw_grid)
                except Exception:
                    pass
                return

            tree.update_idletasks()
            tw = tree.winfo_width()
            th = tree.winfo_height()
            if tw <= 2 or th <= 2:
                try:
                    self.root.after(80, self._draw_grid)
                except Exception:
                    pass
                return

            # posiziona il canvas esattamente dentro la tree area
            try:
                canvas.place(in_=tree, relx=0, rely=0, relwidth=1, relheight=1)
            except Exception:
                canvas.config(width=tw, height=th)

            canvas.delete("grid_line")
            canvas.config(width=tw, height=th)

            # header height approssimato
            header_h = 24
            try:
                header_h = max(20, int(tree.winfo_reqheight() - tree.winfo_height() + 24))
            except Exception:
                header_h = 24

            # rowheight dallo style
            style = ttk.Style(self.root)
            try:
                rowheight = int(style.lookup("Search.Treeview", "rowheight") or 20)
            except Exception:
                rowheight = 20

            visible_rows = max(1, (th // rowheight) + 2)

            # linee orizzontali
            for i in range(0, visible_rows + 2):
                y = header_h + i * rowheight
                if y <= 0:
                    continue
                canvas.create_line(0, y, tw, y, fill="#e6e6e6", tags=("grid_line",), width=1)

            # linee verticali in corrispondenza delle colonne
            x = 0
            cols = tree["columns"]
            for col in cols:
                col_w = tree.column(col, option="width")
                x += int(col_w)
                canvas.create_line(x, 0, x, th, fill="#e6e6e6", tags=("grid_line",), width=1)

            try:
                self.tree.lift()
            except Exception:
                pass

        except Exception:
            pass

