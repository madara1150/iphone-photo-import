"""Pure logic: media items, filtering, file naming, import history and HEIC -> JPG.

Nothing here talks to a device or to Qt, so it is easy to test.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

PHOTO_EXT = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".dng", ".gif", ".tif", ".tiff", ".webp"}
VIDEO_EXT = {".mov", ".mp4", ".m4v", ".avi", ".3gp"}
HEIC_EXT = {".heic", ".heif"}

PERIODS = ("today", "week", "month", "all")


def kind_of(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    if ext in PHOTO_EXT:
        return "photo"
    if ext in VIDEO_EXT:
        return "video"
    return "other"


@dataclass
class MediaItem:
    """One file on the phone. `handle` is whatever the device backend needs to fetch it."""
    id: str
    name: str
    size: int
    date: Optional[datetime]
    folder: str = ""
    handle: Any = field(default=None, repr=False, compare=False)
    live_companion: bool = False  # the short .MOV that belongs to a Live Photo

    @property
    def kind(self) -> str:
        return kind_of(self.name)

    @property
    def stem(self) -> str:
        return os.path.splitext(self.name)[0]

    @property
    def is_heic(self) -> bool:
        return os.path.splitext(self.name)[1].lower() in HEIC_EXT

    def key(self) -> str:
        """Stable identity used by the import history."""
        return f"{self.folder}/{self.name}|{self.size}"


def mark_live_companions(items: List[MediaItem]) -> List[MediaItem]:
    """Flag the .MOV half of Live Photos (same folder + same name as a photo)."""
    photos = {(i.folder, i.stem.upper()) for i in items if i.kind == "photo"}
    for i in items:
        i.live_companion = i.kind == "video" and (i.folder, i.stem.upper()) in photos
    return items


def period_start(period: str, now: Optional[datetime] = None) -> Optional[datetime]:
    now = now or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return today
    if period == "week":
        return today - timedelta(days=6)
    if period == "month":
        return today - timedelta(days=29)
    return None


def filter_items(items: Iterable[MediaItem], period: str = "all", include_videos: bool = False,
                 hide_imported: bool = False, history: Optional["ImportHistory"] = None,
                 now: Optional[datetime] = None) -> List[MediaItem]:
    """Items to show, newest first."""
    start = period_start(period, now)
    out = []
    for i in items:
        if i.kind == "other":
            continue
        if i.kind == "video" and (not include_videos or i.live_companion):
            continue
        if start is not None and (i.date is None or i.date < start):
            continue
        if hide_imported and history is not None and history.contains(i):
            continue
        out.append(i)
    out.sort(key=lambda i: (i.date or datetime.min, i.name), reverse=True)
    return out


def output_name(item: MediaItem, convert_heic: bool) -> str:
    if convert_heic and item.is_heic:
        return item.stem + ".JPG"
    return item.name


def dest_dir(item: MediaItem, root: str, by_date: bool) -> str:
    if by_date and item.date is not None:
        return os.path.join(root, item.date.strftime("%Y-%m-%d"))
    return root


def unique_path(path: str) -> str:
    """Never overwrite: IMG_0001.JPG -> IMG_0001 (2).JPG -> IMG_0001 (3).JPG ..."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    m = re.match(r"^(.*) \((\d+)\)$", base)
    if m:
        base, n = m.group(1), int(m.group(2)) + 1
    else:
        n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def default_destination() -> str:
    pictures = os.path.join(os.path.expanduser("~"), "Pictures")
    return os.path.join(pictures, "iPhone Import")


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


# --------------------------------------------------------------------------- history

class ImportHistory:
    """Remembers which files were already copied from each phone, so 'new only' works
    even after the user moves the photos somewhere else."""

    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, Dict[str, str]] = {}
        self.device = ""
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self._data = {k: dict(v) for k, v in raw.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            pass

    def use_device(self, device_id: str):
        self.device = device_id or "unknown"

    def contains(self, item: MediaItem) -> bool:
        return item.key() in self._data.get(self.device, {})

    def add(self, item: MediaItem, saved_to: str):
        self._data.setdefault(self.device, {})[item.key()] = saved_to

    def count(self) -> int:
        return len(self._data.get(self.device, {}))

    def clear_device(self):
        self._data.pop(self.device, None)
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)
        os.replace(tmp, self.path)


# --------------------------------------------------------------------------- HEIC

_heif_ready = False


def _register_heif():
    global _heif_ready
    if not _heif_ready:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        _heif_ready = True


def convert_to_jpg(src: str, dst: str, quality: int = 92) -> str:
    """Convert a HEIC/HEIF file to JPG, keeping EXIF (date, GPS) and the colour profile.
    The pixels are rotated upright so every program shows them the right way round."""
    from PIL import Image, ImageOps
    _register_heif()
    with Image.open(src) as im:
        exif = im.getexif()
        icc = im.info.get("icc_profile")
        img = ImageOps.exif_transpose(im)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        if exif:
            exif[0x0112] = 1  # orientation: already applied
        kwargs: Dict[str, Any] = {"quality": quality, "subsampling": 0}
        if exif:
            kwargs["exif"] = exif.tobytes()
        if icc:
            kwargs["icc_profile"] = icc
        tmp = dst + ".part"
        img.save(tmp, "JPEG", **kwargs)
    os.replace(tmp, dst)
    return dst


def thumbnail_from_file(path: str, size: int = 240):
    """PIL thumbnail of a local photo (used by the folder backend and tests)."""
    from PIL import Image, ImageOps
    _register_heif()
    with Image.open(path) as im:
        im.draft("RGB", (size * 2, size * 2))
        img = ImageOps.exif_transpose(im)
        img.thumbnail((size, size))
        return img.convert("RGB")
