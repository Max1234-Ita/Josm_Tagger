from forms.main_form import MainForm
from hotkeys import start_hotkeys
import tkinter as tk

appname = 'JOSM Tagger'
appversion = '0.1.0'
author = 'By M. Mula, 2026'
appinfo = f'{appname} v.{appversion} - {author}'  # testo completo da usare nell'About

# --- Funzioni ---
def on_hotkey(app):
    # rientra nel thread Tkinter
    app.root.after(0, app.handle_hotkey)


def main():
    root = tk.Tk()              # crea la finestra Tk principale
    app = MainForm(root)        # passa root al costruttore

    start_hotkeys(lambda: on_hotkey(app))

    root.mainloop()


if __name__ == "__main__":
    main()