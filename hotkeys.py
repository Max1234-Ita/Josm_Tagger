import threading
import time
import sys
import re

# Conditional import for pynput and keyboard
pynput_keyboard = None
try:
    if sys.platform.startswith("linux"):
        from pynput import keyboard as pynput_keyboard
except ImportError:
    pass

keyboard_lib = None
try:
    if sys.platform.startswith("win") or sys.platform.startswith("linux"):
        import keyboard as keyboard_lib
except ImportError:
    pass


def linux_global_hotkeys_available():
    return pynput_keyboard is not None


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
        elif len(part) == 1: # Single character keys (e.g., 'a', 'b', '1')
            converted.append(part)
        else:
            # For other keys not in aliases and not single character,
            # pynput might expect the key name enclosed in <>
            converted.append(f"<{part}>") # Default to <key> format

    return "+".join(converted)


def _normalize_hotkey_for_keyboard(hotkey_str):
    # The 'keyboard' library is more flexible, often just needs the raw string
    # but we can apply some normalization for consistency.
    parts = _split_hotkey_parts(hotkey_str)
    converted = []

    for part in parts:
        if part in MODIFIER_ALIASES:
            converted.append(MODIFIER_ALIASES[part])
        elif part in ZERO_ALIASES:
            # keyboard canonicalizes numpad 0 to plain '0', which is fine here:
            # user wants the hotkey to work with either top-row 0 or numpad 0.
            converted.append("0")
        elif part in PYNPUT_SPECIAL_KEYS: # Use same special keys, but without <>
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

    # Support common config aliases regardless of spacing/casing.
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

    # Preserve order while removing duplicates.
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
        # pynput distinguishes between top-row 0, numpad 0, and sometimes Insert.
        zero_replacements = ["0", "num 0", "insert"]
        for replacement in zero_replacements:
            replaced = list(parts)
            for idx in zero_indices:
                replaced[idx] = replacement
            variants.append(_normalize_hotkey_for_pynput("+".join(replaced)))

    # Preserve order while removing duplicates.
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
            else:
                print("Error: 'keyboard' library not available. Hotkeys disabled on Windows.")
                return False
        
        elif sys.platform.startswith("linux"):
            if pynput_keyboard:
                supported_hotkeys = {}
                for spec in _build_pynput_hotkey_variants(hotkey_str):
                    try:
                        # Test if pynput can parse the hotkey string.
                        pynput_keyboard.HotKey.parse(spec)
                        supported_hotkeys[spec] = callback
                    except Exception as e:
                        print(f"Debug: pynput does not support hotkey spec '{spec}': {e}")

                if supported_hotkeys:
                    print(f"Hotkey backend (Linux): 'pynput' registered: {', '.join(supported_hotkeys.keys())}")
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
            else:
                print("Info: no global hotkey backend available on Linux; local Tk fallback required.")
                return False
        else:
            print(f"Warning: Hotkeys are not supported on platform '{sys.platform}'.")
            return False

    threading.Thread(target=run_hotkey_listener, daemon=True).start()
    return True
