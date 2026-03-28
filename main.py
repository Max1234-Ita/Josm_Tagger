from forms.main_form import MainForm
from hotkeys import start_hotkeys
import tkinter as tk

appname = 'JOSM Tagger'
appversion = '0.1.0'
author = 'By M. Mula, 2026'
appinfo = f'{appname} v.{appversion} - {author}'  # full text to use in About

# --- Functions ---
def on_hotkey(app):
    # re-enter Tkinter thread
    app.root.after(0, app.handle_hotkey)


def main():
    root = tk.Tk()              # create the main Tk window
    app = MainForm(root)        # pass root to the constructor

    start_hotkeys(lambda: on_hotkey(app))

    root.mainloop()


if __name__ == "__main__":
    main()