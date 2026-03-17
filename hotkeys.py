from pynput import keyboard
import threading

def start_hotkeys(callback):
    def run():
        with keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+t': callback
        }) as h:
            h.join()

    threading.Thread(target=run, daemon=True).start()