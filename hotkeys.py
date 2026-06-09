import threading
import time
import sys
import re


MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "control",
    "alt": "alt",
    "shift": "shift",
    "cmd": "cmd",
    "win": "win",
    "super": "super",
}

# Keys that pynput typically expects in '<key>' format
PYNPUT_SPECIAL_KEYS = {
    "num 0": "num_0", "num0": "num_0", "numpad 0": "num_0", "numpad0": "num_0",
    "insert": "insert", "ins": "insert",
    "enter": "enter", "return": "return",
    "space": "space",
    "tab": "tab",
    "esc": "esc", "escape": "escape",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5",
    "f6": "f6", "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10",
    "f11": "f11", "f12": "f12",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "page_up": "page_up", "page_down": "page_down",
    "delete": "delete", "del": "delete", "backspace": "backspace",
    "print_screen": "print_screen", "scroll_lock": "scroll_lock", "pause": "pause",
    "caps_lock": "caps_lock", "num_lock": "num_lock",
}

# Aliases for '0' key, including numpad and insert, for robust parsing
ZERO_ALIASES = {
    "0", "num 0", "num0", "numpad 0", "numpad0", "insert", "ins",
}


def _split_hotkey_parts(hotkey_str):
    # Split by '+' or '-' with optional spaces around them
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
        elif part in PYNPUT_SPECIAL_KEYS: # Use same special keys, but without <>
            converted.append(PYNPUT_SPECIAL_KEYS[part])
        else:
            converted.append(part)
            
    return "+".join(converted)


def _build_keyboard_hotkey_variants(hotkey_str):
    normalized_hotkey = _normalize_hotkey_for_keyboard(hotkey_str)
    variants = [normalized_hotkey]

    # Add variants for numpad '0' vs 'insert' for robustness
    if "num_0" in normalized_hotkey:
        variants.extend([
            normalized_hotkey.replace("num_0", "0"),
            normalized_hotkey.replace("num_0", "insert"),
        ])

    # Support common config aliases regardless of spacing/casing.
    # This part is more for parsing user input, less for keyboard library itself
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
        # We generate variants to cover common user expectations.
        zero_replacements = ["0", "num_0", "insert"] # pynput expects '0' for top-row, '<num_0>' for numpad, '<insert>' for insert
        for replacement in zero_replacements:
            replaced_parts = list(parts)
            for idx in zero_indices:
                replaced_parts[idx] = replacement
            variants.append(_normalize_hotkey_for_pynput("+".join(replaced_parts)))

    # Preserve order while removing duplicates.
    unique_variants = []
    seen = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        unique_variants.append(variant)

    return unique_variants


def start_hotkeys(callback, hotkey_str="ctrl+0"):
    print(f"Attempting to register hotkey: '{hotkey_str}' on platform: {sys.platform}")

    def run_hotkey_listener():
        if sys.platform.startswith("win"):
            try:
                import keyboard
                hotkey_variants = _build_keyboard_hotkey_variants(hotkey_str)
                
                registered = False
                for variant in hotkey_variants:
                    try:
                        keyboard.add_hotkey(variant, callback)
                        print(f"Hotkey backend (Windows): 'keyboard' registered: '{variant}'")
                        registered = True
                        break
                    except Exception as e:
                        print(f"Debug: 'keyboard' failed to register variant '{variant}': {e}")
                
                if not registered:
                    print(f"Error: 'keyboard' could not register hotkey '{hotkey_str}' on Windows. Hotkeys disabled.")
                    return

                keyboard.wait()
            except ImportError:
                print("Error: 'keyboard' library not found. Hotkeys disabled on Windows.")
            except Exception as e:
                print(f"Error: Hotkey registration failed on Windows using 'keyboard': {e}")
        
        elif sys.platform.startswith("linux"):
            try:
                from pynput import keyboard
                
                supported_hotkeys = {}
                for spec in _build_pynput_hotkey_variants(hotkey_str):
                    try:
                        # Test if pynput can parse the hotkey string.
                        keyboard.HotKey.parse(spec)
                        supported_hotkeys[spec] = callback
                    except Exception as e:
                        print(f"Debug: pynput does not support hotkey spec '{spec}': {e}")

                if not supported_hotkeys:
                    print(f"Error: 'pynput' could not register any variant of hotkey '{hotkey_str}' on Linux. Hotkeys disabled.")
                    print("Possible reasons: 'pynput' not installed, Wayland environment, or unsupported hotkey combination.")
                    return

                print(f"Hotkey backend (Linux): 'pynput' registered: {', '.join(supported_hotkeys.keys())}")
                with keyboard.GlobalHotKeys(supported_hotkeys) as h:
                    h.join()

            except ImportError:
                print("Error: 'pynput' library not found. Hotkeys disabled on Linux.")
            except Exception as e:
                print(f"Error: Hotkey registration failed on Linux using 'pynput': {e}")
        else:
            print(f"Warning: Hotkeys are not supported on platform '{sys.platform}'.")

    threading.Thread(target=run_hotkey_listener, daemon=True).start()