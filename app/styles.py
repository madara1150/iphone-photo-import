"""Qt stylesheet (one calm light theme; follows the look of the other apps in this family)."""

P = {
    "bg": "#f3f5fa", "panel": "#ffffff", "border": "#e2e6ef", "text": "#172036", "muted": "#67708a",
    "accent": "#2563eb", "accent2": "#0ea5a4", "accent_soft": "#e8f0ff", "hover": "#f1f4fa",
    "good": "#16a34a", "bad": "#e11d48", "tile": "#e9edf5",
}


def c(key: str) -> str:
    return P[key]


def stylesheet() -> str:
    p = P
    return f"""
* {{ color: {p['text']}; font-size: 13px; }}
QMainWindow, #Root {{ background: {p['bg']}; }}
QToolTip {{ background: white; color: {p['text']}; border: 1px solid {p['border']}; padding: 6px; }}

#Header {{ background: {p['panel']}; border-bottom: 1px solid {p['border']}; }}
#Brand {{ font-size: 17px; font-weight: 800; }}
#Muted, #Tagline {{ color: {p['muted']}; }}
#Small {{ color: {p['muted']}; font-size: 11px; }}
#Title {{ font-size: 22px; font-weight: 800; }}
#DeviceName {{ font-size: 17px; font-weight: 800; }}
#Card {{ background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 18px; }}
#Bottom {{ background: {p['panel']}; border-top: 1px solid {p['border']}; }}
#Step {{ font-size: 14px; }}
#StepNum {{
    background: {p['accent_soft']}; color: {p['accent']}; border-radius: 13px; font-weight: 800;
    min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px;
}}
#Path {{ background: {p['bg']}; border: 1px solid {p['border']}; border-radius: 9px; padding: 6px 10px; }}

QPushButton {{
    background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 10px;
    padding: 7px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: {p['hover']}; }}
QPushButton:disabled {{ color: #a9b0c2; }}
QPushButton#Primary {{
    color: white; border: none; border-radius: 12px; padding: 12px 26px; font-size: 15px; font-weight: 800;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['accent']}, stop:1 {p['accent2']});
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4fd8, stop:1 #0b8f8e);
}}
QPushButton#Primary:disabled {{ background: #c3cad9; color: white; }}
QPushButton#Seg {{ border-radius: 0; padding: 7px 16px; margin: 0; }}
QPushButton#SegFirst {{ border-top-right-radius: 0; border-bottom-right-radius: 0; padding: 7px 16px; }}
QPushButton#SegLast {{ border-top-left-radius: 0; border-bottom-left-radius: 0; padding: 7px 16px; }}
QPushButton#Seg:checked, QPushButton#SegFirst:checked, QPushButton#SegLast:checked {{
    background: {p['accent']}; color: white; border-color: {p['accent']};
}}
QPushButton#Link {{ border: none; background: transparent; color: {p['accent']}; padding: 4px 6px; }}
QPushButton#Link:hover {{ text-decoration: underline; }}

QCheckBox {{ spacing: 7px; }}
QListView {{ background: {p['bg']}; border: none; outline: 0; }}
QProgressBar {{
    background: {p['tile']}; border: none; border-radius: 7px; height: 14px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['accent']}, stop:1 {p['accent2']});
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #c9cfdc; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""
