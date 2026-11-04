import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.devices.base import create_backend
from app.main_window import MainWindow
from app.resources import app_icon


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("iPhone Photo Import")
    app.setOrganizationName("madara1150")
    app.setWindowIcon(app_icon())
    font = QFont()
    # Leelawadee UI renders Thai nicely on Windows; Segoe UI for Latin
    font.setFamilies(["Segoe UI", "Leelawadee UI", "Tahoma", "Helvetica Neue", "Thonburi"])
    app.setFont(font)

    backend = create_backend()
    win = MainWindow(backend)
    win.show()
    backend.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
