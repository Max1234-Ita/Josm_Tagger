import argparse
import os
import socket
import threading
from pathlib import Path


INSTANCE_SOCKET_PATH = Path.home() / ".josm_tagger_socket"


def request_restore(timeout=0.25):
    """
    Ask the running Linux instance to restore/focus itself.
    Returns True if a running instance accepted the request.
    """
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(INSTANCE_SOCKET_PATH))
        sock.sendall(b"RESTORE\n")
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        sock.close()
        return True
    except OSError:
        return False


class LinuxInstanceServer:
    def __init__(self, on_restore, socket_path=INSTANCE_SOCKET_PATH):
        self.on_restore = on_restore
        self.socket_path = Path(socket_path)
        self._sock = None
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        self.stop()
        try:
            self.socket_path.unlink(missing_ok=True)
        except OSError:
            pass

        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(self.socket_path))
        self._sock.listen(1)
        self._sock.settimeout(0.5)

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def _serve(self):
        while not self._stop_event.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                data = conn.recv(64).decode("utf-8", "ignore").strip().upper()
                if data in {"RESTORE", "FOCUS", "SHOW"}:
                    self.on_restore()
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def stop(self):
        self._stop_event.set()

        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._stop_event.clear()

        try:
            self.socket_path.unlink(missing_ok=True)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--restore", action="store_true")
    args, _ = parser.parse_known_args()

    if args.restore:
        raise SystemExit(0 if request_restore() else 1)


if __name__ == "__main__":
    main()
