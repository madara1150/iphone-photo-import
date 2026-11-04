import os
from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app import i18n
from app.main_window import P_BROWSE, P_DONE, P_WAIT, MainWindow
from tests.fake_device import FakeBackend, make_photos

NOW = datetime.now()
SPECS = [
    ("IMG_0001.HEIC", NOW - timedelta(minutes=30)),
    ("IMG_0001.MOV", NOW - timedelta(minutes=30)),   # Live Photo half
    ("IMG_0002.JPG", NOW - timedelta(minutes=10)),
    ("IMG_0003.HEIC", NOW - timedelta(days=3)),
    ("IMG_0004.MOV", NOW - timedelta(minutes=5)),    # real video
]


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(qapp, tmp_path):
    phone = tmp_path / "phone"
    make_photos(str(phone), SPECS)
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    settings.setValue("destination", str(tmp_path / "out"))
    settings.setValue("period", "today")
    backend = FakeBackend(str(phone), SPECS)
    w = MainWindow(backend, settings, history_path=str(tmp_path / "history.json"))
    backend.start()
    yield w, backend, tmp_path
    w.close()


def wait_until(qapp, cond, timeout=10.0):
    import time
    end = time.time() + timeout
    while time.time() < end:
        qapp.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_waits_then_shows_todays_photos(win, qapp):
    w, backend, _ = win
    assert w.stack.currentIndex() == P_WAIT
    backend.plug_in(locked=True)
    qapp.processEvents()
    assert w.stack.currentIndex() == P_WAIT
    assert "Test iPhone" in w.wait_msg.text()
    backend.plug_in()
    qapp.processEvents()
    assert w.stack.currentIndex() == P_BROWSE
    names = [i.name for i in w.model.items]
    assert names == ["IMG_0002.JPG", "IMG_0001.HEIC"]  # today, no videos, newest first
    assert len(w.model.selected) == 2
    assert w.btn_import.isEnabled()


def test_filters(win, qapp):
    w, backend, _ = win
    backend.plug_in()
    w._set_period("week")
    assert len(w.model.items) == 3
    w.chk_videos.setChecked(True)
    names = [i.name for i in w.model.items]
    assert "IMG_0004.MOV" in names and "IMG_0001.MOV" not in names
    w.model.select_all(False)
    assert not w.btn_import.isEnabled()


def test_import_converts_and_remembers(win, qapp):
    w, backend, tmp = win
    backend.plug_in()
    w._start_import()
    assert wait_until(qapp, lambda: w.stack.currentIndex() == P_DONE)
    day = NOW.strftime("%Y-%m-%d")
    out = tmp / "out" / day
    files = sorted(os.listdir(out))
    assert files == ["IMG_0001.JPG", "IMG_0002.JPG"]
    assert w.last_result.failed == []
    # back: both are now marked as imported and nothing is pre-selected
    w._back_to_browse()
    assert w.stack.currentIndex() == P_BROWSE
    assert len(w.model.selected) == 0
    assert all(w.model.is_imported(i) for i in w.model.items)
    # importing again never overwrites
    w.model.select_all(True)
    w._start_import()
    assert wait_until(qapp, lambda: w.stack.currentIndex() == P_DONE)
    assert sorted(os.listdir(out)) == ["IMG_0001 (2).JPG", "IMG_0001.JPG", "IMG_0002 (2).JPG", "IMG_0002.JPG"]


def test_import_keeps_heic_when_asked_and_reports_failures(win, qapp):
    w, backend, tmp = win
    backend.plug_in()
    backend.fail.add("IMG_0002.JPG")
    w.chk_jpg.setChecked(False)
    w.chk_date.setChecked(False)
    w._start_import()
    assert wait_until(qapp, lambda: w.stack.currentIndex() == P_DONE)
    assert os.listdir(tmp / "out") == ["IMG_0001.HEIC"]
    assert w.last_result.failed == ["IMG_0002.JPG"]
    assert w.done_failed.isVisible() or w.done_failed.text()


def test_unplug_returns_to_waiting(win, qapp):
    w, backend, _ = win
    backend.plug_in()
    backend.unplug()
    qapp.processEvents()
    assert w.stack.currentIndex() == P_WAIT
    assert w.model.rowCount() == 0


def test_language_switch(win, qapp):
    w, backend, _ = win
    i18n.set_lang("th")
    w.retranslate()
    th = w.wait_title.text()
    w._toggle_lang()
    assert w.wait_title.text() != th
    assert w.lang_btn.text() == "ภาษาไทย"
    w._toggle_lang()
