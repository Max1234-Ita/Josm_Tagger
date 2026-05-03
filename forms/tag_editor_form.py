import copy
import os
import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, simpledialog

from codes_manager import save_codes
import effects
from effects import apply_background_picture, apply_theme_colors, get_active_theme
from forms.base_form import BaseForm


def _monitor_workarea_from_point(x, y, fallback_window):
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes

            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            user32 = ctypes.windll.user32
            pt = POINT(int(x), int(y))
            monitor = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
            if monitor:
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    return (
                        int(info.rcWork.left),
                        int(info.rcWork.top),
                        int(info.rcWork.right),
                        int(info.rcWork.bottom),
                    )
        except Exception:
            pass

    try:
        return (0, 0, fallback_window.winfo_screenwidth(), fallback_window.winfo_screenheight())
    except Exception:
        return (0, 0, 1920, 1080)


def _clamp_to_monitor(window, x, y):
    try:
        area = _monitor_workarea_from_point(x, y, window)
        min_x, min_y, max_x, max_y = area
        window.update_idletasks()
        w = window.winfo_reqwidth()
        h = window.winfo_reqheight()
        final_x = max(min_x, min(x, max_x - w))
        final_y = max(min_y, min(y, max_y - h))
        return final_x, final_y
    except Exception:
        return x, y


class TagPropertiesForm(BaseForm):
    def __init__(self, parent, config, key_value=None):
        self.config = config
        self.result = None
        super().__init__(parent, "tag_properties")
        self.title("Tag properties")
        self.attributes("-topmost", True)
        try:
            self.attributes("-toolwindow", True)
        except Exception:
            pass
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        apply_background_picture(self, self.config)
        self._set_icon()

        self.key_var = tk.StringVar(value=(key_value or {}).get("key", ""))
        self.value_var = tk.StringVar(value=(key_value or {}).get("value", ""))

        self._build_ui()
        self._apply_font()
        self._apply_theme()
        self._place_near_pointer()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.focus_force()

    def _set_icon(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ico_path = os.path.join(base_dir, "resources", "josm_tagger.ico")
        png_path = os.path.join(base_dir, "resources", "josm_tagger.png")
        try:
            if sys.platform.startswith("win") and os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            elif os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _build_ui(self):
        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(main, text="Key:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 6))
        key_entry = tk.Entry(main, textvariable=self.key_var, width=40)
        key_entry.grid(row=0, column=1, sticky="we", pady=(0, 6))

        tk.Label(main, text="Value:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(0, 6))
        value_entry = tk.Entry(main, textvariable=self.value_var, width=40)
        value_entry.grid(row=1, column=1, sticky="we", pady=(0, 6))
        value_entry.bind("<Return>", lambda _e: self._on_ok())

        btn = tk.Frame(main)
        btn.grid(row=2, column=0, columnspan=2, sticky="e", pady=(6, 0))
        tk.Button(btn, text="OK", width=10, command=self._on_ok).pack(side="left", padx=(0, 6))
        tk.Button(btn, text="Cancel", width=10, command=self._on_cancel).pack(side="left")

        main.columnconfigure(1, weight=1)
        key_entry.focus_set()

    def _apply_font(self):
        font_conf = (
            self.config.get("font_family", "Segoe UI"),
            self.config.get("font_size", 10),
        )
        self.option_add("*Font", font_conf)

        def apply(widget):
            try:
                widget.configure(font=font_conf)
            except Exception:
                pass
            for child in widget.winfo_children():
                apply(child)

        apply(self)

    def _apply_theme(self):
        apply_theme_colors(self, self.config)
        theme = get_active_theme(self.config)
        p_fg = theme.get("panel_fg")
        p_bg = theme.get("panel")
        for child in self.winfo_children():
            for w in child.winfo_children():
                if isinstance(w, tk.Entry):
                    w.configure(bg=p_bg, fg=p_fg, insertbackground=p_fg)

    def _place_near_pointer(self):
        self.update_idletasks()
        px = self.winfo_pointerx()
        py = self.winfo_pointery()
        x, y = _clamp_to_monitor(self, px + 12, py + 12)
        self.geometry(f"+{x}+{y}")

    def _on_ok(self):
        key = self.key_var.get().strip()
        value = self.value_var.get().strip()
        if not key or not value:
            messagebox.showwarning("Warning", "Key and value are required", parent=self)
            return
        self.result = {"key": key, "value": value}
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class TagEditorForm(BaseForm):
    _instance = None

    def __init__(self, root, codes, on_save_callback=None, config=None, preload_code=None):
        if TagEditorForm._instance and TagEditorForm._instance.winfo_exists():
            inst = TagEditorForm._instance
            inst.deiconify()
            inst.lift()
            inst.focus_force()
            if preload_code:
                inst.load_code(preload_code)
            return

        TagEditorForm._instance = self

        self.source_codes = codes
        self.working_codes = copy.deepcopy(codes)
        self.on_save_callback = on_save_callback
        self.config = config or {}
        self.preload_code = preload_code
        self.current_code = None

        super().__init__(root, "tag_editor")
        self.title("Tag Editor")
        self.attributes("-topmost", True)
        try:
            self.attributes("-toolwindow", True)
        except Exception:
            pass
        self.minsize(450, 300)
        self.resizable(False, False)
        apply_background_picture(self, self.config)
        self._set_icon()

        self._trace_id = None
        self.code_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.value_var = tk.StringVar()

        self.entry_code = None
        self.code_list = None
        self.tag_list = None
        self.tag_context_menu = None
        self.code_context_menu = None

        self.build_ui()
        self.apply_font()
        self.apply_theme()

        self._trace_id = self.code_var.trace_add("write", self.auto_load_code)
        self.entry_code["values"] = sorted(self.working_codes.keys())
        self.update_code_list()

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.update_idletasks()
        self._place_near_pointer_with_parent_offset(root)
        self.deiconify()
        self.lift()
        self.focus_force()

        if self.preload_code:
            self.load_code(self.preload_code)

    def _set_icon(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ico_path = os.path.join(base_dir, "resources", "josm_tagger.ico")
        png_path = os.path.join(base_dir, "resources", "josm_tagger.png")
        try:
            if sys.platform.startswith("win") and os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            elif os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _place_near_pointer_with_parent_offset(self, parent):
        self.update_idletasks()
        px = self.winfo_pointerx()
        py = self.winfo_pointery()
        ox = int(parent.winfo_width() * 0.30)
        oy = int(parent.winfo_height() * 0.30)
        x, y = _clamp_to_monitor(self, px + ox, py + oy)
        self.geometry(f"+{x}+{y}")

    def build_ui(self):
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=6, pady=6)

        tk.Label(top_frame, text="Code:").pack(side="left")
        self.entry_code = ttk.Combobox(top_frame, textvariable=self.code_var)
        self.entry_code.pack(side="left", fill="x", expand=True, padx=(4, 4))

        tk.Button(top_frame, text="New", command=self.new_code).pack(side="right", padx=4)

        paned = tk.PanedWindow(self, orient="horizontal", sashrelief="raised")
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        left_frame = tk.Frame(paned)
        tk.Label(left_frame, text="Available codes").pack(anchor="w", padx=4)
        list_container = tk.Frame(left_frame)
        list_container.pack(fill="both", expand=True)
        self.code_list = tk.Listbox(list_container)
        self.code_list.pack(side="left", fill="both", expand=True)
        scrollbar_left = ttk.Scrollbar(list_container, orient="vertical", command=self.code_list.yview)
        scrollbar_left.pack(side="right", fill="y")
        self.code_list.config(yscrollcommand=scrollbar_left.set)
        self.code_list.bind("<<ListboxSelect>>", self.on_code_select)
        self.code_list.bind("<Button-3>", self.show_code_context_menu)
        paned.add(left_frame, minsize=170)

        right_frame = tk.Frame(paned)
        tk.Label(right_frame, text="Assigned tags").pack(anchor="w", padx=4)

        tag_container = tk.Frame(right_frame)
        tag_container.pack(fill="both", expand=True)
        self.tag_list = tk.Listbox(tag_container)
        self.tag_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tag_container, orient="vertical", command=self.tag_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.tag_list.config(yscrollcommand=scrollbar.set)
        self.tag_list.bind("<Button-3>", self.show_tag_context_menu)

        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text="Add", width=10, command=self.add_tag).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Edit", width=10, command=self.edit_tag).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Remove", width=10, command=self.remove_tag).pack(side="left", padx=4)

        paned.add(right_frame, minsize=300)

        self.tag_context_menu = tk.Menu(self, tearoff=0)
        self.code_context_menu = tk.Menu(self, tearoff=0)

        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(bottom, text="OK", width=10, command=self.ok).pack(side="right", padx=(4, 0))
        tk.Button(bottom, text="Cancel", width=10, command=self.cancel).pack(side="right")

    def update_code_list(self):
        self.code_list.delete(0, tk.END)
        for c in sorted(self.working_codes.keys()):
            self.code_list.insert(tk.END, c)

    def auto_load_code(self, *_args):
        typed = self.code_var.get().strip()

        filtered = sorted([c for c in self.working_codes if c.lower().startswith(typed.lower())])
        self.entry_code["values"] = filtered if typed else sorted(self.working_codes.keys())

        if typed in self.working_codes:
            self.current_code = typed
            self._select_code_in_available_list(typed)
            self.update_tag_list()
        else:
            self.current_code = None
            self.tag_list.delete(0, tk.END)
            if filtered:
                self._select_code_in_available_list(filtered[0])
            else:
                self.code_list.selection_clear(0, tk.END)

    def _select_code_in_available_list(self, code):
        values = list(self.code_list.get(0, tk.END))
        if code not in values:
            return
        idx = values.index(code)
        self.code_list.selection_clear(0, tk.END)
        self.code_list.selection_set(idx)
        self.code_list.activate(idx)
        self.code_list.see(idx)

    def on_code_select(self, _event=None):
        sel = self.code_list.curselection()
        if not sel:
            return
        code = self.code_list.get(sel[0])
        if self._trace_id:
            self.code_var.trace_remove("write", self._trace_id)
        self.code_var.set(code)
        self._trace_id = self.code_var.trace_add("write", self.auto_load_code)
        self.current_code = code
        self.update_tag_list()

    def show_tag_context_menu(self, event):
        nearest = self.tag_list.nearest(event.y)
        size = self.tag_list.size()
        clicked_on_item = False

        if 0 <= nearest < size:
            bbox = self.tag_list.bbox(nearest)
            if bbox:
                x, y, w, h = bbox
                if y <= event.y <= y + h:
                    clicked_on_item = True

        self.tag_context_menu.delete(0, tk.END)
        self.tag_context_menu.add_command(label="Add", command=self.add_tag)

        if clicked_on_item:
            self.tag_list.selection_clear(0, tk.END)
            self.tag_list.selection_set(nearest)
            self.tag_list.activate(nearest)
            self.tag_context_menu.add_command(label="Edit", command=self.edit_tag)
            self.tag_context_menu.add_command(label="Remove", command=self.remove_tag)
        else:
            self.tag_list.selection_clear(0, tk.END)

        try:
            self.tag_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tag_context_menu.grab_release()

    def show_code_context_menu(self, event):
        nearest = self.code_list.nearest(event.y)
        size = self.code_list.size()
        clicked_on_item = False

        if 0 <= nearest < size:
            bbox = self.code_list.bbox(nearest)
            if bbox:
                _x, y, _w, h = bbox
                if y <= event.y <= y + h:
                    clicked_on_item = True

        self.code_context_menu.delete(0, tk.END)
        self.code_context_menu.add_command(label="New", command=self.new_code)

        if clicked_on_item:
            self.code_list.selection_clear(0, tk.END)
            self.code_list.selection_set(nearest)
            self.code_list.activate(nearest)
            code = self.code_list.get(nearest)
            if self._trace_id:
                self.code_var.trace_remove("write", self._trace_id)
            self.code_var.set(code)
            self._trace_id = self.code_var.trace_add("write", self.auto_load_code)
            self.current_code = code
            self.update_tag_list()

            self.code_context_menu.add_command(label="Rename", command=self.rename_code)
            self.code_context_menu.add_command(label="Delete", command=self.delete_code)
        else:
            self.code_list.selection_clear(0, tk.END)

        try:
            self.code_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.code_context_menu.grab_release()

    def load_code(self, code):
        if code not in self.working_codes:
            return
        if self._trace_id:
            self.code_var.trace_remove("write", self._trace_id)
        self.code_var.set(code)
        self._trace_id = self.code_var.trace_add("write", self.auto_load_code)
        self.current_code = code
        self._select_code_in_available_list(code)
        self.update_tag_list()

    def update_tag_list(self):
        self.tag_list.delete(0, tk.END)
        if not self.current_code or self.current_code not in self.working_codes:
            return
        for t in self.working_codes.get(self.current_code, []):
            self.tag_list.insert(tk.END, f"{t['key']} = {t['value']}")

    def _open_tag_properties(self, initial=None):
        form = TagPropertiesForm(self, config=self.config, key_value=initial)
        self.wait_window(form)
        return form.result

    def add_tag(self):
        if not self.current_code:
            messagebox.showwarning("Warning", "Select or enter a code first")
            return
        res = self._open_tag_properties()
        if res:
            if self.current_code not in self.working_codes:
                self.working_codes[self.current_code] = []
            self.working_codes[self.current_code].append(res)
            self.update_tag_list()

    def edit_tag(self):
        sel = self.tag_list.curselection()
        if not sel:
            return
        idx = sel[0]
        initial = self.working_codes[self.current_code][idx]
        res = self._open_tag_properties(initial)
        if res:
            self.working_codes[self.current_code][idx] = res
            self.update_tag_list()

    def remove_tag(self):
        sel = self.tag_list.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.working_codes[self.current_code][idx]
        self.update_tag_list()

    def new_code(self):
        name = simpledialog.askstring("New Code", "Enter code name:", parent=self)
        if name:
            name = name.strip()
            if name in self.working_codes:
                messagebox.showerror("Error", f"Code '{name}' already exists")
                return
            self.working_codes[name] = []
            self.update_code_list()
            self.load_code(name)

    def rename_code(self):
        if not self.current_code:
            return
        old = self.current_code
        new = simpledialog.askstring("Rename", f"Rename '{old}' to:", initialvalue=old, parent=self)
        if new:
            new = new.strip()
            if new == old:
                return
            if new in self.working_codes:
                messagebox.showerror("Error", f"Code '{new}' already exists")
                return
            self.working_codes[new] = self.working_codes.pop(old)
            self.update_code_list()
            self.load_code(new)

    def delete_code(self):
        if not self.current_code:
            return
        code = self.current_code
        if messagebox.askyesno("Delete", f"Delete code '{code}'?"):
            del self.working_codes[code]
            self.current_code = None
            self.code_var.set("")
            self.update_code_list()
            self.update_tag_list()

    def ok(self):
        self.source_codes.clear()
        self.source_codes.update(self.working_codes)
        save_codes(self.source_codes)
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

    def cancel(self):
        try:
            self.destroy()
        finally:
            TagEditorForm._instance = None

    def apply_font(self):
        font_conf = (
            self.config.get("font_family", "Segoe UI"),
            self.config.get("font_size", 10),
        )
        self.option_add("*Font", font_conf)

        def apply(widget):
            try:
                widget.configure(font=font_conf)
            except Exception:
                pass
            for child in widget.winfo_children():
                apply(child)

        apply(self)

    def apply_theme(self):
        apply_theme_colors(self, self.config)
        theme = get_active_theme(self.config)
        p_fg = theme.get("panel_fg")
        p_bg = theme.get("panel")
        
        # Stile TTK per Combobox
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("TCombobox", 
                        fieldbackground=p_bg, 
                        background=p_bg, 
                        foreground=p_fg,
                        arrowcolor=p_fg)
        
        # Dropdown colors
        self.option_add("*TCombobox*Listbox.background", p_bg)
        self.option_add("*TCombobox*Listbox.foreground", p_fg)
        
        def apply_extra(widget):
            if isinstance(widget, tk.Menu):
                try:
                    widget.configure(bg=p_bg, fg=p_fg, 
                                     activebackground="#0078d7", activeforeground="white")
                except:
                    pass

            if isinstance(widget, (tk.Entry, tk.Listbox)):
                try:
                    widget.configure(bg=p_bg, fg=p_fg)
                    if hasattr(widget, "configure") and "insertbackground" in widget.keys():
                        widget.configure(insertbackground=p_fg)
                except:
                    pass
            if isinstance(widget, tk.Listbox):
                try:
                    widget.configure(selectbackground="#0078d7", selectforeground="white")
                except:
                    pass
            for child in widget.winfo_children():
                apply_extra(child)
        
        apply_extra(self)
