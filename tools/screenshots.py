"""Run the real app with the real device backend and save README screenshots.

    .venv/bin/python tools/screenshots.py            # waiting screen (+ gallery if an iPhone is plugged in)
    .venv/bin/python tools/screenshots.py --wait 60  # give yourself time to plug in / unlock the phone

Writes docs/screenshots/{waiting,gallery}-{th,en}.png. Settings and history go to a temp
folder, so your own settings are not touched.
"""
import argparse
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QSettings, QTimer  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import i18n  # noqa: E402
from app.devices.base import READY, create_backend  # noqa: E402
from app.main_window import P_BROWSE, MainWindow  # noqa: E402
from app.resources import app_icon  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screenshots")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=int, default=20, help="seconds to wait for an iPhone")
    ap.add_argument("--period", default="week")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("iPhone Photo Import")
    app.setWindowIcon(app_icon())
    font = QFont()
    font.setFamilies(["Segoe UI", "Leelawadee UI", "Tahoma", "Helvetica Neue", "Thonburi"])
    app.setFont(font)
    tmp = tempfile.mkdtemp()
    settings = QSettings(os.path.join(tmp, "s.ini"), QSettings.IniFormat)
    settings.setValue("period", args.period)
    backend = create_backend()
    win = MainWindow(backend, settings, history_path=os.path.join(tmp, "history.json"))
    win.resize(1080, 760)
    win.show()
    backend.start()
    os.makedirs(OUT, exist_ok=True)

    def shoot(name):
        for lang in ("th", "en"):
            i18n.set_lang(lang)
            win.retranslate()
            app.processEvents()
            win.grab().save(os.path.join(OUT, f"{name}-{lang}.png"))
            print("saved", f"{name}-{lang}.png")

    state = {"t": 0, "waiting_done": False}

    def tick():
        state["t"] += 1
        if not state["waiting_done"] and state["t"] >= 2 and backend.status != READY:
            shoot("waiting")
            state["waiting_done"] = True
        if backend.status == READY and win.stack.currentIndex() == P_BROWSE:
            if state["t"] % 4 == 0:  # give thumbnails time to arrive
                shoot("gallery")
                app.quit()
            return
        if state["t"] > args.wait:
            print("no iPhone ready - only the waiting screen was captured; status:", backend.status)
            app.quit()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(1000)
    app.exec()
    backend.stop()


if __name__ == "__main__":
    main()
