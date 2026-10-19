"""Prevent two application instances from recovering/processing the same queue."""
from pathlib import Path
import os

from .errors import ExtractionError


class InstanceLock:
    def __init__(self, database):
        path = Path(str(Path(database).resolve()) + ".lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("a+b")
        if path.stat().st_size == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise ExtractionError("This database is already open in another app instance. Stop it or choose a separate --database path.") from None

    def close(self):
        self.handle.close()  # OS locks are released on close, including process crashes.
