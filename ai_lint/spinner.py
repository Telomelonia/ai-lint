"""Loading spinner for long-running operations."""

import itertools
import sys
import threading
import time


class Spinner:
    """Context manager that shows a braille-dot spinner on stderr."""

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Working..."):
        self.message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _spin(self):
        for frame in itertools.cycle(self._FRAMES):
            if self._stop.is_set():
                break
            sys.stderr.write(f"\r{frame} {self.message}")
            sys.stderr.flush()
            time.sleep(0.08)

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stderr.write("\r" + " " * (len(self.message) + 4) + "\r")
        sys.stderr.flush()
