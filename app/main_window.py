"""Main window: wait for the phone -> pick photos -> copy -> done."""
from __future__ import annotations

import os
import sys
from typing import List, Optional

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from . import i18n
from .devices.base import DENIED, LOADING, LOCKED, NO_DRIVER, READY, UNSUPPORTED, WAITING, DeviceBackend
from .engine import PERIODS, ImportHistory, MediaItem, default_destination, filter_items
from .gallery import GalleryModel, GalleryView
from .i18n import tr
from .importer import ImportJob, ImportOptions, ImportResult
from .resources import resource_path
from .styles import stylesheet

P_WAIT, P_BROWSE, P_PROGRESS, P_DONE = range(4)


def _label(text="", name=None, wrap=False, align=None) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    if align is not None:
        lab.setAlignment(align)
    return lab


class MainWindow(QMainWindow):
    def __init__(self, backend: DeviceBackend, settings: Optional[QSettings] = None, history_path: Optional[str] = None):
        super().__init__()
        self.settings = settings or QSettings()
        i18n.set_lang(self.settings.value("lang", "th"))
        self.backend = backend
        if history_path is None:
            data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            history_path = os.path.join(data_dir, "history.json")
        self.history = ImportHistory(history_path)
        self.all_items: List[MediaItem] = []
        self.device: Optional[dict] = None
        self.job: Optional[ImportJob] = None
        self.last_result: Optional[ImportResult] = None
        self.period = self.settings.value("period", "today")
        if self.period not in PERIODS:
            self.period = "today"
        self.destination = self.settings.value("destination", default_destination())

        self.setWindowTitle(tr("app_title"))
        self.resize(1080, 760)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(stylesheet())

        self.model = GalleryModel(self)
        self.model.history = self.history
        self.model.selection_changed.connect(self._update_import_button)

        root = QWidget(objectName="Root")
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_header())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_wait())
        self.stack.addWidget(self._build_browse())
        self.stack.addWidget(self._build_progress())
        self.stack.addWidget(self._build_done())
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self._thumb_timer = QTimer(self, singleShot=True, interval=120)
        self._thumb_timer.timeout.connect(self._request_thumbs)

        backend.device_changed.connect(self._on_device)
        backend.status_changed.connect(self._on_status)
        backend.items_ready.connect(self._on_items)
        backend.thumbnail_ready.connect(self.model.set_thumbnail)
        backend.progress.connect(self._on_catalog_progress)
        self.retranslate()
        self._on_status(backend.status, "")

    # ================================================================== building
    def _build_header(self):
        bar = QFrame(objectName="Header")
        h = QHBoxLayout(bar)
        h.setContentsMargins(22, 12, 18, 12)
        icon = QLabel()
        pm = QPixmap(resource_path("assets", "icon.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        h.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.brand = _label(name="Brand")
        self.tagline = _label(name="Tagline")
        col.addWidget(self.brand)
        col.addWidget(self.tagline)
        h.addLayout(col)
        h.addStretch(1)
        self.offline = _label(name="Small")
        h.addWidget(self.offline)
        h.addSpacing(12)
        self.lang_btn = QPushButton()
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_btn.clicked.connect(self._toggle_lang)
        h.addWidget(self.lang_btn)
        return bar

    def _build_wait(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.addStretch(1)
        card = QFrame(objectName="Card")
        card.setFixedWidth(560)
        v = QVBoxLayout(card)
        v.setContentsMargins(40, 36, 40, 36)
        v.setSpacing(14)
        self.wait_art = _label(align=Qt.AlignCenter)
        art = QPixmap(resource_path("assets", "icon-1024.png"))
        if not art.isNull():
            art = art.scaled(312, 312, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            art.setDevicePixelRatio(3)  # crisp on Retina / high-DPI screens
            self.wait_art.setPixmap(art)
        v.addWidget(self.wait_art)
        self.wait_title = _label(name="Title", align=Qt.AlignCenter, wrap=True)
        self.wait_msg = _label(name="Muted", align=Qt.AlignCenter, wrap=True)
        v.addWidget(self.wait_title)
        v.addWidget(self.wait_msg)
        self.steps_box = QWidget()
        sv = QVBoxLayout(self.steps_box)
        sv.setContentsMargins(10, 8, 10, 4)
        sv.setSpacing(12)
        self.step_labels = []
        for n in range(3):
            row = QHBoxLayout()
            num = _label(str(n + 1), "StepNum", align=Qt.AlignCenter)
            text = _label(name="Step", wrap=True)
            row.addWidget(num, 0, Qt.AlignTop)
            row.addSpacing(6)
            row.addWidget(text, 1)
            sv.addLayout(row)
            self.step_labels.append(text)
        v.addWidget(self.steps_box)
        self.wait_status = _label(name="Small", align=Qt.AlignCenter)
        v.addSpacing(6)
        v.addWidget(self.wait_status)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(card)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(2)
        return page

    def _build_browse(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        top = QWidget()
        t = QVBoxLayout(top)
        t.setContentsMargins(22, 16, 22, 8)
        t.setSpacing(10)
        row1 = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(1)
        self.dev_name = _label(name="DeviceName")
        self.dev_line = _label(name="Muted")
        col.addWidget(self.dev_name)
        col.addWidget(self.dev_line)
        row1.addLayout(col)
        row1.addStretch(1)
        self.period_group = QButtonGroup(self)
        self.period_group.setExclusive(True)
        self.period_btns = {}
        seg = QHBoxLayout()
        seg.setSpacing(0)
        for i, key in enumerate(PERIODS):
            b = QPushButton(objectName="SegFirst" if i == 0 else "SegLast" if i == len(PERIODS) - 1 else "Seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(key == self.period)
            b.clicked.connect(lambda _c=False, k=key: self._set_period(k))
            self.period_group.addButton(b)
            self.period_btns[key] = b
            seg.addWidget(b)
        row1.addLayout(seg)
        t.addLayout(row1)

        row2 = QHBoxLayout()
        self.chk_videos = QCheckBox()
        self.chk_videos.setChecked(self.settings.value("videos", False, type=bool))
        self.chk_videos.toggled.connect(lambda on: (self.settings.setValue("videos", on), self._refilter()))
        self.chk_hide = QCheckBox()
        self.chk_hide.setChecked(self.settings.value("hide_imported", False, type=bool))
        self.chk_hide.toggled.connect(lambda on: (self.settings.setValue("hide_imported", on), self._refilter()))
        row2.addWidget(self.chk_videos)
        row2.addSpacing(14)
        row2.addWidget(self.chk_hide)
        row2.addStretch(1)
        self.sel_label = _label(name="Muted")
        row2.addWidget(self.sel_label)
        self.btn_all = QPushButton(objectName="Link")
        self.btn_all.setCursor(Qt.PointingHandCursor)
        self.btn_all.clicked.connect(lambda: self.model.select_all(True))
        self.btn_none = QPushButton(objectName="Link")
        self.btn_none.setCursor(Qt.PointingHandCursor)
        self.btn_none.clicked.connect(lambda: self.model.select_all(False))
        row2.addWidget(self.btn_all)
        row2.addWidget(self.btn_none)
        t.addLayout(row2)
        v.addWidget(top)

        self.grid_stack = QStackedWidget()
        self.view = GalleryView(self.model)
        self.view.scrolled.connect(lambda _r: self._thumb_timer.start())
        self.grid_stack.addWidget(self.view)
        empty = QWidget()
        ev = QVBoxLayout(empty)
        ev.addStretch(1)
        self.empty_title = _label(name="Title", align=Qt.AlignCenter)
        self.empty_hint = _label(name="Muted", align=Qt.AlignCenter)
        ev.addWidget(self.empty_title)
        ev.addWidget(self.empty_hint)
        ev.addStretch(2)
        self.grid_stack.addWidget(empty)
        v.addWidget(self.grid_stack, 1)

        bottom = QFrame(objectName="Bottom")
        b = QHBoxLayout(bottom)
        b.setContentsMargins(22, 14, 22, 14)
        b.setSpacing(16)
        opts = QVBoxLayout()
        opts.setSpacing(8)
        prow = QHBoxLayout()
        self.save_to = _label()
        self.path_label = _label(name="Path")
        self.path_label.setMinimumWidth(220)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.btn_change = QPushButton()
        self.btn_change.setCursor(Qt.PointingHandCursor)
        self.btn_change.clicked.connect(self._pick_folder)
        prow.addWidget(self.save_to)
        prow.addWidget(self.path_label, 1)
        prow.addWidget(self.btn_change)
        opts.addLayout(prow)
        crow = QHBoxLayout()
        self.chk_date = QCheckBox()
        self.chk_date.setChecked(self.settings.value("by_date", True, type=bool))
        self.chk_date.toggled.connect(lambda on: self.settings.setValue("by_date", on))
        self.chk_jpg = QCheckBox()
        self.chk_jpg.setChecked(self.settings.value("to_jpg", True, type=bool))
        self.chk_jpg.toggled.connect(lambda on: self.settings.setValue("to_jpg", on))
        crow.addWidget(self.chk_date)
        crow.addSpacing(14)
        crow.addWidget(self.chk_jpg)
        crow.addStretch(1)
        opts.addLayout(crow)
        b.addLayout(opts, 1)
        self.btn_import = QPushButton(objectName="Primary")
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setMinimumHeight(52)
        self.btn_import.setMinimumWidth(240)
        self.btn_import.clicked.connect(self._start_import)
        b.addWidget(self.btn_import)
        v.addWidget(bottom)
        return page

    def _build_progress(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.addStretch(1)
        card = QFrame(objectName="Card")
        card.setFixedWidth(520)
        v = QVBoxLayout(card)
        v.setContentsMargins(36, 32, 36, 32)
        v.setSpacing(14)
        self.prog_title = _label(name="Title", align=Qt.AlignCenter)
        self.prog_file = _label(name="Muted", align=Qt.AlignCenter)
        self.prog_bar = QProgressBar()
        self.prog_bar.setTextVisible(False)
        self.btn_cancel = QPushButton()
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(lambda: self.job and self.job.cancel())
        v.addWidget(self.prog_title)
        v.addWidget(self.prog_bar)
        v.addWidget(self.prog_file)
        v.addWidget(self.btn_cancel, 0, Qt.AlignCenter)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(card)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(2)
        return page

    def _build_done(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.addStretch(1)
        card = QFrame(objectName="Card")
        card.setFixedWidth(560)
        v = QVBoxLayout(card)
        v.setContentsMargins(36, 32, 36, 32)
        v.setSpacing(12)
        self.done_title = _label(name="Title", align=Qt.AlignCenter)
        self.done_msg = _label(name="Muted", align=Qt.AlignCenter, wrap=True)
        self.done_failed = _label(name="Small", align=Qt.AlignCenter, wrap=True)
        v.addWidget(self.done_title)
        v.addWidget(self.done_msg)
        v.addWidget(self.done_failed)
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_open = QPushButton(objectName="Primary")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_result_folder)
        self.btn_back = QPushButton()
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self._back_to_browse)
        row.addWidget(self.btn_back)
        row.addWidget(self.btn_open)
        row.addStretch(1)
        v.addSpacing(8)
        v.addLayout(row)
        r2 = QHBoxLayout()
        r2.addStretch(1)
        r2.addWidget(card)
        r2.addStretch(1)
        outer.addLayout(r2)
        outer.addStretch(2)
        return page

    # ================================================================== texts
    def retranslate(self):
        self.setWindowTitle(tr("app_title"))
        self.brand.setText(tr("app_title"))
        self.tagline.setText(tr("tagline"))
        self.offline.setText("🔒 " + tr("offline"))
        self.lang_btn.setText(tr("lang_switch"))
        for lab, key in zip(self.step_labels, ("wait_step1", "wait_step2", "wait_step3")):
            lab.setText(tr(key))
        for key, b in self.period_btns.items():
            b.setText(tr("p_" + key))
        self.chk_videos.setText(tr("show_videos"))
        self.chk_hide.setText(tr("hide_imported"))
        self.btn_all.setText(tr("select_all"))
        self.btn_none.setText(tr("select_none"))
        self.empty_title.setText(tr("empty_title"))
        self.empty_hint.setText(tr("empty_hint"))
        self.save_to.setText(tr("save_to"))
        self.path_label.setText(self.destination)
        self.btn_change.setText(tr("change"))
        self.chk_date.setText(tr("by_date"))
        self.chk_jpg.setText(tr("to_jpg"))
        self.btn_cancel.setText(tr("cancel"))
        self.btn_open.setText(tr("open_folder"))
        self.btn_back.setText(tr("back"))
        self._on_status(self.backend.status, "")
        self._update_device_line()
        self._update_import_button()
        if self.last_result is not None:
            self._show_result(self.last_result)
        self.model.refresh_all()

    def _toggle_lang(self):
        i18n.set_lang("en" if i18n.lang() == "th" else "th")
        self.settings.setValue("lang", i18n.lang())
        self.retranslate()

    # ================================================================== backend events
    def _device_name(self) -> str:
        return (self.device or {}).get("name", "iPhone")

    def _on_device(self, info):
        self.device = info
        if info:
            self.history.use_device(info.get("id", ""))
        else:
            self.all_items = []
            self.model.set_items([])
            self.model.clear_thumbs()
        self._update_device_line()

    def _on_status(self, status, detail):
        if self.job is not None:
            return  # keep the progress page while copying
        if status == READY:
            if self.stack.currentIndex() == P_WAIT:
                self.stack.setCurrentIndex(P_BROWSE)
            return
        name = self._device_name()
        texts = {
            WAITING: (tr("wait_title"), "", True, tr("searching")),
            LOCKED: (tr("locked_title"), tr("locked_msg", name=name), True, ""),
            LOADING: (tr("loading_title"), tr("loading_msg", name=name), False, ""),
            DENIED: (tr("denied_title"), tr("denied_msg"), False, detail),
            NO_DRIVER: (tr("nodriver_title"), tr("nodriver_msg"), False, ""),
            UNSUPPORTED: (tr("unsupported"), "", False, ""),
        }
        title, msg, steps, small = texts.get(status, texts[WAITING])
        self.wait_title.setText(title)
        self.wait_msg.setText(msg)
        self.wait_msg.setVisible(bool(msg))
        self.steps_box.setVisible(steps)
        self.wait_status.setText(small)
        if self.stack.currentIndex() != P_DONE:  # let the user read the result even after unplugging
            self.stack.setCurrentIndex(P_WAIT)

    def _on_catalog_progress(self, pct):
        if self.backend.status == LOADING and pct:
            self.wait_status.setText(f"{pct}%")

    def _on_items(self, items):
        self.all_items = items
        self._update_device_line()
        self._refilter()
        if self.job is None and self.stack.currentIndex() == P_WAIT:
            self.stack.setCurrentIndex(P_BROWSE)

    # ================================================================== browsing
    def _update_device_line(self):
        self.dev_name.setText("📱 " + self._device_name())
        photos = sum(1 for i in self.all_items if i.kind == "photo")
        videos = sum(1 for i in self.all_items if i.kind == "video" and not i.live_companion)
        self.dev_line.setText(tr("device_line", photos=photos, videos=videos))

    def _set_period(self, key):
        self.period = key
        self.settings.setValue("period", key)
        self._refilter()

    def _refilter(self):
        shown = filter_items(self.all_items, self.period, include_videos=self.chk_videos.isChecked(),
                             hide_imported=self.chk_hide.isChecked(), history=self.history)
        self.model.set_items(shown)
        self.grid_stack.setCurrentIndex(0 if shown else 1)
        self.view.scrollToTop()
        self._thumb_timer.start()

    def _request_thumbs(self):
        self.backend.want_thumbnails(self.model.missing_thumbs(self.view.first_visible()))

    def _update_import_button(self):
        n = len(self.model.selected)
        self.sel_label.setText(tr("selected", n=n, total=len(self.model.items)))
        self.btn_import.setEnabled(n > 0)
        self.btn_import.setText(tr("import_n", n=n) if n else tr("import_none"))

    def _pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, tr("pick_folder"), self.destination)
        if path:
            self.destination = path
            self.settings.setValue("destination", path)
            self.path_label.setText(path)

    # ================================================================== import
    def _start_import(self):
        items = self.model.selected_items()
        if not items:
            return
        opt = ImportOptions(root=self.destination, by_date=self.chk_date.isChecked(),
                            convert_heic=self.chk_jpg.isChecked())
        self.job = ImportJob(self.backend, items, opt, self.history, self)
        self.job.progress.connect(self._on_progress)
        self.job.finished.connect(self._on_finished)
        self.prog_bar.setRange(0, len(items))
        self.prog_bar.setValue(0)
        self.stack.setCurrentIndex(P_PROGRESS)
        self.job.start()

    def _on_progress(self, done, total, name):
        self.prog_title.setText(tr("importing", done=done, total=total))
        self.prog_file.setText(name)
        self.prog_bar.setValue(done)

    def _on_finished(self, result: ImportResult):
        self.job = None
        self.last_result = result
        self._show_result(result)
        self.stack.setCurrentIndex(P_DONE)
        self.model.refresh_all()

    def _show_result(self, r: ImportResult):
        folder = r.folders[0] if len(r.folders) == 1 else self.destination
        if r.cancelled:
            self.done_title.setText(tr("done_cancel", n=len(r.copied)))
        else:
            self.done_title.setText(tr("done_title"))
        self.done_msg.setText(tr("done_msg", n=len(r.copied), folder=folder))
        if r.failed:
            names = ", ".join(r.failed[:5]) + ("…" if len(r.failed) > 5 else "")
            self.done_failed.setText(tr("done_failed", n=len(r.failed), names=names))
        else:
            self.done_failed.setText("")
        self.done_failed.setVisible(bool(r.failed))

    def _open_result_folder(self):
        r = self.last_result
        folder = r.folders[0] if r and len(r.folders) == 1 else self.destination
        os.makedirs(folder, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _back_to_browse(self):
        self.last_result = None
        if self.backend.status == READY:
            self._refilter()
            self.stack.setCurrentIndex(P_BROWSE)
        else:
            self.stack.setCurrentIndex(P_WAIT)
            self._on_status(self.backend.status, "")

    def closeEvent(self, e):
        if self.job is not None:
            self.job.cancel()
        self.backend.stop()
        super().closeEvent(e)
