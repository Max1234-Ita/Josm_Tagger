import tkinter as tk
import fcntl
import os
import sys
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

def acquire_lock():
    global LOCK_FILE
    try:
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
    except IOError:
        other_pid = _read_pid_file()
        if other_pid == "unknown":
            other_pid = _read_lock_pid()
        if other_pid != "unknown" and not _pid_is_running(other_pid):
            other_pid = f"{other_pid} (not running; stale lock file?)"
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
