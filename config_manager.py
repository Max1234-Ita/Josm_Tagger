import json
import os

CONFIG_FILE = "config.json"


# =========================
# BASE CONFIG I/O
# =========================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_debug_mode(cfg=None):
    if isinstance(cfg, bool):
        return cfg
    if isinstance(cfg, dict):
        config = cfg
    else:
        config = load_config()

    return bool(config.get("debug_mode", False))


def debug_print(*args, cfg=None, **kwargs):
    if is_debug_mode(cfg):
        print(*args, **kwargs)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# =========================
# GEOMETRY SAVE / LOAD
# =========================

def save_geometry(key, window):
    cfg = load_config()

    geom = window.geometry()
    # format: "WxH+X+Y"
    size, pos = geom.split("+", 1)
    w, h = map(int, size.split("x"))
    x, y = map(int, pos.split("+"))

    if "geometry" not in cfg:
        cfg["geometry"] = {}

    cfg["geometry"][key] = {
        "x": x,
        "y": y,
        "w": w,
        "h": h,
    }

    save_config(cfg)


def load_geometry(key):
    cfg = load_config()

    try:
        g = cfg["geometry"][key]
        return g["x"], g["y"], g["w"], g["h"]
    except Exception:
        return None


# =========================
# SCREEN DETECTION
# =========================

def _get_monitors():
    """
    Returns list of monitors.
    Try screeninfo, fallback to primary monitor.
    """
    try:
        from screeninfo import get_monitors
        return get_monitors()
    except Exception:
        return None


def _is_visible_on_any_monitor(x, y, w, h, root):
    monitors = _get_monitors()

    if monitors:
        for m in monitors:
            if (
                x + w > m.x and
                x < m.x + m.width and
                y + h > m.y and
                y < m.y + m.height
            ):
                return True
        return False

    # fallback: only primary monitor
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    return not (x > sw or y > sh or x + w < 0 or y + h < 0)


def _center_on_primary(root, w, h):
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    x = (sw - w) // 2
    y = (sh - h) // 2

    return x, y


def _adjust_if_offscreen(root, x, y, w, h):
    if _is_visible_on_any_monitor(x, y, w, h, root):
        return x, y

    return _center_on_primary(root, w, h)


# =========================
# PUBLIC API
# =========================

def apply_geometry(window, key, default_size=(800, 600)):
    """
    Apply saved geometry:
    - if exists → use it
    - if off screen → correct it
    - if not exists → center with default_size
    """

    data = load_geometry(key)

    if data:
        x, y, w, h = data
        x, y = _adjust_if_offscreen(window, x, y, w, h)
    else:
        w, h = default_size
        x, y = _center_on_primary(window, w, h)

    window.geometry(f"{w}x{h}+{x}+{y}")


def bind_auto_save_geometry(window, key):
    """
    Automatically save geometry on close.
    """

    def _on_close():
        try:
            save_geometry(key, window)
        finally:
            window.destroy()

    window.protocol("WM_DELETE_WINDOW", _on_close)
