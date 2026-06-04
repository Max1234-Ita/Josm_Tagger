import re
import sys
import threading

# Conditional import for Linux hotkey backends.
pynput_keyboard = None
try:
    if sys.platform.startswith("linux"):
        from pynput import keyboard as pynput_keyboard
except ImportError:
    pass

keyboard_lib = None
try:
    if sys.platform.startswith("linux"):
        import keyboard as keyboard_lib
except ImportError:
    pass


def linux_global_hotkeys_available():
    return pynput_keyboard is not None or keyboard_lib is not None


def linux_global_hotkeys_status():
    if pynput_keyboard is not None and keyboard_lib is not None:
        return "available (pynput + keyboard)"
    if pynput_keyboard is not None:
        return "available (pynput)"
    if keyboard_lib is not None:
        return "available (keyboard)"
    return "missing"


MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "cmd": "cmd",
    "win": "cmd",
    "super": "cmd",
}

# Keys that pynput typically expects in '<key>' format
PYNPUT_SPECIAL_KEYS = {
    "num 0": "num_0", "num0": "num_0", "numpad 0": "num_0", "numpad0": "num_0",
    "insert": "insert", "ins": "insert",
    "enter": "enter", "return": "enter",
    "space": "space",
    "tab": "tab",
    "esc": "esc", "escape": "esc",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5",
    "f6": "f6", "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10",
    "f11": "f11", "f12": "f12",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "page_up": "page_up", "page_down": "page_down",
    "delete": "delete", "del": "delete", "backspace": "backspace",
    "print_screen": "print_screen", "scroll_lock": "scroll_lock", "pause": "pause",
    "caps_lock": "caps_lock", "num_lock": "num_lock",
}

ZERO_ALIASES = {
    "0",
    "num 0",
    "num0",
    "num_0",
    "numpad 0",
    "numpad0",
    "numpad_0",
    "insert",
    "ins",
}

ZERO_VARIANTS = ("0", "num 0", "num0", "numpad 0", "numpad0", "insert")


def _split_hotkey_parts(hotkey_str):
    return [part.strip().lower() for part in re.split(r"\s*[+-]\s*", hotkey_str) if part.strip()]


def _normalize_hotkey_for_pynput(hotkey_str):
    parts = _split_hotkey_parts(hotkey_str)
    converted = []

    for part in parts:
        if part in MODIFIER_ALIASES:
            converted.append(f"<{MODIFIER_ALIASES[part]}>")
        elif part in PYNPUT_SPECIAL_KEYS:
            converted.append(f"<{PYNPUT_SPECIAL_KEYS[part]}>")
        elif len(part) == 1:
            converted.append(part)
        else:
            converted.append(f"<{part}>")

    return "+".join(converted)


def _normalize_hotkey_for_keyboard(hotkey_str):
    parts = _split_hotkey_parts(hotkey_str)
    converted = []

    for part in parts:
        if part in MODIFIER_ALIASES:
            converted.append(MODIFIER_ALIASES[part])
        elif part in ZERO_ALIASES:
            converted.append("0")
        elif part in PYNPUT_SPECIAL_KEYS:
            converted.append(PYNPUT_SPECIAL_KEYS[part])
        else:
            converted.append(part)

    return "+".join(converted)


def _build_keyboard_hotkey_variants(hotkey_str):
    normalized_hotkey = _normalize_hotkey_for_keyboard(hotkey_str)
    variants = [normalized_hotkey]

    parts = _split_hotkey_parts(hotkey_str)
    zero_indices = [idx for idx, part in enumerate(parts) if part in ZERO_ALIASES]
    if zero_indices:
        for replacement in ZERO_VARIANTS:
            replaced = list(parts)
            for idx in zero_indices:
                replaced[idx] = replacement
            variants.append("+".join(replaced))

    raw_variants = {
        hotkey_str.strip().lower(),
        hotkey_str.strip().lower().replace("-", "+"),
        hotkey_str.strip().lower().replace("num 0", "num0"),
        hotkey_str.strip().lower().replace("num 0", "numpad 0"),
        hotkey_str.strip().lower().replace("num 0", "numpad0"),
    }
    for variant in raw_variants:
        if variant:
            variants.append(_normalize_hotkey_for_keyboard(variant))

    unique_variants = []
    seen = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        unique_variants.append(variant)

    return unique_variants


def _build_pynput_hotkey_variants(hotkey_str):
    parts = _split_hotkey_parts(hotkey_str)
    zero_indices = [idx for idx, part in enumerate(parts) if part in ZERO_ALIASES]

    variants = [_normalize_hotkey_for_pynput(hotkey_str)]

    if zero_indices:
        zero_replacements = ["0", "num 0", "insert"]
        for replacement in zero_replacements:
            replaced = list(parts)
            for idx in zero_indices:
                replaced[idx] = replacement
            variants.append(_normalize_hotkey_for_pynput("+".join(replaced)))

    unique_variants = []
    seen = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        unique_variants.append(variant)

    return unique_variants


def start_hotkeys(callback, hotkey_str="ctrl+0"):
    print(f"Attempting to register Linux hotkey: '{hotkey_str}' on platform: {sys.platform}")

    def run_hotkey_listener():
        if pynput_keyboard:
            supported_hotkeys = {}
            for spec in _build_pynput_hotkey_variants(hotkey_str):
                try:
                    pynput_keyboard.HotKey.parse(spec)
                    supported_hotkeys[spec] = callback
                except Exception as e:
                    print(f"Debug: pynput does not support hotkey spec '{spec}': {e}")

            if supported_hotkeys:
                print(
                    "Hotkey backend (Linux): 'pynput' registered: "
                    f"{', '.join(supported_hotkeys.keys())}"
                )
                with pynput_keyboard.GlobalHotKeys(supported_hotkeys) as h:
                    h.join()
                return True

            print(
                f"Warning: 'pynput' could not register hotkey '{hotkey_str}' on Linux. "
                "Trying keyboard fallback."
            )

        if keyboard_lib:
            registered = False
            for variant in _build_keyboard_hotkey_variants(hotkey_str):
                try:
                    keyboard_lib.add_hotkey(variant, callback)
                    print(f"Hotkey backend (Linux fallback): 'keyboard' registered: '{variant}'")
                    registered = True
                    break
                except Exception as e:
                    print(f"Debug: 'keyboard' failed to register variant '{variant}': {e}")

            if not registered:
                print(
                    f"Error: neither 'pynput' nor 'keyboard' could register hotkey '{hotkey_str}' on Linux. "
                    "Hotkeys disabled."
                )
                return False

            keyboard_lib.wait()
            return True

        print("Info: no global hotkey backend available on Linux; local Tk fallback required.")
        return False

    threading.Thread(target=run_hotkey_listener, daemon=True).start()
    return True


def linux_hotkey_matches(event=None, spec="ctrl+0"):
    parts = [part.strip().lower() for part in re.split(r"\s*[+-]\s*", spec) if part.strip()]
    if not parts or event is None:
        return False

    keysym = str(getattr(event, "keysym", "") or "").lower()
    keycode = int(getattr(event, "keycode", -1))
    state = int(getattr(event, "state", 0))

    alt_mask = 0x0008
    shift_mask = 0x0001
    ctrl_mask = 0x0004

    wants_alt = any(p in ("alt", "menu", "mod1") for p in parts)
    wants_ctrl = any(p in ("ctrl", "control") for p in parts)
    wants_shift = any(p == "shift" for p in parts)

    if wants_alt and not (state & alt_mask):
        return False
    if wants_ctrl and not (state & ctrl_mask):
        return False
    if wants_shift and not (state & shift_mask):
        return False

    key_tokens = [p for p in parts if p not in ("alt", "menu", "mod1", "ctrl", "control", "shift")]
    if not key_tokens:
        return False

    key = key_tokens[-1]
    zero_keys = {"0", "num 0", "num0", "num_0", "numpad 0", "numpad0", "numpad_0"}
    if key in zero_keys:
        return keysym in {"0", "kp_0", "insert"} or keycode in (19, 10, 90)

    return keysym == key.replace(" ", "_")
