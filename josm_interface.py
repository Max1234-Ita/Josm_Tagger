import platform
import subprocess
import pyperclip
import time
import sys
import os
import urllib.error
import urllib.parse
import urllib.request


JOSM_WINDOW_MATCHES = (
    "josm",
    "java openstreetmap editor",
    "openstreetmap editor",
    "org.openstreetmap.josm",
)
APP_WINDOW_MATCHES = (
    "josm tagger",
)
APP_PROCESS_MATCHES = (
    "josm_tagger",
    "josm tagger",
    "pycharmprojects/josm_tagger",
    "/josm_tagger/",
)
JOSM_PROCESS_MATCHES = (
    "org.openstreetmap.josm",
    "josm.jar",
    "/josm",
    " josm",
)
JOSM_REMOTE_BASE_URL = "http://127.0.0.1:8111"
JOSM_REMOTE_AUTO_CONFIRM = True
JOSM_REMOTE_CONFIRM_DELAY = 0.7


def _run_window_command(command):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=2
        )
    except FileNotFoundError:
        print(f"DEBUG: Command not found: {command[0]}")
    except Exception as e:
        print(f"DEBUG: Error running {' '.join(command)}: {e}")
    return None


def _line_window_id(line):
    parts = line.split()
    return parts[0] if parts else None


def _is_josm_window_line(line):
    lower_line = line.lower()
    if any(match in lower_line for match in APP_WINDOW_MATCHES):
        return False
    return any(match in lower_line for match in JOSM_WINDOW_MATCHES)


def _is_josm_process_line(line):
    lower_line = line.lower()
    if any(match in lower_line for match in APP_PROCESS_MATCHES):
        return False
    return any(match in lower_line for match in JOSM_PROCESS_MATCHES)


def _get_josm_process_ids_linux():
    result = _run_window_command(["pgrep", "-a", "-f", "josm"])
    if result is None or result.returncode != 0:
        return set()

    pids = set()
    for line in result.stdout.splitlines():
        if not _is_josm_process_line(line):
            continue
        parts = line.split(maxsplit=1)
        if parts and parts[0].isdigit():
            pids.add(parts[0])
    print(f"DEBUG: JOSM candidate process IDs: {sorted(pids)}")
    return pids


def _get_josm_window_linux():
    """Find JOSM window ID on Linux using wmctrl."""
    print("DEBUG: Searching for JOSM window on Linux...")

    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        print("DEBUG: Wayland session detected. wmctrl can only see XWayland windows.")

    for command in (["wmctrl", "-lx"], ["wmctrl", "-l"]):
        result = _run_window_command(command)
        if result is None:
            continue
        print(f"DEBUG: {' '.join(command)} output:\n{result.stdout}")
        for line in result.stdout.splitlines():
            if _is_josm_window_line(line):
                window_id = _line_window_id(line)
                if window_id:
                    print(f"DEBUG: Found JOSM window ID by title/class: {window_id}")
                    return window_id

    pids = _get_josm_process_ids_linux()
    if pids:
        result = _run_window_command(["wmctrl", "-lp"])
        if result is not None:
            print(f"DEBUG: wmctrl -lp output:\n{result.stdout}")
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[2] in pids:
                    window_id = parts[0]
                    print(f"DEBUG: Found JOSM window ID by PID: {window_id}")
                    return window_id

    print("DEBUG: JOSM window not found")
    return None


def _activate_window_linux(window_id):
    """Activate a window on Linux using wmctrl."""
    print(f"DEBUG: Activating window ID: {window_id}")

    print("DEBUG: Restoring and activating window...")
    result = _run_window_command(["wmctrl", "-i", "-R", window_id])
    if result is not None:
        print(f"DEBUG: wmctrl restore result: returncode={result.returncode}")
        if result.returncode == 0:
            return True
        print(f"DEBUG: wmctrl stderr: {result.stderr}")

    print("DEBUG: Trying fallback activation...")
    result = _run_window_command(["wmctrl", "-i", "-a", window_id])
    if result is not None:
        print(f"DEBUG: wmctrl fallback result: returncode={result.returncode}")
        if result.returncode == 0:
            return True
        print(f"DEBUG: wmctrl fallback stderr: {result.stderr}")

    try:
        result = subprocess.run(
            ["xdotool", "windowactivate", "--sync", window_id],
            capture_output=True,
            text=True,
            timeout=2
        )
        print(f"DEBUG: xdotool activation result: returncode={result.returncode}")
        if result.returncode == 0:
            return True
        print(f"DEBUG: xdotool stderr: {result.stderr}")
    except FileNotFoundError:
        print("DEBUG: xdotool not available for fallback activation")
    except Exception as e:
        print(f"DEBUG: xdotool activation failed: {e}")
        return False

    return False


def _is_wayland_session():
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def _remote_control_request(path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{JOSM_REMOTE_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"

    print(f"DEBUG: Calling JOSM Remote Control: {url}")
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"DEBUG: JOSM Remote Control status: {response.status}")
            if body:
                print(f"DEBUG: JOSM Remote Control response: {body[:500]}")
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"DEBUG: JOSM Remote Control HTTP error: {e.code} {body[:500]}")
    except urllib.error.URLError as e:
        print(f"DEBUG: JOSM Remote Control unavailable: {e}")
    except Exception as e:
        print(f"DEBUG: JOSM Remote Control failed: {e}")

    return False


def _format_addtags(pairs):
    return "|".join(f"{p['key']}={p['value']}" for p in pairs)


def _send_tags_remote_control(pairs):
    print("DEBUG: Trying JOSM Remote Control fallback")

    if not _remote_control_request("/version"):
        print(
            "DEBUG: JOSM Remote Control is not available. "
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

    # Some JOSM versions insist on a bbox for /zoom even when currentselection
    # is used. Keep it tiny and ask JOSM to zoom to the selected objects.
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


def _confirm_remote_control_dialog():
    if not JOSM_REMOTE_AUTO_CONFIRM:
        return

    print("DEBUG: Trying to confirm JOSM Remote Control dialog")
    time.sleep(JOSM_REMOTE_CONFIRM_DELAY)
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.press("enter")
        print("DEBUG: Sent Enter to confirm JOSM Remote Control dialog")
    except Exception as e:
        print(f"DEBUG: Could not auto-confirm JOSM Remote Control dialog: {e}")


def focus_josm(main_root=None):
    """Focus JOSM window (cross-platform)."""
    print("DEBUG: focus_josm() called")
    system = platform.system()
    print(f"DEBUG: System detected: {system}")

    if system == "Linux":
        print("DEBUG: Using Linux path for focus_josm")
        window_id = _get_josm_window_linux()
        if not window_id:
            print("DEBUG: JOSM window not found, returning False")
            return False

        if main_root is not None:
            try:
                # Keep main_form topmost while JOSM gets activated.
                if not bool(main_root.attributes("-topmost")):
                    main_root.attributes("-topmost", True)
                    main_root.update_idletasks()
            except:
                pass

        print('Activating JOSM window')
        if not _activate_window_linux(window_id):
            print("DEBUG: Failed to activate JOSM window")
            return False

        time.sleep(0.3)
        return True

    else:  # Windows / macOS
        try:
            import pygetwindow as gw
        except ImportError:
            print("DEBUG: pygetwindow not available on this platform")
            return False

        windows = gw.getWindowsWithTitle("Java OpenStreetMap Editor")

        if not windows:
            print("DEBUG: JOSM window not found on Windows/macOS")
            return False

        win = windows[0]

        if main_root is not None:
            try:
                if not bool(main_root.attributes("-topmost")):
                    main_root.attributes("-topmost", True)
                    main_root.update_idletasks()
            except:
                pass

        try:
            print('Activating JOSM window')
            win.activate()
        except:
            print('Restoring JOSM window')
            win.minimize()
            win.restore()
            win.activate()

        time.sleep(0.3)
        return True


def send_tags(pairs, main_root=None):
    """Send tags to JOSM (cross-platform)."""
    print("DEBUG: send_tags() called with pairs:", pairs)

    in_debug = 'pydevd' in sys.modules

    if platform.system() == "Linux":
        if in_debug:
            # Check for Debug mode (Tag sending will work only in production environment)
            print("DEBUG MODE DETECTED: Printing tags instead of sending to JOSM")
            for pair in pairs:
                print(f"  [TAG] {pair['key']} = {pair['value']}")
            print("DEBUG MODE: Tag sending skipped (no X11 display available)")
            return

        if _is_wayland_session():
            if _send_tags_remote_control(pairs):
                print("DEBUG: Tags sent through JOSM Remote Control")
                return
            print("DEBUG: Remote Control fallback failed, trying keyboard path")

    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        print("DEBUG: pyautogui imported successfully")
    except Exception as e:
        print(f"Warning: Could not import pyautogui: {e}")
        print("Tag sending is disabled in this session.")
        return

    print("DEBUG: Calling focus_josm()")
    if not focus_josm(main_root=main_root):
        print("DEBUG: focus_josm() returned False, tag sending aborted")
        return

    print("DEBUG: JOSM focused, sending Alt+A")

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
