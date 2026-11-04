"""Windows backend: the iPhone shows up in "This PC" as a portable device (WPD) once
Apple's driver is installed (Apple Devices app or iTunes). We walk it through the Windows
Shell COM API, the same view File Explorer shows, and copy files with Folder.CopyHere.

All COM work happens on one worker thread.
"""
from __future__ import annotations

import os
import shutil
import time
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from ..engine import MediaItem, kind_of, mark_live_companions
from .base import LOADING, LOCKED, NO_DRIVER, READY, WAITING, DeviceBackend

POLL_MS = 2000
COPY_TIMEOUT_S = 15 * 60
# FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOCONFIRMMKDIR | FOF_NOERRORUI
COPY_FLAGS = 4 | 16 | 512 | 1024
STAGING = ".iphone-import-tmp"
DEVICE_WORDS = ("iphone", "ipad", "ipod", "apple")


def _py_datetime(v) -> Optional[datetime]:
    if v is None:
        return None
    try:
        return datetime(v.year, v.month, v.day, v.hour, v.minute, v.second)
    except Exception:
        return None


def _ext_from_type(type_text: str) -> str:
    word = (type_text or "").split(" ")[0].strip(".").lower()
    return "." + word if word and kind_of("x." + word) != "other" else ""


class _Worker(QObject):
    device = Signal(object)
    status = Signal(str, str)
    items = Signal(list)
    downloaded = Signal(int, object, object)  # request id, path, error

    def __init__(self):
        super().__init__()
        self.shell = None
        self.dev_item = None
        self.dev_name = None
        self.dcim = None
        self.handles: Dict[str, object] = {}
        self.timer = None
        self.sent = False

    @Slot()
    def run(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        self.shell = win32com.client.Dispatch("Shell.Application")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(POLL_MS)
        self.poll()

    # ---------------------------------------------------------------- discovery
    def _find_device(self):
        computer = self.shell.NameSpace(17)  # ssfDRIVES = "This PC"
        if computer is None:
            return None
        for it in computer.Items():
            try:
                name = str(it.Name)
                if it.IsFileSystem:
                    continue  # a normal drive letter
            except Exception:
                continue
            if any(w in name.lower() for w in DEVICE_WORDS):
                return it
        return None

    def _find_dcim(self, dev_item):
        try:
            root = dev_item.GetFolder
        except Exception:
            return None
        if root is None:
            return None
        for storage in root.Items():  # "Internal Storage"
            if not storage.IsFolder:
                continue
            if str(storage.Name).upper() == "DCIM":
                return storage.GetFolder
            try:
                for child in storage.GetFolder.Items():
                    if child.IsFolder and str(child.Name).upper() == "DCIM":
                        return child.GetFolder
            except Exception:
                continue
        return None

    @Slot()
    def poll(self):
        try:
            dev = self._find_device()
        except Exception:
            dev = None
        if dev is None:
            if self.dev_item is not None:
                self.dev_item = self.dcim = None
                self.handles.clear()
                self.sent = False
                self.device.emit(None)
                self.status.emit(WAITING, "")
            return
        name = str(dev.Name)
        if self.dev_item is None or name != self.dev_name:
            self.dev_item, self.dev_name, self.sent = dev, name, False
            self.device.emit({"name": name, "id": name})
        if self.sent:
            return
        dcim = self._find_dcim(dev)
        if dcim is None:
            self.status.emit(LOCKED, "")  # locked, or "Trust this computer?" not answered yet
            return
        self.status.emit(LOADING, "")
        self.dcim = dcim
        self._enumerate()

    def _enumerate(self):
        items: List[MediaItem] = []
        self.handles.clear()
        for folder_item in self.dcim.Items():
            if not folder_item.IsFolder:
                continue
            folder_name = str(folder_item.Name)
            folder = folder_item.GetFolder
            for f in folder.Items():
                if f.IsFolder:
                    continue
                name = self._file_name(f)
                date = None
                for prop in ("System.Photo.DateTaken", "System.DateCreated"):
                    try:
                        date = _py_datetime(f.ExtendedProperty(prop))
                    except Exception:
                        date = None
                    if date:
                        break
                date = date or _py_datetime(getattr(f, "ModifyDate", None))
                try:
                    size = int(f.Size)
                except Exception:
                    size = 0
                item_id = f"{folder_name}/{name}"
                self.handles[item_id] = f
                items.append(MediaItem(id=item_id, name=name, size=size, date=date, folder=folder_name))
        mark_live_companions(items)
        self.sent = True
        self.status.emit(READY, "")
        self.items.emit(items)

    @staticmethod
    def _file_name(f) -> str:
        name = ""
        try:
            name = str(f.ExtendedProperty("System.FileName") or "")
        except Exception:
            pass
        name = name or str(f.Name)
        if not os.path.splitext(name)[1]:
            name += _ext_from_type(str(getattr(f, "Type", "")))
        return name

    # ---------------------------------------------------------------- copy
    @Slot(int, str, str, str)
    def download(self, req, item_id, folder, filename):
        f = self.handles.get(item_id)
        if f is None:
            self.downloaded.emit(req, None, "not found")
            return
        stage = os.path.join(folder, STAGING)
        try:
            os.makedirs(stage, exist_ok=True)
            for old in os.listdir(stage):
                os.remove(os.path.join(stage, old))
            self.shell.NameSpace(os.path.abspath(stage)).CopyHere(f, COPY_FLAGS)
            got = self._wait_for_file(stage)
            if got is None:
                raise RuntimeError("timeout")
            # The phone may hand over a JPG instead of HEIC ("Transfer to Mac or PC: Automatic")
            ext = os.path.splitext(got)[1] or os.path.splitext(filename)[1]
            final = os.path.join(folder, os.path.splitext(filename)[0] + ext)
            from ..engine import unique_path
            final = unique_path(final)
            shutil.move(os.path.join(stage, got), final)
            self.downloaded.emit(req, final, None)
        except Exception as e:
            self.downloaded.emit(req, None, str(e))
        finally:
            try:
                os.rmdir(stage)
            except OSError:
                pass

    @staticmethod
    def _wait_for_file(stage) -> Optional[str]:
        deadline = time.time() + COPY_TIMEOUT_S
        last, stable = -1, 0
        while time.time() < deadline:
            names = [n for n in os.listdir(stage) if not n.startswith("~")]
            if names:
                path = os.path.join(stage, names[0])
                try:
                    size = os.path.getsize(path)
                    with open(path, "ab"):
                        pass  # fails while Explorer still writes it
                    ok = True
                except OSError:
                    ok, size = False, -1
                if ok and size > 0 and size == last:
                    stable += 1
                    if stable >= 2:
                        return names[0]
                else:
                    stable = 0
                last = size
            time.sleep(0.25)
        return None


class WindowsBackend(DeviceBackend):
    _req = Signal(int, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.worker = _Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.device.connect(self.device_changed)
        self.worker.status.connect(self.set_status)
        self.worker.items.connect(self.items_ready)
        self.worker.downloaded.connect(self._on_downloaded)
        self._req.connect(self.worker.download)
        self._callbacks: Dict[int, object] = {}
        self._next = 0

    def start(self):
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            self.set_status(NO_DRIVER, "pywin32 missing")
            return
        self.set_status(WAITING)
        self.thread.start()

    def stop(self):
        self.thread.quit()
        self.thread.wait(2000)

    def download(self, item, folder, filename, callback):
        self._next += 1
        self._callbacks[self._next] = callback
        self._req.emit(self._next, item.id, folder, filename)

    def _on_downloaded(self, req, path, error):
        cb = self._callbacks.pop(req, None)
        if cb:
            cb(path, error)
