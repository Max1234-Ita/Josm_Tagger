import tkinter as tk

from forms.main_form import MainForm


def main():

    root = tk.Tk()

    app = MainForm(root)

    root.mainloop()


if __name__ == "__main__":
    main()