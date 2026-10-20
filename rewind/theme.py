"""Application theme — a restrained, macOS-style dark palette.

Design rules: flat surfaces (no gradients anywhere), 1px hairline
separators instead of shadows or cards, a typography-first hierarchy,
and one system accent reserved for the primary action.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

# --- surfaces ---------------------------------------------------------------
WINDOW_BG = "#1e1e20"
SIDEBAR_BG = "#1a1a1c"
PANEL_BG = "#19191b"
CONTROL_BG = "#3a3a3e"
CONTROL_HOVER = "#464649"
CONTROL_PRESSED = "#2e2e31"
SELECTION_BG = "#3d3d42"

# --- hairlines ----------------------------------------------------------------
HAIRLINE = "#303033"
HAIRLINE_SOFT = "#2a2a2d"
CONTROL_EDGE = "#4a4a4e"

# --- text ---------------------------------------------------------------------
TEXT_PRIMARY = "#ececee"
TEXT_SECONDARY = "#9b9ba0"
TEXT_TERTIARY = "#6b6b70"

# --- accents (used sparingly) ---------------------------------------------------
ACCENT = "#0a84ff"          # macOS systemBlue (dark)
ACCENT_HOVER = "#1f8fff"
ACCENT_PRESSED = "#0077ee"
TRACE = "#30d158"           # macOS systemGreen (dark) — EKG trace
RIPPLE = "#ff453a"          # macOS systemRed (dark) — replay ripples

# --- chart painting -------------------------------------------------------------
GRID_LINE = QColor(255, 255, 255, 12)
BASE_LINE = QColor(255, 255, 255, 30)

FONT_FAMILIES = (
    "Inter",
    "SF Pro Text",
    "SF Pro Display",
    "Helvetica Neue",
    "Segoe UI",
    "Ubuntu",
    "DejaVu Sans",
)


def font_family() -> str:
    """First available family from the SF-like stack."""
    available = set(QFontDatabase.families())
    for family in FONT_FAMILIES:
        if family in available:
            return family
    return "sans-serif"


def apply_theme(app: QApplication) -> None:
    """Fusion base + dark palette + the global stylesheet."""
    app.setStyle("Fusion")

    font = QFont(font_family())
    font.setPointSizeF(10.0)  # ≈13 px at 96 dpi — macOS system text size
    app.setFont(font)

    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(WINDOW_BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Base, QColor(PANEL_BG))
    pal.setColor(QPalette.AlternateBase, QColor(WINDOW_BG))
    pal.setColor(QPalette.Text, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Button, QColor(CONTROL_BG))
    pal.setColor(QPalette.ButtonText, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Highlight, QColor(SELECTION_BG))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.PlaceholderText, QColor(TEXT_TERTIARY))
    pal.setColor(QPalette.ToolTipBase, QColor(CONTROL_PRESSED))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(TEXT_TERTIARY))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(TEXT_TERTIARY))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(TEXT_TERTIARY))
    app.setPalette(pal)

    app.setStyleSheet(_stylesheet())


def _stylesheet() -> str:
    return f"""
/* ---- surfaces ---- */
QMainWindow, QDialog {{
    background: {WINDOW_BG};
}}
QWidget#sidebar {{
    background: {SIDEBAR_BG};
}}
QFrame#hairlineH {{
    background: {HAIRLINE};
    border: none;
    max-height: 1px;
}}
QFrame#hairlineV {{
    background: {HAIRLINE};
    border: none;
    max-width: 1px;
}}

/* ---- typography ---- */
QLabel#pageTitle {{
    font-size: 20px;
    font-weight: 600;
}}
QLabel#pageSubtitle, QLabel#summaryLabel, QLabel#statusLabel, QLabel#countLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
QLabel#countLabel {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
}}
QLabel#sectionLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    padding-left: 2px;
}}

/* ---- sidebar source list ---- */
QListWidget#sidebarNav {{
    background: transparent;
    border: none;
    outline: 0;
    font-size: 13px;
}}
QListWidget#sidebarNav::item {{
    height: 28px;
    padding-left: 10px;
    padding-right: 8px;
    border-radius: 6px;
    color: #dcdce0;
}}
QListWidget#sidebarNav::item:selected {{
    background: {SELECTION_BG};
    color: #ffffff;
}}
QListWidget#sidebarNav::item:hover:!selected {{
    background: rgba(255, 255, 255, 0.05);
}}

/* ---- buttons ---- */
QPushButton {{
    background: {CONTROL_BG};
    border: 1px solid {CONTROL_EDGE};
    border-radius: 6px;
    padding: 4px 12px;
    color: {TEXT_PRIMARY};
    outline: none;
}}
QPushButton:hover {{
    background: {CONTROL_HOVER};
}}
QPushButton:pressed {{
    background: {CONTROL_PRESSED};
}}
QPushButton:disabled {{
    color: {TEXT_TERTIARY};
    background: {CONTROL_PRESSED};
    border-color: {HAIRLINE};
}}
QPushButton:focus {{
    border-color: rgba(10, 132, 255, 140);
}}
QPushButton#navButton {{
    padding: 0;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    font-size: 16px;
    font-weight: 500;
}}
QPushButton[accent="true"] {{
    background: {ACCENT};
    border-color: {ACCENT_PRESSED};
    color: #ffffff;
    font-weight: 500;
}}
QPushButton[accent="true"]:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton[accent="true"]:pressed {{
    background: {ACCENT_PRESSED};
}}

/* ---- tables ---- */
QTableWidget {{
    background: transparent;
    border: none;
    outline: 0;
    gridline-color: transparent;
    selection-background-color: {SELECTION_BG};
    selection-color: #ffffff;
}}
QTableWidget::item {{
    padding: 6px 8px;
    border-bottom: 1px solid {HAIRLINE_SOFT};
}}
QTableWidget::item:selected {{
    background: {SELECTION_BG};
}}
QHeaderView {{
    background: transparent;
    border: none;
}}
QHeaderView::section {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {HAIRLINE};
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    padding: 6px 8px;
}}
QTableCornerButton::section {{
    background: transparent;
    border: none;
}}

/* ---- chart panel ---- */
QWidget#chartPanel {{
    background: {PANEL_BG};
    border: 1px solid {HAIRLINE};
    border-radius: 10px;
}}

/* ---- menus & tooltips ---- */
QMenu {{
    background: {CONTROL_PRESSED};
    border: 1px solid {HAIRLINE};
    padding: 5px;
}}
QMenu::item {{
    padding: 4px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {SELECTION_BG};
}}
QToolTip {{
    background: {CONTROL_PRESSED};
    color: {TEXT_PRIMARY};
    border: 1px solid {HAIRLINE};
    padding: 4px 8px;
}}

/* ---- scrollbars: thin, flat, no arrows ---- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.26);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.26);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
"""
