"""Copies a list of items from the phone, one at a time, converting HEIC -> JPG on a
background thread while the next file is already downloading."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtCore import QObject, Qt, Signal

from .engine import HEIC_EXT, ImportHistory, MediaItem, convert_to_jpg, dest_dir, unique_path


@dataclass
class ImportOptions:
    root: str
    by_date: bool = True
    convert_heic: bool = True


@dataclass
class ImportResult:
    copied: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    cancelled: bool = False
    folders: List[str] = field(default_factory=list)


class ImportJob(QObject):
    progress = Signal(int, int, str)   # done, total, current file name
    finished = Signal(object)          # ImportResult
    _converted = Signal(object, object, object)  # item, path, error

    def __init__(self, backend, items: List[MediaItem], options: ImportOptions,
                 history: Optional[ImportHistory] = None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.queue = list(items)
        self.total = len(items)
        self.opt = options
        self.history = history
        self.result = ImportResult()
        self.done = 0
        self.pending_conversions = 0
        self.downloading = False
        self.cancelled = False
        self.pool = ThreadPoolExecutor(max_workers=2)
        self._converted.connect(self._on_converted, Qt.QueuedConnection)

    def start(self):
        os.makedirs(self.opt.root, exist_ok=True)
        self.progress.emit(0, self.total, "")
        self._next()

    def cancel(self):
        self.cancelled = True
        self.result.cancelled = True
        self.queue.clear()
        self._maybe_finish()

    # ------------------------------------------------------------------
    def _next(self):
        if self.cancelled or not self.queue:
            self._maybe_finish()
            return
        item = self.queue.pop(0)
        folder = dest_dir(item, self.opt.root, self.opt.by_date)
        os.makedirs(folder, exist_ok=True)
        filename = os.path.basename(unique_path(os.path.join(folder, item.name)))
        self.downloading = True
        self.progress.emit(self.done, self.total, item.name)
        self.backend.download(item, folder, filename, lambda path, err, it=item: self._on_downloaded(it, path, err))

    def _on_downloaded(self, item, path, error):
        self.downloading = False
        if error or not path or not os.path.exists(path):
            self._record(item, None, error or "missing")
        elif self.opt.convert_heic and os.path.splitext(path)[1].lower() in HEIC_EXT:
            self.pending_conversions += 1
            self.pool.submit(self._convert, item, path)
        else:
            self._record(item, path, None)
        self._next()

    def _convert(self, item, src):
        try:
            dst = unique_path(os.path.splitext(src)[0] + ".JPG")
            convert_to_jpg(src, dst)
            os.remove(src)
            self._converted.emit(item, dst, None)
        except Exception as e:  # keep the original if conversion fails
            self._converted.emit(item, src, None if os.path.exists(src) else str(e))

    def _on_converted(self, item, path, error):
        self.pending_conversions -= 1
        self._record(item, path, error)
        self._maybe_finish()

    def _record(self, item, path, error):
        self.done += 1
        if path and not error:
            self.result.copied.append(path)
            folder = os.path.dirname(path)
            if folder not in self.result.folders:
                self.result.folders.append(folder)
            if self.history is not None:
                self.history.add(item, path)
        else:
            self.result.failed.append(item.name)
        self.progress.emit(self.done, self.total, item.name)

    def _maybe_finish(self):
        if self.downloading or self.pending_conversions or (self.queue and not self.cancelled):
            return
        if getattr(self, "_finished", False):
            return
        self._finished = True
        self.pool.shutdown(wait=False)
        if self.history is not None:
            try:
                self.history.save()
            except OSError:
                pass
        self.finished.emit(self.result)
