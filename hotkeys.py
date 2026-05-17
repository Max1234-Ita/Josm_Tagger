import threading
import time


MODIFIER_ALIASES = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "cmd": "<cmd>",
    "win": "<cmd>",
    "super": "<cmd>",
}

SPECIAL_KEY_ALIASES = {
    "num 0": "<num_0>",
    "num0": "<num_0>",
    "numpad 0": "<num_0>",
    "numpad0": "<num_0>",
    "insert": "<insert>",
    "ins": "<insert>",
    "enter": "<enter>",
    "return": "<enter>",
    "space": "<space>",
    "tab": "<tab>",
    "esc": "<esc>",
    "escape": "<esc>",
}


def hotkey_to_pynput_specs(hotkey):
    parts = [part.strip().lower() for part in hotkey.split("+") if part.strip()]
    converted = []

    for part in parts:
        if part in MODIFIER_ALIASES:
            converted.append(MODIFIER_ALIASES[part])
        elif part in SPECIAL_KEY_ALIASES:
            converted.append(SPECIAL_KEY_ALIASES[part])
        elif len(part) == 1:
            converted.append(part)
        elif part.startswith("<") and part.endswith(">"):
            converted.append(part)
        else:
            converted.append(f"<{part.replace(' ', '_')}>")

    primary = "+".join(converted)
    specs = [primary]

    # Linux may expose numpad 0 either as num_0, plain 0, or Insert,
    # depending on Num Lock and the active desktop/session.
    if "<num_0>" in primary:
        specs.append(primary.replace("<num_0>", "0"))
        specs.append(primary.replace("<num_0>", "<insert>"))

    return list(dict.fromkeys(specs))


def hotkey_to_keyboard_specs(hotkey):
    normalized = " + ".join(part.strip().lower() for part in hotkey.split("+") if part.strip())
    specs = [normalized]

    for numpad_name in ("num 0", "num0", "numpad 0", "numpad0"):
        if numpad_name in normalized:
            specs.append(normalized.replace(numpad_name, "0"))
            specs.append(normalized.replace(numpad_name, "insert"))

    return list(dict.fromkeys(specs))


def start_hotkeys(callback, hotkey="ctrl+alt+t"):
    def run():
        if _run_pynput_hotkeys(callback, hotkey):
            return
        _run_keyboard_hotkey(callback, hotkey)

    threading.Thread(target=run, daemon=True).start()


def _run_pynput_hotkeys(callback, hotkey):
    try:
        from pynput import keyboard

        hotkeys = {
            spec: callback
            for spec in hotkey_to_pynput_specs(hotkey)
            if is_pynput_hotkey_supported(keyboard, spec)
        }
        if not hotkeys:
            print(f"Warning: No supported hotkey variant found for: {hotkey}")
            return False
        print(f"Hotkey backend: pynput ({', '.join(hotkeys.keys())})")
        with keyboard.GlobalHotKeys(hotkeys) as h:
            h.join()
        return True
    except Exception as e:
        print(f"Warning: pynput hotkey backend failed: {e}")
        return False


def _run_keyboard_hotkey(callback, hotkey):
    try:
        import keyboard

        registered = []
        for spec in hotkey_to_keyboard_specs(hotkey):
            try:
                keyboard.add_hotkey(spec, callback)
                registered.append(spec)
            except Exception as e:
                print(f"Warning: Unsupported keyboard hotkey variant skipped: {spec} ({e})")

        if not registered:
            print(f"Warning: No supported keyboard hotkey variant found for: {hotkey}")
            return

        print(f"Hotkey backend: keyboard ({', '.join(registered)})")
        while True:
            time.sleep(3600)
    except Exception as e:
        print(f"Warning: keyboard hotkey backend failed: {e}")
        print("Hotkeys will be disabled in this session.")


def is_pynput_hotkey_supported(pynput_keyboard, spec):
    try:
        pynput_keyboard.HotKey.parse(spec)
        return True
    except Exception as e:
        print(f"Warning: Unsupported hotkey variant skipped: {spec} ({e})")
        return False
