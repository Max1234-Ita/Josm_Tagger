import re
import sys
import threading

keyboard_lib = None
try:
    if sys.platform.startswith("win"):
        import keyboard as keyboard_lib
except ImportError:
    pass


MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "cmd": "cmd",
    "win": "cmd",
    "super": "cmd",
}

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


def _split_hotkey_parts(hotkey_str):
    return [part.strip().lower() for part in re.split(r"\s*[+-]\s*", hotkey_str) if part.strip()]


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

    if "num_0" in normalized_hotkey:
        variants.extend([
            normalized_hotkey.replace("num_0", "0"),
            normalized_hotkey.replace("num_0", "insert"),
        ])

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


def start_hotkeys(callback, hotkey_str="alt+0"):
    print(f"Attempting to register hotkey: '{hotkey_str}' on platform: {sys.platform}")

    def run_hotkey_listener():
        if sys.platform.startswith("win"):
            if keyboard_lib:
                hotkey_variants = _build_keyboard_hotkey_variants(hotkey_str)

                registered = False
                for variant in hotkey_variants:
                    try:
                        keyboard_lib.add_hotkey(variant, callback)
                        print(f"Hotkey backend (Windows): 'keyboard' registered: '{variant}'")
                        registered = True
                        break
                    except Exception as e:
                        print(f"Debug: 'keyboard' failed to register variant '{variant}': {e}")

                if not registered:
                    print(f"Error: 'keyboard' could not register hotkey '{hotkey_str}' on Windows. Hotkeys disabled.")
                    return False

                keyboard_lib.wait()
                return True

            print("Error: 'keyboard' library not available. Hotkeys disabled on Windows.")
            return False

        print(f"Warning: Hotkeys are not supported on platform '{sys.platform}'.")
        return False

    threading.Thread(target=run_hotkey_listener, daemon=True).start()
    return True
