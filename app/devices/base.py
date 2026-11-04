"""Common interface every device backend implements.

All signals are delivered on the Qt main thread. Backends call `self.on_main(fn)` to run
code coming from a device/OS callback thread safely on the main thread.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QImage

from ..engine import MediaItem

# status values
WAITING = "waiting"      # no phone plugged in
LOCKED = "locked"        # phone found, but locked / "Trust this computer?" not answered
LOADING = "loading"      # reading the list of photos
READY = "ready"          # items_ready has been emitted
DENIED = "denied"        # the OS refused access (macOS privacy setting)
NO_DRIVER = "no_driver"  # Windows: Apple device driver missing
UNSUPPORTED = "unsupported"

DownloadCallback = Callable[[Optional[str], Optional[str]], None]  # (saved_path, error)


class DeviceBackend(QObject):
    device_changed = Signal(object)        # dict(name=..., id=...) or None
    status_changed = Signal(str, str)      # status, detail text
    items_ready = Signal(list)             # List[MediaItem]
    thumbnail_ready = Signal(str, QImage)  # item id, image
    progress = Signal(int)                 # catalogue loading percent

    _main = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._main.connect(lambda fn: fn(), Qt.QueuedConnection)
        self.status = WAITING

    def on_main(self, fn: Callable[[], None]):
        self._main.emit(fn)

    def set_status(self, status: str, detail: str = ""):
        self.status = status
        self.status_changed.emit(status, detail)

    # ---- to implement
    def start(self):
        raise NotImplementedError

    def stop(self):
        pass

    def want_thumbnails(self, items: List[MediaItem]):
        """Replace the thumbnail queue with these items (in display order)."""

    def download(self, item: MediaItem, folder: str, filename: str, callback: DownloadCallback):
        """Copy one file into folder/filename (must not overwrite). Calls callback on the main thread."""
        raise NotImplementedError


def create_backend(parent=None) -> DeviceBackend:
    import sys
    if sys.platform == "darwin":
        from .mac import MacBackend
        return MacBackend(parent)
    if sys.platform.startswith("win"):
        from .windows import WindowsBackend
        return WindowsBackend(parent)

    class _Unsupported(DeviceBackend):
        def start(self):
            self.set_status(UNSUPPORTED)

    return _Unsupported(parent)
