import os
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from config_manager import debug_print, is_debug_mode, load_config

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
# JOSM_WINDOW_TITLE will be loaded from config or default to "Java OpenStreetMap Editor"
DEBUG_MODE = is_debug_mode()


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


def _should_keep_main_form_visible():
    try:
        config = load_config()
    except Exception:
        return False

    beh = config.get("behaviour", {})
    return beh.get("on_apply", "keep_visible") == "keep_visible"


def _remote_control_request(path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{JOSM_REMOTE_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"

    debug_print(f"Calling JOSM Remote Control: {url}", cfg=DEBUG_MODE)
    try:
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=2) as response:
            body = response.read().decode("utf-8", errors="replace")
            debug_print(f"JOSM Remote Control status: {response.status}", cfg=DEBUG_MODE)
            if body:
                debug_print(f"JOSM Remote Control response: {body[:500]}", cfg=DEBUG_MODE)
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        debug_print(f"JOSM Remote Control HTTP error: {e.code} {body[:500]}", cfg=DEBUG_MODE)
    except urllib.error.URLError as e:
        debug_print(f"JOSM Remote Control unavailable: {e}", cfg=DEBUG_MODE)
    except Exception as e:
        debug_print(f"JOSM Remote Control failed: {e}", cfg=DEBUG_MODE)

    return False


def _format_addtags(pairs):
    return "|".join(f"{p['key']}={p['value']}" for p in pairs)


def _confirm_remote_control_dialog():
    if not JOSM_REMOTE_AUTO_CONFIRM:
        return

    if is_linux():
        debug_print("Skipping auto-confirm on Linux.", cfg=DEBUG_MODE)
        return

    debug_print("Trying to confirm JOSM Remote Control dialog", cfg=DEBUG_MODE)
    time.sleep(JOSM_REMOTE_CONFIRM_DELAY)
    try:
        if pyautogui:
            pyautogui.FAILSAFE = False
            pyautogui.press("enter")
            debug_print("Sent Enter to confirm JOSM Remote Control dialog", cfg=DEBUG_MODE)
        else:
            debug_print("pyautogui not available, skipping auto-confirm.", cfg=DEBUG_MODE)
    except Exception as e:
        debug_print(f"Could not auto-confirm JOSM Remote Control dialog: {e}", cfg=DEBUG_MODE)


def send_tags_remote_control(pairs):
    debug_print("Trying JOSM Remote Control", cfg=DEBUG_MODE)

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
        debug_print(f"Sending pair: {p['key']}={p['value']}", cfg=DEBUG_MODE)
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
    def _release_topmost():
        if main_root is None or _should_keep_main_form_visible():
            return
        try:
            main_root.attributes("-topmost", False)
        except Exception:
            pass

    config = load_config()
    josm_window_title = config.get("josm_window_title", "Java OpenStreetMap Editor")

    if is_linux():
        if main_root is not None:
            try:
                if not bool(main_root.attributes("-topmost")):
                    main_root.attributes("-topmost", True)
                    main_root.update_idletasks()
            except Exception:
                pass

        for command in (
            ["wmctrl", "-a", josm_window_title],
            ["xdotool", "search", "--name", josm_window_title],
        ):
            if not shutil.which(command[0]):
                continue

            try:
                if command[0] == "wmctrl":
                    debug_print("Activating JOSM window via wmctrl", cfg=DEBUG_MODE)
                    subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if main_root is not None:
                        main_root.after(100, _release_topmost)
                    time.sleep(0.2)
                    return True

                debug_print("Searching JOSM window via xdotool", cfg=DEBUG_MODE)
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                window_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                if not window_ids:
                    continue

                window_id = window_ids[-1]
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", window_id],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                subprocess.run(
                    ["xdotool", "windowraise", window_id],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if main_root is not None and not _should_keep_main_form_visible():
                    main_root.after(100, _release_topmost)
                time.sleep(0.2)
                return True
            except Exception as e:
                debug_print(f"Could not activate JOSM on Linux using {command[0]}: {e}", cfg=DEBUG_MODE)

        print("Could not focus JOSM on Linux.")
        return False

    if not gw:
        print("pygetwindow not available, cannot focus JOSM.")
        return False

    windows = gw.getWindowsWithTitle(josm_window_title)

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
        debug_print("Activating JOSM window", cfg=DEBUG_MODE)
        win.activate()
    except:
        debug_print("Restoring JOSM window", cfg=DEBUG_MODE)
        win.minimize()
        win.restore()
        win.activate()

    if main_root is not None and not _should_keep_main_form_visible():
        main_root.after(100, _release_topmost)

    time.sleep(0.3)

    return True

def send_tags(pairs, main_root=None, control_method=None):
    method = resolve_control_method(control_method)
    debug_print(f"Using JOSM control method: {method}", cfg=DEBUG_MODE)

    if method == JOSM_CONTROL_REMOTE:
        return send_tags_remote_control(pairs)

    return send_tags_gui_automation(pairs, main_root=main_root)
