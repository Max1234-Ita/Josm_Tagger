from forms.main_form import MainForm
import tkinter as tk
from app_metadata import APP_AUTHOR, APP_INFO, APP_NAME, APP_VERSION

appname = APP_NAME
appversion = APP_VERSION
author = APP_AUTHOR
appinfo = APP_INFO  # Full text to use in About

appicon_ico = 'resources/josm_tagger.ico'  # Path to the icon file (relative to the script)
appicon_png = 'resources/josm_tagger.png'  # Path to the PNG icon file (relative to the script)

def main():
    root = tk.Tk()              # create the main Tk window
    app = MainForm(root)        # pass root to the constructor

    root.mainloop()

if __name__ == "__main__":
    main()
