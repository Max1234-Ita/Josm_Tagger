from forms.main_form import MainForm
import tkinter as tk

appname = 'JOSM Tagger'
appversion = '0.1.11'
author = 'By Max1234-ITA, 2026'
appinfo = f'{appname} v.{appversion}\n- {author} -'  # Full text to use in About

appicon_ico = 'resources/josm_tagger.ico'  # Path to the icon file (relative to the script)
appicon_png = 'resources/josm_tagger.png'  # Path to the PNG icon file (relative to the script)

def main():
    root = tk.Tk()              # create the main Tk window
    app = MainForm(root)        # pass root to the constructor

    root.mainloop()

if __name__ == "__main__":
    main()
