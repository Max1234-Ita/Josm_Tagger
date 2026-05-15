
from forms.main_form import MainForm
from hotkeys import start_hotkeys
import tkinter as tk

appname = 'JOSM Tagger'
appversion = '0.1.8'
author = 'By Max1234-ITA, 2026'
appinfo = f'{appname} v.{appversion}\n- {author} -'  # Full text to use in About

appicon_ico = 'resources/josm_tagger.ico'  # Path to the icon file (relative to the script)
appicon_png = 'resources/josm_tagger.png'  # Path to the PNG icon file (relative to the script)

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