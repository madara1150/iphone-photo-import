"""macOS backend: Apple's ImageCaptureCore (the same framework the Image Capture app uses).

It talks to the iPhone directly over USB, so no extra software is needed.
"""
from __future__ import annotations

import io
import os
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import objc
from Foundation import NSObject, NSURL
import ImageCaptureCore as ICC
from PySide6.QtGui import QImage

from ..engine import MediaItem, mark_live_companions
from .base import DENIED, LOADING, LOCKED, READY, WAITING, DeviceBackend

THUMB_PX = 320
MAX_THUMB_REQUESTS = 4


def _to_datetime(nsdate) -> Optional[datetime]:
    if nsdate is None:
        return None
    try:
        return datetime.fromtimestamp(nsdate.timeIntervalSince1970())
    except (OverflowError, OSError, ValueError):
        return None


def _qimage_from_bytes(data: bytes) -> QImage:
    img = QImage.fromData(data)
    if not img.isNull():
        return img
    try:  # HEIC thumbnail data: decode with Pillow
        from PIL import Image
        from ..engine import _register_heif
        _register_heif()
        with Image.open(io.BytesIO(data)) as im:
            rgb = im.convert("RGB")
            raw = rgb.tobytes("raw", "RGB")
            return QImage(raw, rgb.width, rgb.height, rgb.width * 3, QImage.Format_RGB888).copy()
    except Exception:
        return QImage()


def _protocols(*names):
    out = []
    for n in names:
        try:
            out.append(objc.protocolNamed(n))
        except objc.ProtocolError:
            pass
    return out


class _BrowserDelegate(NSObject, protocols=_protocols("ICDeviceBrowserDelegate")):
    def initWithOwner_(self, owner):
        self = objc.super(_BrowserDelegate, self).init()
        if self is not None:
            self.owner = owner
        return self

    def deviceBrowser_didAddDevice_moreComing_(self, browser, device, more):
        self.owner._device_added(device)

    def deviceBrowser_didRemoveDevice_moreGoing_(self, browser, device, more):
        self.owner._device_removed(device)


class _CameraDelegate(NSObject, protocols=_protocols("ICCameraDeviceDelegate")):
    def initWithOwner_(self, owner):
        self = objc.super(_CameraDelegate, self).init()
        if self is not None:
            self.owner = owner
        return self

    # ICDeviceDelegate
    def didRemoveDevice_(self, device):
        self.owner._device_removed(device)

    def device_didOpenSessionWithError_(self, device, error):
        self.owner._session_opened(device, error)

    def device_didCloseSessionWithError_(self, device, error):
        pass

    def device_didEncounterError_(self, device, error):
        pass

    def deviceDidBecomeReady_(self, device):
        pass

    # ICCameraDeviceDelegate
    def cameraDevice_didAddItems_(self, camera, items):
        self.owner._catalog_changed(camera)

    def cameraDevice_didRemoveItems_(self, camera, items):
        self.owner._catalog_changed(camera)

    def cameraDevice_didRenameItems_(self, camera, items):
        pass

    def cameraDevice_didReceiveThumbnail_forItem_error_(self, camera, thumb, item, error):
        pass

    def cameraDevice_didReceiveMetadata_forItem_error_(self, camera, metadata, item, error):
        pass

    def cameraDevice_didReceivePTPEvent_(self, camera, data):
        pass

    def cameraDeviceDidChangeCapability_(self, camera):
        pass

    def deviceDidBecomeReadyWithCompleteContentCatalog_(self, camera):
        self.owner._catalog_ready(camera)

    def cameraDeviceDidEnableAccessRestriction_(self, camera):
        self.owner._restricted(camera)

    def cameraDeviceDidRemoveAccessRestriction_(self, camera):
        self.owner._unrestricted(camera)


class MacBackend(DeviceBackend):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser = None
        self.camera = None
        self._delegate = _BrowserDelegate.alloc().initWithOwner_(self)
        self._cam_delegate = _CameraDelegate.alloc().initWithOwner_(self)
        self._items: Dict[str, MediaItem] = {}
        self._thumb_queue: deque = deque()
        self._thumb_inflight = 0
        self._thumb_done: set = set()
        self._catalog_sent = False

    # ------------------------------------------------------------------ lifecycle
    def start(self):
        self.set_status(WAITING)
        self.browser = ICC.ICDeviceBrowser.alloc().init()
        self.browser.setDelegate_(self._delegate)
        self.browser.setBrowsedDeviceTypeMask_(ICC.ICDeviceTypeMaskCamera | ICC.ICDeviceLocationTypeMaskLocal)
        self._request_authorization()
        self.browser.start()

    def stop(self):
        if self.camera is not None:
            try:
                self.camera.requestCloseSession()
            except Exception:
                pass
        if self.browser is not None:
            self.browser.stop()

    def _request_authorization(self):
        # macOS 10.15+: ask once for access to photos on connected devices.
        req = getattr(self.browser, "requestContentsAuthorizationWithCompletion_", None)
        if req is None:
            return

        def done(status):
            if status == getattr(ICC, "ICAuthorizationStatusDenied", "denied") or \
                    status == getattr(ICC, "ICAuthorizationStatusRestricted", "restricted"):
                self.on_main(lambda: self.set_status(DENIED))
        try:
            req(done)
        except Exception:
            pass

    # ------------------------------------------------------------------ device events
    def _device_added(self, device):
        if self.camera is not None or not device.isKindOfClass_(ICC.ICCameraDevice):
            return
        self.camera = device
        self._items.clear()
        self._thumb_done.clear()
        self._thumb_queue.clear()
        self._catalog_sent = False
        device.setDelegate_(self._cam_delegate)
        self.device_changed.emit({"name": str(device.name() or "iPhone"), "id": self._device_id(device)})
        self.set_status(LOADING)
        device.requestOpenSession()

    def _device_removed(self, device):
        if self.camera is None or device != self.camera:
            return
        self.camera = None
        self._items.clear()
        self._thumb_queue.clear()
        self.device_changed.emit(None)
        self.set_status(WAITING)

    @staticmethod
    def _device_id(device) -> str:
        for attr in ("serialNumberString", "persistentIDString", "UUIDString"):
            try:
                v = getattr(device, attr)()
            except Exception:
                v = None
            if v:
                return str(v)
        return str(device.name())

    def _session_opened(self, device, error):
        if error is not None:
            code = error.code() if hasattr(error, "code") else 0
            self.on_main(lambda: self.set_status(DENIED if code == ICC.ICReturnConnectionNotAuthorizedToOpenDevice
                                                 else LOCKED, str(error.localizedDescription())))
            return
        if self._is_restricted(device):
            self.on_main(lambda: self.set_status(LOCKED))

    @staticmethod
    def _is_restricted(device) -> bool:
        try:
            return bool(device.isAccessRestrictedAppleDevice())
        except Exception:
            return False

    def _restricted(self, camera):
        self.on_main(lambda: self.set_status(LOCKED))

    def _unrestricted(self, camera):
        self.on_main(lambda: self.set_status(LOADING))

    def _catalog_changed(self, camera):
        try:
            pct = int(camera.contentCatalogPercentCompleted())
        except Exception:
            pct = 0
        self.on_main(lambda: self.progress.emit(pct))
        if self._catalog_sent:  # new photo taken while connected
            self.on_main(lambda: self._publish(camera))

    def _catalog_ready(self, camera):
        self.on_main(lambda: self._publish(camera))

    def _publish(self, camera):
        if camera is not self.camera and camera != self.camera:
            return
        items: List[MediaItem] = []
        new_map: Dict[str, MediaItem] = {}
        for f in camera.mediaFiles() or []:
            try:
                name = str(f.name())
                folder = f.parentFolder()
                folder_name = str(folder.name()) if folder is not None else ""
                date = _to_datetime(f.exifCreationDate()) or _to_datetime(f.creationDate()) \
                    or _to_datetime(f.fileCreationDate())
                item_id = f"{folder_name}/{name}"
                item = MediaItem(id=item_id, name=name, size=int(f.fileSize()), date=date,
                                 folder=folder_name, handle=f)
            except Exception:
                continue
            new_map[item_id] = item
            items.append(item)
        mark_live_companions(items)
        self._items = new_map
        self._catalog_sent = True
        self.set_status(READY)
        self.items_ready.emit(items)

    # ------------------------------------------------------------------ thumbnails
    def want_thumbnails(self, items: List[MediaItem]):
        self._thumb_queue = deque(i for i in items if i.id not in self._thumb_done)
        self._pump_thumbs()

    def _pump_thumbs(self):
        while self._thumb_inflight < MAX_THUMB_REQUESTS and self._thumb_queue:
            item = self._thumb_queue.popleft()
            if item.id in self._thumb_done:
                continue
            self._thumb_done.add(item.id)
            self._thumb_inflight += 1
            self._request_thumb(item)

    def _request_thumb(self, item: MediaItem):
        f = item.handle
        opts = {getattr(ICC, "ICImageSourceThumbnailMaxPixelSize", "kCGImageSourceThumbnailMaxPixelSize"): THUMB_PX}

        def done(data, error):
            raw = bytes(data) if data is not None else b""

            def finish():
                self._thumb_inflight -= 1
                self._thumb_done.discard(item.id)  # the UI keeps the cache; allow re-requests
                if raw:
                    img = _qimage_from_bytes(raw)
                    if not img.isNull():
                        self.thumbnail_ready.emit(item.id, img)
                self._pump_thumbs()
            self.on_main(finish)
        try:
            f.requestThumbnailDataWithOptions_completion_(opts, done)
        except Exception:
            self._thumb_inflight -= 1
            self._thumb_done.discard(item.id)

    # ------------------------------------------------------------------ download
    def download(self, item, folder, filename, callback):
        f = item.handle
        os.makedirs(folder, exist_ok=True)
        opts = {
            ICC.ICDownloadsDirectoryURL: NSURL.fileURLWithPath_isDirectory_(folder, True),
            ICC.ICSaveAsFilename: filename,
            ICC.ICOverwrite: False,
        }

        def done(saved_name, error):
            if error is not None:
                msg = str(error.localizedDescription())
                self.on_main(lambda: callback(None, msg))
            else:
                path = os.path.join(folder, str(saved_name or filename))
                self.on_main(lambda: callback(path, None))
        try:
            f.requestDownloadWithOptions_completion_(opts, done)
        except Exception as e:  # pragma: no cover - device went away
            msg = str(e)
            self.on_main(lambda: callback(None, msg))
