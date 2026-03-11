# import json
# import os
# import logging
# import sys
# import tkinter as tk
# import threading
# import time
#
# import pyautogui
# import pygetwindow as gw
# import pyperclip
# import keyboard
#
#
# CODES_FILE = "codes.json"
# LOG_FILE = "josm_keyboard_sender.log"
#
#
# file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
# file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
# file_handler.setFormatter(file_formatter)
#
# console_handler = logging.StreamHandler(sys.stdout)
# console_handler.setFormatter(file_formatter)
#
# logging.basicConfig(
#     level=logging.DEBUG,
#     handlers=[file_handler, console_handler]
# )
#
#
# def load_codes():
#
#     with open(CODES_FILE, "r", encoding="utf-8") as f:
#         data = json.load(f)
#
#     logging.info("Loaded %d codes", len(data))
#     return data
#
#
# def code_matches_search(code, text):
#
#     text = text.lower()
#     return text in code.lower()
#
#
# def focus_josm_window():
#
#     windows = gw.getWindowsWithTitle("Java OpenStreetMap Editor")
#
#     if not windows:
#         logging.warning("JOSM window not found")
#         print("[WARN] JOSM window not found")
#         return False
#
#     win = windows[0]
#
#     try:
#         win.activate()
#     except:
#
#         try:
#             win.minimize()
#             win.restore()
#             win.activate()
#         except Exception as e:
#             logging.error("Cannot activate JOSM window: %s", e)
#             return False
#
#     time.sleep(0.3)
#     return True
#
#
# class CodeForm:
#
#     def __init__(self, root):
#
#         self.root = root
#         self.codes = load_codes()
#         self.codes_mtime = os.path.getmtime(CODES_FILE)
#
#         self.internal_update = False
#
#         root.title("JOSM Tag Sender")
#         root.geometry("520x420")
#         root.attributes("-topmost", True)
#
#         self.build_ui()
#
#         self.update_list()
#         self.watch_json()
#
#         self.register_hotkey()
#
#     def build_ui(self):
#
#         top = tk.Frame(self.root)
#         top.pack(fill="x", padx=6, pady=6)
#
#         tk.Label(top, text="Code:").pack(side="left")
#
#         self.code_var = tk.StringVar()
#         self.code_var.trace_add("write", self.on_code_change)
#
#         self.entry = tk.Entry(top, textvariable=self.code_var)
#         self.entry.pack(side="left", fill="x", expand=True, padx=5)
#
#         self.entry.bind("<Return>", self.apply_code)
#         self.entry.bind("<Down>", self.move_to_list)
#
#         apply_btn = tk.Button(top, text="Apply", command=self.apply_code)
#         apply_btn.pack(side="right")
#
#         middle = tk.Frame(self.root)
#         middle.pack(fill="both", expand=True, padx=6, pady=6)
#
#         self.code_list = tk.Listbox(middle)
#         self.code_list.pack(side="left", fill="both", expand=True)
#
#         self.code_list.bind("<<ListboxSelect>>", self.on_list_select)
#         self.code_list.bind("<Double-Button-1>", self.on_list_double_click)
#
#         scrollbar = tk.Scrollbar(middle, command=self.code_list.yview)
#         scrollbar.pack(side="left", fill="y")
#
#         self.code_list.config(yscrollcommand=scrollbar.set)
#
#         preview_frame = tk.LabelFrame(self.root, text="Tag preview")
#         preview_frame.pack(fill="both", padx=6, pady=6)
#
#         self.preview = tk.Text(preview_frame, height=8)
#         self.preview.pack(fill="both", expand=True)
#
#         bottom = tk.Frame(self.root)
#         bottom.pack(fill="x", padx=6, pady=6)
#
#         tk.Button(
#             bottom,
#             text="Reload codes",
#             command=self.manual_reload
#         ).pack(fill="x")
#
#     def register_hotkey(self):
#
#         def hotkey_handler():
#
#             logging.info("CTRL+NUM0 detected")
#             print("[INFO] CTRL+NUM0 detected")
#
#             self.root.after(0, self.focus_input)
#
#         keyboard.add_hotkey("ctrl+num 0", hotkey_handler)
#
#     def focus_input(self):
#
#         try:
#
#             self.root.deiconify()
#             self.root.lift()
#             self.root.attributes("-topmost", True)
#
#             self.root.after(
#                 10,
#                 lambda: self.root.attributes("-topmost", False)
#             )
#
#             self.entry.focus_set()
#             self.entry.select_range(0, tk.END)
#
#         except Exception as e:
#             logging.error("Focus failed: %s", e)
#
#     def on_code_change(self, *args):
#
#         if self.internal_update:
#             return
#
#         self.update_list()
#
#     def update_list(self):
#
#         text = self.code_var.get().strip()
#
#         self.code_list.delete(0, tk.END)
#
#         for code in sorted(self.codes):
#
#             if text and not code_matches_search(code, text):
#                 continue
#
#             self.code_list.insert(tk.END, code)
#
#         if self.code_list.size() > 0:
#
#             first = self.code_list.get(0)
#             self.update_preview(first)
#
#         else:
#
#             self.preview.delete("1.0", tk.END)
#
#     def update_preview(self, code):
#
#         self.preview.delete("1.0", tk.END)
#
#         if code not in self.codes:
#             return
#
#         for p in self.codes[code]:
#
#             line = f"{p['key']} = {p['value']}\n"
#             self.preview.insert(tk.END, line)
#
#     def on_list_select(self, event):
#
#         selection = self.code_list.curselection()
#
#         if not selection:
#             return
#
#         code = self.code_list.get(selection[0])
#
#         self.internal_update = True
#         self.code_var.set(code)
#         self.internal_update = False
#
#         self.update_preview(code)
#
#     def on_list_double_click(self, event):
#
#         selection = self.code_list.curselection()
#
#         if not selection:
#             return
#
#         code = self.code_list.get(selection[0])
#
#         self.internal_update = True
#         self.code_var.set(code)
#         self.internal_update = False
#
#         self.apply_code()
#
#     def move_to_list(self, event):
#
#         if self.code_list.size() == 0:
#             return
#
#         self.code_list.focus_set()
#         self.code_list.selection_clear(0, tk.END)
#         self.code_list.selection_set(0)
#         self.code_list.activate(0)
#
#     def apply_code(self, event=None):
#
#         code = self.code_var.get().strip()
#
#         if code not in self.codes:
#
#             logging.warning("Code not found: %s", code)
#             print("[WARN] Code not found:", code)
#             return
#
#         pairs = self.codes[code]
#
#         logging.info("Applying code %s", code)
#         print("[INFO] Applying", code)
#
#         threading.Thread(
#             target=self.send_tags_to_josm,
#             args=(pairs,),
#             daemon=True
#         ).start()
#
#         self.code_var.set("")
#
#     def send_tags_to_josm(self, pairs):
#
#         if not focus_josm_window():
#
#             print("[ERROR] Cannot activate JOSM")
#             return
#
#         print("[INFO] Sending tags...")
#
#         pyautogui.hotkey("alt", "a")
#
#         time.sleep(0.2)
#
#         for i, pair in enumerate(pairs):
#
#             pyautogui.hotkey("ctrl", "a")
#             pyautogui.press("delete")
#
#             pyperclip.copy(pair["key"])
#             pyautogui.hotkey("ctrl", "v")
#
#             pyautogui.press("tab")
#
#             pyautogui.hotkey("ctrl", "a")
#             pyautogui.press("delete")
#
#             pyperclip.copy(pair["value"])
#             pyautogui.hotkey("ctrl", "v")
#
#             if i < len(pairs) - 1:
#                 pyautogui.hotkey("shift", "enter")
#             else:
#                 pyautogui.press("enter")
#
#         logging.info("Tags sent")
#
#     def manual_reload(self):
#
#         logging.info("Manual reload requested")
#         print("[INFO] Reloading codes.json")
#
#         try:
#
#             self.codes = load_codes()
#             self.codes_mtime = os.path.getmtime(CODES_FILE)
#
#             self.update_list()
#
#             print("[INFO] Reload completed")
#
#         except Exception as e:
#
#             logging.error("Reload failed: %s", e)
#             print("[ERROR] Reload failed:", e)
#
#     def reload_codes_if_changed(self):
#
#         mtime = os.path.getmtime(CODES_FILE)
#
#         if mtime != self.codes_mtime:
#
#             logging.info("codes.json changed, reloading")
#             print("[INFO] codes.json changed, reloading")
#
#             self.codes = load_codes()
#             self.codes_mtime = mtime
#
#             self.update_list()
#
#     def watch_json(self):
#
#         self.reload_codes_if_changed()
#         self.root.after(2000, self.watch_json)
#
#
# def main():
#
#     root = tk.Tk()
#     app = CodeForm(root)
#     root.mainloop()
#
#
# if __name__ == "__main__":
#     main()