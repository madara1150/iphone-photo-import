# PyInstaller spec (Windows) — antivirus-friendly settings:
#   * one-folder build (no self-extracting onefile stub, the #1 false-positive trigger)
#   * UPX disabled, real version resource + icon, windowed app
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

EXCLUDES = ["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
            "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtBluetooth", "PySide6.QtSql"]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "assets"), "assets")],
    hiddenimports=["win32com.client", "pythoncom", "pywintypes", "pillow_heif"],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="iPhonePhotoImport",
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    version=os.path.join(ROOT, "build_tools", "version_info.txt"),
    console=False,
    upx=False,
    strip=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="iPhonePhotoImport", upx=False, strip=False)
