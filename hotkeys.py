import threading


def start_hotkeys(callback):
    def run():
        from pynput import keyboard

        with keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+t': callback
        }) as h:
            h.join()

    threading.Thread(target=run, daemon=True).start()