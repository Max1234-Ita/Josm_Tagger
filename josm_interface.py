import pyautogui
import pygetwindow as gw
import pyperclip
import time


def focus_josm(main_root=None):

    windows = gw.getWindowsWithTitle("Java OpenStreetMap Editor")

    if not windows:
        return False

    win = windows[0]

    if main_root is not None:
        try:
            # Keep main_form topmost while JOSM gets activated.
            if not bool(main_root.attributes("-topmost")):
                main_root.attributes("-topmost", True)
                main_root.update_idletasks()
        except:
            pass

    try:
        print('Activating JOSM window')
        win.activate()      # TODO - Activate fa sparire main_form E' topmost?.
    except:
        print('Restoring JOSM window')
        win.minimize()
        win.restore()
        win.activate()

    time.sleep(0.3)

    return True


def send_tags(pairs, main_root=None):

    if not focus_josm(main_root=main_root):
        return

    pyautogui.hotkey("alt", "a")

    time.sleep(0.2)

    for i, p in enumerate(pairs):
        print(f"Sending pair: {p['key']}={p['value']}")
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("delete")

        pyperclip.copy(p["key"])
        pyautogui.hotkey("ctrl", "v")

        pyautogui.press("tab")

        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("delete")

        pyperclip.copy(p["value"])
        pyautogui.hotkey("ctrl", "v")

        if i < len(pairs) - 1:
            pyautogui.hotkey("shift", "enter")
        else:
            pyautogui.press("enter")

    pass
