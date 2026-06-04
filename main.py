import tkinter as tk
import fcntl
import os
import signal
import sys
import time
from pathlib import Path
from app_metadata import APP_AUTHOR, APP_INFO, APP_NAME, APP_VERSION
from forms.main_form import MainForm

appname = APP_NAME
appversion = APP_VERSION
author = APP_AUTHOR
appinfo = APP_INFO  # Full text to use in About

appicon_ico = 'resources/josm_tagger.ico'  # Path to the icon file (relative to the script)
appicon_png = 'resources/josm_tagger.png'  # Path to the PNG icon file (relative to the script)

# --- Single Instance Logic ---
LOCK_FILE_PATH = Path.home() / ".josm_tagger_lock"
PID_FILE_PATH = Path.home() / ".josm_tagger.pid"
LOCK_FILE = None


def _read_lock_pid():
    try:
        with open(LOCK_FILE_PATH, "r", encoding="utf-8") as f:
            data = f.read().strip()
            return data or "unknown"
    except OSError:
        return "unknown"


def _read_pid_file():
    try:
        with open(PID_FILE_PATH, "r", encoding="utf-8") as f:
            data = f.read().strip()
            return data or "unknown"
    except OSError:
        return "unknown"


def _pid_is_running(pid_text):
    try:
        pid = int(str(pid_text).strip())
        if pid <= 0:
            return False
    except Exception:
        return False

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists, but we may not have permission to signal it.
        return True
    except OSError:
        return False


def _pid_looks_like_josm_tagger(pid_text):
    try:
        pid = int(str(pid_text).strip())
        if pid <= 0:
            return False
    except Exception:
        return False

    if not sys.platform.startswith("linux"):
        return False

    try:
        cmdline_path = Path(f"/proc/{pid}/cmdline")
        if not cmdline_path.exists():
            return False
        raw = cmdline_path.read_bytes().replace(b"\x00", b" ").decode("utf-8", "ignore").lower()
        return "josm-tagger" in raw or "josmtagger" in raw or "main.py" in raw
    except OSError:
        return False


def _terminate_pid(pid_text, timeout=2.0):
    try:
        pid = int(str(pid_text).strip())
        if pid <= 0:
            return False
    except Exception:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    except OSError:
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _pid_is_running(pid):
            return True
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    except OSError:
        return False

    deadline = time.time() + 1.0
    while time.time() < deadline:
        if not _pid_is_running(pid):
            return True
        time.sleep(0.1)

    return not _pid_is_running(pid)


def _clear_lock_files():
    for path in (LOCK_FILE_PATH, PID_FILE_PATH):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

def acquire_lock():
    global LOCK_FILE
    try:
        def _try_acquire():
            global LOCK_FILE
            LOCK_FILE = open(LOCK_FILE_PATH, 'a+', encoding="utf-8")
            # Acquire an exclusive lock, non-blocking
            fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
            pid_text = str(os.getpid())
            LOCK_FILE.seek(0)
            LOCK_FILE.truncate()
            LOCK_FILE.write(pid_text)
            LOCK_FILE.flush()
            with open(PID_FILE_PATH, "w", encoding="utf-8") as pid_file:
                pid_file.write(pid_text)
            print(f"Acquired lock: {LOCK_FILE_PATH}")
            return True

        if _try_acquire():
            return True
    except IOError:
        other_pid = _read_pid_file()
        if other_pid == "unknown":
            other_pid = _read_lock_pid()
        if other_pid != "unknown" and not _pid_is_running(other_pid):
            print(
                f"Stale lock detected (pid={other_pid}). "
                f"Cleaning up {LOCK_FILE_PATH} and retrying."
            )
            try:
                if LOCK_FILE is not None:
                    LOCK_FILE.close()
            except OSError:
                pass
            LOCK_FILE = None
            _clear_lock_files()
            try:
                return _try_acquire()
            except IOError:
                pass
        if other_pid != "unknown" and _pid_looks_like_josm_tagger(other_pid):
            print(f"Existing JOSM Tagger instance detected (pid={other_pid}). Attempting takeover.")
            if _terminate_pid(other_pid):
                print(f"Existing instance terminated (pid={other_pid}). Retrying lock acquisition.")
                _clear_lock_files()
                try:
                    return _try_acquire()
                except IOError:
                    pass
            else:
                print(f"Warning: could not terminate existing instance (pid={other_pid}).")
        print(
            f"Another instance is already running (pid={other_pid}). "
            f"Could not acquire lock: {LOCK_FILE_PATH}"
        )
        return False

def release_lock():
    global LOCK_FILE
    if LOCK_FILE:
        fcntl.flock(LOCK_FILE, fcntl.LOCK_UN)
        LOCK_FILE.close()
        LOCK_FILE = None
        print(f"Released lock: {LOCK_FILE_PATH}")
        # Optionally remove the lock file, though it's not strictly necessary
        # if the lock is properly released.
        try:
            LOCK_FILE_PATH.unlink(missing_ok=True)
        except OSError as e:
            print(f"Warning: Could not remove lock file {LOCK_FILE_PATH}: {e}")
        try:
            PID_FILE_PATH.unlink(missing_ok=True)
        except OSError as e:
            print(f"Warning: Could not remove pid file {PID_FILE_PATH}: {e}")

def main():
    if not acquire_lock():
        # If another instance is running, just exit.
        # On Wayland, bringing the existing instance to front is complex.
        # The user will have to manually switch to the existing window.
        sys.exit(0)

    # Ensure lock is released on exit
    import atexit
    atexit.register(release_lock)

    root = tk.Tk()              # create the main Tk window
    app = MainForm(root)        # pass root to the constructor

    root.mainloop()

if __name__ == "__main__":
    main()
