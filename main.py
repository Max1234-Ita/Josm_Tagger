from forms.main_form import MainForm
from hotkeys import start_hotkeys
import tkinter as tk

appname = 'JOSM Tagger'
appversion = '0.1.7'
author = 'By Max1234-ITA, 2026'
appinfo = f'{appname} v.{appversion}\n- {author} -'  # Full text to use in About

# --- Functions ---
def on_hotkey(app):
    # Activate widget by pressing the Hotkey combination
    app.root.after(0, app.handle_hotkey)


def main():
    root = tk.Tk()              # create the main Tk window
    app = MainForm(root)        # pass root to the constructor

    start_hotkeys(lambda: on_hotkey(app))

    root.mainloop()

    pass

if __name__ == "__main__":
    main()