import os
import platform
import time
import urllib.error
import urllib.parse
import urllib.request

# Conditional import for Windows-specific libraries
if platform.system() == "Windows":
    try:
        import pyautogui
        import pygetwindow as gw
        import pyperclip
    except ImportError:
        pyautogui = None
        gw = None
        pyperclip = None
else:
    pyautogui = None
    gw = None
    pyperclip = None


JOSM_REMOTE_BASE_URL = "http://127.0.0.1:8111"
JOSM_REMOTE_AUTO_CONFIRM = True
JOSM_REMOTE_CONFIRM_DELAY = 0.7
JOSM_CONTROL_GUI_AUTOMATION = "gui_automation"
JOSM_CONTROL_REMOTE = "remote_control"


def _is_wayland_session():
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def is_linux():
    return platform.system() == "Linux"


def resolve_control_method(control_method=None):
    if is_linux():
        return JOSM_CONTROL_REMOTE

    if control_method == JOSM_CONTROL_REMOTE:
        return JOSM_CONTROL_REMOTE

    return JOSM_CONTROL_GUI_AUTOMATION


def _remote_control_request(path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{JOSM_REMOTE_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"

    print(f"Calling JOSM Remote Control: {url}")
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"JOSM Remote Control status: {response.status}")
            if body:
                print(f"JOSM Remote Control response: {body[:500]}")
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"JOSM Remote Control HTTP error: {e.code} {body[:500]}")
    except urllib.error.URLError as e:
        print(f"JOSM Remote Control unavailable: {e}")
    except Exception as e:
        print(f"JOSM Remote Control failed: {e}")

    return False


def _format_addtags(pairs):
    return "|".join(f"{p['key']}={p['value']}" for p in pairs)


def _confirm_remote_control_dialog():
    if not JOSM_REMOTE_AUTO_CONFIRM:
        return

    if is_linux():
        print("Skipping auto-confirm on Linux.")
        return

    print("Trying to confirm JOSM Remote Control dialog")
    time.sleep(JOSM_REMOTE_CONFIRM_DELAY)
    try:
        if pyautogui:
            pyautogui.FAILSAFE = False
            pyautogui.press("enter")
            print("Sent Enter to confirm JOSM Remote Control dialog")
        else:
            print("pyautogui not available, skipping auto-confirm.")
    except Exception as e:
        print(f"Could not auto-confirm JOSM Remote Control dialog: {e}")


def send_tags_remote_control(pairs):
    print("Trying JOSM Remote Control")

    if not _remote_control_request("/version"):
        print(
            "JOSM Remote Control is not available. "
            "Enable it in JOSM: Preferences > Remote Control."
        )
        return False

    params = {
        "select": "currentselection",
        "addtags": _format_addtags(pairs),
    }
    if _remote_control_request("/zoom", params):
        _confirm_remote_control_dialog()
        return True

    params.update({
        "left": "0",
        "right": "0.000001",
        "bottom": "0",
        "top": "0.000001",
        "zoom_mode": "selection",
    })
    if _remote_control_request("/zoom", params):
        _confirm_remote_control_dialog()
        return True

    return False


def send_tags_gui_automation(pairs, main_root=None):
    if not pyautogui or not gw or not pyperclip:
        print("GUI automation libraries not available on this OS.")
        return False

    if not focus_josm(main_root=main_root):
        return False

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

    return True


def focus_josm(main_root=None):
    if not gw:
        print("pygetwindow not available, cannot focus JOSM.")
        return False

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

def send_tags(pairs, main_root=None, control_method=None):
    method = resolve_control_method(control_method)
    print(f"Using JOSM control method: {method}")

    if method == JOSM_CONTROL_REMOTE:
        return send_tags_remote_control(pairs)

    return send_tags_gui_automation(pairs, main_root=main_root)