import pyautogui
import pygetwindow as gw
import pyperclip
import time


def focus_josm():

    windows = gw.getWindowsWithTitle("Java OpenStreetMap Editor")

    if not windows:
        return False

    win = windows[0]

    try:
        win.activate()
    except:
        win.minimize()
        win.restore()
        win.activate()

    time.sleep(0.3)

    return True


def send_tags(pairs):

    if not focus_josm():
        return

    pyautogui.hotkey("alt", "a")

    time.sleep(0.2)

    for i, p in enumerate(pairs):

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