"""A pretend phone backed by a local folder, for tests."""
import os
import shutil
from datetime import datetime

from PIL import Image
from PySide6.QtGui import QImage

from app.devices.base import LOCKED, READY, WAITING, DeviceBackend
from app.engine import MediaItem, mark_live_companions


def make_photos(folder, specs):
    """specs: list of (name, datetime). Writes small real images (HEIC via pillow-heif)."""
    from pillow_heif import register_heif_opener
    register_heif_opener()
    os.makedirs(folder, exist_ok=True)
    paths = []
    for i, (name, _date) in enumerate(specs):
        path = os.path.join(folder, name)
        ext = os.path.splitext(name)[1].lower()
        if ext in (".mov", ".mp4"):
            with open(path, "wb") as f:
                f.write(b"\0" * 2048)
        else:
            img = Image.new("RGB", (64, 48), (40 * i % 255, 120, 200))
            exif = Image.Exif()
            exif[0x0112] = 6  # rotated 90° like a portrait iPhone photo
            img.save(path, "HEIF" if ext in (".heic", ".heif") else "JPEG", exif=exif.tobytes())
        paths.append(path)
    return paths


class FakeBackend(DeviceBackend):
    def __init__(self, folder, specs, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.specs = specs
        self.fail = set()
        self.thumb_requests = []

    def start(self):
        self.set_status(WAITING)

    def plug_in(self, locked=False):
        self.device_changed.emit({"name": "Test iPhone", "id": "SERIAL123"})
        if locked:
            self.set_status(LOCKED)
            return
        items = []
        for name, date in self.specs:
            path = os.path.join(self.folder, name)
            items.append(MediaItem(id=f"100APPLE/{name}", name=name, size=os.path.getsize(path),
                                   date=date, folder="100APPLE", handle=path))
        mark_live_companions(items)
        self.set_status(READY)
        self.items_ready.emit(items)

    def unplug(self):
        self.device_changed.emit(None)
        self.set_status(WAITING)

    def want_thumbnails(self, items):
        self.thumb_requests = list(items)
        for it in items[:3]:
            img = QImage(40, 30, QImage.Format_RGB32)
            img.fill(0x3366CC)
            self.thumbnail_ready.emit(it.id, img)

    def download(self, item, folder, filename, callback):
        if item.name in self.fail:
            self.on_main(lambda: callback(None, "device error"))
            return
        dst = os.path.join(folder, filename)
        assert not os.path.exists(dst), "backend must never overwrite"
        shutil.copy2(item.handle, dst)
        self.on_main(lambda: callback(dst, None))


SPECS_NOW = datetime.now()
