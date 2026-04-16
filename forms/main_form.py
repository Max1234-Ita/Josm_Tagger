import os
import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
import threading
import keyboard
import pystray
from PIL import Image

from config_manager import load_config, save_config
from codes_manager import load_codes
from josm_interface import send_tags
from forms.tag_editor_form import TagEditorForm
from forms.font_selector_form import FontSelectorForm


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


class Tooltip:
    """Simple tooltip widget for Tkinter."""
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

        self._disable_maximize()

        root.title("JOSM Tagger")
        root.attributes("-topmost", True)

        # --- TRAY STATE ---
        self.tray_icon = None
        self.tray_thread = None
        self.tray_running = False

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
        self.root.bind("<Configure>", self._prevent_maximize)

        # X → minimizza nella tray
        # self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.protocol("WM_DELETE_WINDOW", self._exit_app)

        # Declared attributes
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

        # Panel state
        self.preview_expanded = self.config.get("preview_expanded", True)
        self.preview_height = max(160, self.config.get("preview_height", 160))
        self.upper_height = self.config.get("upper_height", None)

        # Build GUI
        self.build_menu()
        self.build_ui()
        self.register_hotkey()
        self.apply_font()
        self.update_list()

        # Tooltip
        self._list_tooltip_window = None
        self._list_tooltip_last_index = None

        # Restore panes layout after Tk has stabilized geometry
        self.root.after_idle(self._restore_panes_layout)

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
        Save only the main window geometry (position and size).
        Does not modify other config settings.
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
        Save preview panel state and pane heights.
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
        file_menu.add_command(label="Exit", command=self._exit_app)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Tags & Codes", command=self.open_editor)

        view_menu = tk.Menu(self.menubar, tearoff=0)
        view_menu.add_command(label="Font", command=self.select_font)
        view_menu.add_separator()
        view_menu.add_command(label="Minimize to tray", command=self.minimize_to_tray)

        about_menu = tk.Menu(self.menubar, tearoff=0)
        about_menu.add_command(label="About", command=self.show_about)

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

        # --- PANED WINDOW ---
        self.paned = tk.PanedWindow(self.root, orient="vertical", sashrelief="raised")
        self.paned.pack(fill="both", expand=True, padx=6, pady=6)

        # --- UPPER PANEL ---
        upper_frame = tk.Frame(self.paned)

        list_frame = tk.Frame(upper_frame)
        list_frame.pack(fill="both", expand=True)

        self.code_list = tk.Listbox(list_frame, height=4)
        self.code_list.bind("<Motion>", self._on_list_motion)
        self.code_list.bind("<Leave>", self._on_list_leave)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.code_list.pack(fill="both", expand=True, side="left")
        self.code_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.code_list.yview)

        self.code_list.bind("<<ListboxSelect>>", self.update_preview)
        self.code_list.bind("<Double-Button-1>", self.apply_from_list)
        self.code_list.bind("<Return>", self.apply_from_list)
        self.code_list.bind("<Button-3>", self.show_context_menu)

        # Preview header
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

        # Fixed minimum height for upper panel
        self.MIN_UPPER = 160
        self.paned.add(upper_frame, minsize=self.MIN_UPPER)

        # --- LOWER PANEL (PREVIEW) ---
        self.preview_frame = tk.Frame(self.paned)

        preview_inner = tk.Frame(self.preview_frame)
        preview_inner.pack(fill="both", expand=True)

        self.preview = tk.Listbox(preview_inner, height=4)
        scrollbar_preview = tk.Scrollbar(preview_inner)
        scrollbar_preview.pack(side="right", fill="y")
        self.preview.pack(fill="both", expand=True, side="left")
        self.preview.config(yscrollcommand=scrollbar_preview.set)
        scrollbar_preview.config(command=self.preview.yview)

        # Make preview read-only to mouse clicks
        self.preview.bind("<Button-1>", lambda e: "break")

        if self.preview_expanded:
            self.paned.add(self.preview_frame, minsize=0)
        else:
            self.paned.add(self.preview_frame, minsize=0)
            self.paned.forget(self.preview_frame)

        # --- CONTEXT MENU ---
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Use", command=self.context_use)
        self.context_menu.add_command(label="Edit", command=self.context_edit)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.context_delete)

    def on_close(self):
        """Handle window close, saving geometry."""
        self.save_geometry()
        self.root.destroy()

    def _on_list_motion(self, event):
        """Show tooltip with tag preview when hovering over a code."""
        index = self.code_list.nearest(event.y)

        # Out of bounds → hide tooltip
        if index < 0 or index >= self.code_list.size():
            self._hide_list_tooltip()
            self._list_tooltip_last_index = None
            return

        # Same row → do nothing
        if self._list_tooltip_last_index == index:
            # Update position only
            if self._list_tooltip_window:
                self._list_tooltip_window.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            return

        self._list_tooltip_last_index = index
        code = self.code_list.get(index)
        tags = self.codes.get(code, [])

        if not tags:
            self._hide_list_tooltip()
            return

        # Build preview text
        lines = [f"{t['key']} = {t['value']}" for t in tags]
        text = "\n".join(lines)

        # Show tooltip near cursor
        self._show_list_tooltip(event.x_root + 10, event.y_root + 10, text)

    def _on_list_leave(self, event):
        """Hide tooltip when leaving the listbox."""
        self._hide_list_tooltip()
        self._list_tooltip_last_index = None

    def _show_list_tooltip(self, x, y, text):
        self._hide_list_tooltip()

        tw = tk.Toplevel(self.code_list)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)  # required because main window is topmost

        label = tk.Label(
            tw,
            text=text,
            bg="#ffffe0",
            fg="black",
            justify="left",
            font=self.entry.cget("font"),
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#aaaaaa"
        )
        label.pack(ipadx=4, ipady=2)

        self._list_tooltip_window = tw

    def _hide_list_tooltip(self):
        """Destroy tooltip window if present."""
        if self._list_tooltip_window is not None:
            try:
                self._list_tooltip_window.destroy()
            except:
                pass
        self._list_tooltip_window = None

    def _load_icons(self):
        """Initialize expand/collapse symbols for the preview toggle button."""
        self.expand_symbol = "▼"
        self.collapse_symbol = "▲"
        self.expand_image = None
        self.collapse_image = None

    # ---------------- TOGGLE PREVIEW ----------------
    def toggle_preview(self):
        self.preview_expanded = not self.preview_expanded
        self.toggle_button.config(
            text=self.collapse_symbol if self.preview_expanded else self.expand_symbol
        )

        if not self.preview_expanded:
            self._collapse_preview()
        else:
            self._expand_preview()

    def _collapse_preview(self):
        self.root.update_idletasks()

        # Capture current upper pane height once, clamp to minimum
        try:
            self.upper_height = self.paned.sash_coord(0)[1]
        except:
            self.upper_height = self.MIN_UPPER

        self.upper_height = max(self.upper_height, self.MIN_UPPER)

        # Remove preview panel
        try:
            self.paned.forget(self.preview_frame)
        except:
            pass

        # Fix upper pane minimum height so it does not shrink
        try:
            self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
        except:
            pass

        # Optionally adjust window height to match upper pane
        w = self.root.winfo_width()
        self.root.geometry(f"{w}x{self.upper_height}")

        self.save_config()

    def _expand_preview(self):
        self.root.update_idletasks()

        # Fallback if upper_height was never set
        if self.upper_height is None:
            try:
                self.upper_height = self.paned.sash_coord(0)[1]
            except:
                self.upper_height = self.MIN_UPPER

        self.upper_height = max(self.upper_height, self.MIN_UPPER)
        self.preview_height = max(160, self.preview_height)

        # Re-add preview panel if missing
        if self.preview_frame not in self.paned.panes():
            try:
                self.paned.add(self.preview_frame, minsize=0)
            except:
                pass

        self.root.update_idletasks()

        # Place sash so upper pane has fixed height
        try:
            self.paned.sash_place(0, 0, self.upper_height)
        except:
            pass

        # Fix upper pane minimum height
        try:
            self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
        except:
            pass

        # Adjust window height to upper + preview
        w = self.root.winfo_width()
        total_h = self.upper_height + self.preview_height
        self.root.geometry(f"{w}x{total_h}")

        # Update preview_height from actual widget height
        self.root.update_idletasks()
        try:
            self.preview_height = max(160, self.preview_frame.winfo_height())
        except:
            self.preview_height = 160

        self.save_config()

    def _restore_panes_layout(self):
        """
        Restore the split layout after window creation, using saved heights.
        """
        self.root.update_idletasks()

        # Ensure minimum upper height
        if self.upper_height is None:
            try:
                self.upper_height = self.paned.sash_coord(0)[1]
            except:
                self.upper_height = self.MIN_UPPER

        self.upper_height = max(self.upper_height, self.MIN_UPPER)
        self.preview_height = max(160, self.preview_height)

        if not self.preview_expanded:
            # Collapsed: ensure preview is removed and upper pane fixed
            try:
                self.paned.forget(self.preview_frame)
            except:
                pass
            try:
                self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
            except:
                pass
            w = self.root.winfo_width()
            self.root.geometry(f"{w}x{self.upper_height}")
            self.save_config()
            return

        # Expanded: ensure preview is present
        if self.preview_frame not in self.paned.panes():
            try:
                self.paned.add(self.preview_frame, minsize=0)
            except:
                pass

        self.root.update_idletasks()

        # Place sash and fix upper pane
        try:
            self.paned.sash_place(0, 0, self.upper_height)
        except:
            pass

        try:
            self.paned.paneconfig(self.paned.panes()[0], minsize=self.upper_height)
        except:
            pass

        # Adjust window height to match saved layout
        w = self.root.winfo_width()
        total_h = self.upper_height + self.preview_height
        self.root.geometry(f"{w}x{total_h}")

        self.root.update_idletasks()
        self.save_config()

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
        f = (
            self.config.get("font_family", "Segoe UI"),
            int(self.config.get("font_size", 10))
        )
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
        if self.tray_running:
            # se è in tray, ripristina
            self._on_tray_restore()
            return

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
        self.entry["values"] = self.filtered_codes

    def filter_codes(self, *args):
        text = self.code_var.get().lower()
        self.code_list.delete(0, tk.END)
        self.filtered_codes = sorted(
            [c for c in self.codes if c.lower().startswith(text)]
        )
        for c in self.filtered_codes:
            self.code_list.insert(tk.END, c)
        self.entry["values"] = self.filtered_codes
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
        # self._reset_input()

    def apply_code(self, event=None):
        code = self.code_var.get().strip()

        # Caso 1: l'utente ha scritto un codice valido
        if code in self.codes:
            self.send(code)
            # self._reset_input()
            return

        # Caso 2: l'utente ha selezionato un codice dalla lista
        sel = self.code_list.curselection()
        if sel:
            selected = self.code_list.get(sel[0])
            self.send(selected)
            # self._reset_input()
            return

        # Caso 3: NON applicare nulla → NON ripulire
        # (prima applicava il primo codice filtrato, ora non lo fa più)

    def _promote_code(self, code):
        """Move the used code to the top of the combobox (MRU list)."""
        values = list(self.code_list["values"])

        # Remove if already present
        if code in values:
            values.remove(code)

        # Insert at the top
        values.insert(0, code)

        # Update combobox values
        self.code_list["values"] = values

    def _reset_input(self):
        self.code_var.set("")
        self.preview.delete(0, tk.END)

    def clear_input(self, event=None):
        self._reset_input()

    def send(self, code):
        self._show_sending_preview(code)

        def worker():
            import pyautogui
            pyautogui.FAILSAFE = False  # disable only inside this thread

            try:
                send_tags(self.codes[code])
            finally:
                def done():
                    self._promote_code(code)  # move used code to top
                    self._reset_input()  # baseline behavior

                self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _show_sending_preview(self, code):
        """Mostra nella preview i tag che stanno per essere inviati."""
        self.preview.delete(0, tk.END)
        for t in self.codes.get(code, []):
            self.preview.insert(tk.END, f"{t['key']} = {t['value']}")

    def _lock_ui(self):
        """Blocca completamente il form durante l'invio dei tag."""
        try:
            self.root.attributes("-disabled", True)
        except:
            pass  # Linux non supporta -disabled

        # Disabilita i widget principali
        self.entry.configure(state="disabled")
        self.apply_button.configure(state="disabled")
        self.code_list.configure(state="disabled")
        self.preview.configure(state="disabled")

    def _unlock_ui(self):
        """Sblocca il form dopo l'invio dei tag."""
        try:
            self.root.attributes("-disabled", False)
        except:
            pass

        self.entry.configure(state="normal")
        self.apply_button.configure(state="normal")
        self.code_list.configure(state="normal")
        self.preview.configure(state="normal")

    # ---------------- OTHER ----------------
    def reload_codes(self):
        self.codes = load_codes()
        self.update_list()

    def open_editor(self):
        TagEditorForm(self.root, self.codes)

    # ---------------------------------------------------------
    # SYSTEM TRAY SUPPORT (pystray)
    # ---------------------------------------------------------
    def minimize_to_tray(self):
        """Hide window and show tray icon."""
        if self.tray_running:
            return

        self.save_geometry()
        self.root.withdraw()

        self.tray_running = True
        self.tray_thread = threading.Thread(target=self._run_tray_icon_thread, daemon=True)
        self.tray_thread.start()

    def _run_tray_icon_thread(self):
        icon_path = resource_path("resources/josm_tagger.ico")
        image = Image.open(icon_path)

        menu = pystray.Menu(
            pystray.MenuItem("Restore", self._on_tray_restore),
            pystray.MenuItem("Exit", self._on_tray_exit)
        )

        def setup(icon):
            icon.visible = True

            # ⭐ Windows: abilita click sinistro per restore
            if sys.platform.startswith("win"):
                def on_click(icon, event):
                    # LEFT_CLICK è supportato solo dal backend Win32
                    if event == pystray.MouseEvent.LEFT_CLICK:
                        self._on_tray_restore()

                icon.on_click = on_click

            # ⭐ Linux: NON assegnare on_click
            # AppIndicator/SNI non supportano eventi → evitiamo eccezioni

        self.tray_icon = pystray.Icon(
            "josm_tagger",
            image,
            "JOSM Tagger",
            menu
        )

        # ⭐ IMPORTANTE: run con setup
        self.tray_icon.run(setup=setup)

    def _on_tray_restore(self, icon=None, item=None):
        """Restore window from tray."""
        self.tray_running = False
        if self.tray_icon:
            self.tray_icon.stop()

        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(50, lambda: self.root.attributes("-topmost", True))
        self.focus_input()

    def _on_tray_exit(self, icon=None, item=None):
        """Exit application from tray."""
        self.tray_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self._exit_app)

    def _prevent_maximize(self, event):
        # Se la finestra è massimizzata → ripristina la geometria salvata
        if self.root.state() == "zoomed":
            self.root.state("normal")
            self.apply_geometry()

    def _disable_maximize(self):
        """
        Disabilita completamente la massimizzazione della finestra su Windows:
        - rimuove il pulsante di massimizzazione
        - blocca il doppio click sulla title-bar
        - blocca Win+FrecciaSu
        - evita il flash visivo della finestra che si massimizza per un istante
        """
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

            GWL_STYLE = -16
            WS_MAXIMIZEBOX = 0x00010000
            WS_THICKFRAME = 0x00040000  # mantiene il resize manuale

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

            # Rimuove solo la capacità di massimizzare, NON il resize
            style &= ~WS_MAXIMIZEBOX

            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        except Exception:
            # Su Linux o se ctypes non funziona → ignora silenziosamente
            pass

    def _exit_app(self):
        self.save_geometry()
        self.root.destroy()