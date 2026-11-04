import os
import sys

from PySide6.QtGui import QIcon


def resource_path(*parts: str) -> str:
    """Works both from source and from a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


_icon = None


def app_icon() -> QIcon:
    global _icon
    if _icon is None:
        _icon = QIcon(resource_path("assets", "icon.png"))
    return _icon
