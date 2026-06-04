import configparser
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path


def _open_url_windows(url):
    os.startfile(url)


def _desktop_entry_dirs():
    dirs = []
    home = Path.home()
    dirs.append(home / ".local" / "share" / "applications")

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        dirs.append(Path(xdg_data_home) / "applications")

    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    for base in xdg_data_dirs.split(":"):
        if base:
            dirs.append(Path(base) / "applications")

    return dirs


def _desktop_entry_path(entry_name):
    for directory in _desktop_entry_dirs():
        candidate = directory / entry_name
        if candidate.exists():
            return candidate
    return None


def _linux_default_browser_command():
    browser_id = None

    try:
        result = subprocess.run(
            ["xdg-settings", "get", "default-web-browser"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        browser_id = (result.stdout or "").strip()
    except Exception:
        browser_id = None

    if not browser_id:
        try:
            result = subprocess.run(
                ["gio", "mime", "x-scheme-handler/https"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            output = (result.stdout or "").strip()
            if "=" in output:
                browser_id = output.split("=", 1)[1].strip()
        except Exception:
            browser_id = None

    if not browser_id:
        return None

    desktop_path = _desktop_entry_path(browser_id)
    if desktop_path is None:
        return None

    parser = configparser.ConfigParser(interpolation=None)
    parser.read(desktop_path, encoding="utf-8")
    if not parser.has_section("Desktop Entry"):
        return None

    exec_value = parser.get("Desktop Entry", "Exec", fallback="").strip()
    if not exec_value:
        return None

    exec_value = (
        exec_value
        .replace("%u", "")
        .replace("%U", "")
        .replace("%f", "")
        .replace("%F", "")
        .replace("%i", "")
        .replace("%c", "")
        .replace("%k", "")
    ).strip()
    if not exec_value:
        return None

    return shlex.split(exec_value)


def _open_url_linux(url):
    command = _linux_default_browser_command()
    if command:
        subprocess.Popen(command + [url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    for fallback in ("xdg-open", "gio"):
        if shutil.which(fallback):
            if fallback == "gio":
                subprocess.Popen(
                    ["gio", "open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return

    raise RuntimeError("Could not resolve the default browser on Linux.")


def open_url_in_default_browser(url):
    system = platform.system()
    if system == "Windows":
        _open_url_windows(url)
        return
    if system == "Linux":
        _open_url_linux(url)
        return

    import webbrowser
    webbrowser.open(url)
