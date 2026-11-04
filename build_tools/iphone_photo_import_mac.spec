# PyInstaller spec for macOS -> dist/iPhone Photo Import.app
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
VERSION = os.environ.get("APP_VERSION", "1.0.0")

EXCLUDES = ["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
            "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtBluetooth", "PySide6.QtSql"]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "assets"), "assets")],
    hiddenimports=["ImageCaptureCore", "pillow_heif"],
    excludes=EXCLUDES,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="iPhone Photo Import",
          console=False, upx=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name="iPhone Photo Import", upx=False)
app = BUNDLE(
    coll,
    name="iPhone Photo Import.app",
    icon=os.path.join(ROOT, "build", "icon.icns"),
    bundle_identifier="com.madara1150.iphonephotoimport",
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "iPhone Photo Import",
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSHumanReadableCopyright": "Copyright (c) 2026 Tanathip",
        # shown by macOS when the app first reads photos from a connected iPhone
        "NSCameraUsageDescription": "Read photos and videos from your connected iPhone so you can copy them to this Mac.",
    },
)
