"""Design tokens and the central stylesheet for Rewind.

Design read: a calm, single-window macOS instrument. One memorable thing —
the EKG trace — and everything around it quiet and disciplined.

Principles applied (taste-skill philosophy, ported to QSS):
- ONE accent color, locked app-wide: phosphor green, the trace itself.
  Amber/red appear only as *data* colors for fragmentation severity and the
  replay playhead, never as decoration.
- ONE dark theme, locked. No light/dark mixing anywhere.
- ONE corner-radius scale (6px) for every interactive element.
- Hairline borders + negative space instead of card chrome.
- System type stack with a small deliberate scale; sentence-case labels.
- Motivated motion only: the replay playhead (it shows replay progress).
  No decorative animation.
"""

# ------------------------------------------------------------------ palette

BG_BASE = "#14161A"       # window surface: deep slate-charcoal
BG_RAISED = "#1B1E25"     # tables, trace canvas, inputs
BG_HOVER = "#232733"      # hover fills
BORDER = "#2B303B"        # hairlines
BORDER_STRONG = "#3B4150" # focused/pressed edges

TEXT = "#E8EAEF"          # primary text
TEXT_MUTED = "#8D93A1"    # secondary text, captions, grid labels

ACCENT = "#3BD98A"        # phosphor green: trace, primary action, focus ring
ACCENT_PRESS = "#2CB573"
WARN = "#E8A33D"          # moderate fragmentation (data color)
ALERT = "#F0554D"         # high fragmentation, playhead (data color)

# ------------------------------------------------------------------ type

FONT_FAMILY = (
    '-apple-system, "SF Pro Text", "Helvetica Neue", "Segoe UI", sans-serif'
)
FONT_MONO = '"SF Mono", "Menlo", "Consolas", monospace'
FS_CAPTION = 11
FS_BODY = 13
FS_TITLE = 17
FS_METRIC = 24

# ------------------------------------------------------------------ spacing

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24

RADIUS = 6                # the one radius scale, used everywhere


def stylesheet() -> str:
    """The single QSS stylesheet every view inherits."""
    return f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: {FS_BODY}px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QWidget {{
    background: {BG_BASE};
}}

/* ------------------------- tabs: quiet chrome, accent underline */
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {BORDER};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 16px;
    margin-right: 2px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}

/* ------------------------- buttons: one shape, tactile states */
QPushButton {{
    background: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 6px 14px;
    min-height: 18px;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {BORDER_STRONG};
}}
QPushButton:pressed {{
    background: {BORDER};
}}
QPushButton:focus {{
    border-color: {ACCENT};
}}
QPushButton[accent="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #0E1512;
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{ background: {ACCENT_PRESS}; }}
QPushButton[accent="true"]:pressed {{ background: {ACCENT_PRESS}; }}

/* ------------------------- combo boxes: same hairline shape as buttons */
QComboBox {{
    background: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    padding: 5px 12px;
    min-height: 18px;
}}
QComboBox:hover {{ border-color: {BORDER_STRONG}; }}
QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {BG_RAISED};
    border: 1px solid {BORDER_STRONG};
    selection-background-color: {BG_HOVER};
    selection-color: {TEXT};
    outline: none;
}}

/* ------------------------- toolbar: slim instrument strip */
QToolBar {{
    background: {BG_BASE};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px;
    spacing: 8px;
}}
QToolButton {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    color: {TEXT};
    padding: 4px 12px;
}}
QToolButton:hover {{ background: {BG_HOVER}; }}
QToolButton:checked {{
    background: {BG_RAISED};
    border-color: {ACCENT};
    color: {ACCENT};
}}

/* ------------------------- tables: hairline grid, no card chrome */
QTableWidget {{
    background: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    gridline-color: {BORDER};
    selection-background-color: {BG_HOVER};
    selection-color: {TEXT};
    alternate-background-color: #181B21;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QTableWidget::item:selected {{ background: {BG_HOVER}; }}
QHeaderView::section {{
    background: {BG_BASE};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-size: {FS_CAPTION}px;
}}

/* ------------------------- labels and the metric strip */
QLabel#sectionLabel {{
    color: {TEXT_MUTED};
    font-size: {FS_CAPTION}px;
    font-weight: 600;
}}
QLabel#metricValue {{
    font-size: {FS_METRIC}px;
    font-weight: 600;
}}
QLabel#metricLabel {{
    color: {TEXT_MUTED};
    font-size: {FS_CAPTION}px;
}}
QLabel#dateLabel {{
    font-size: {FS_TITLE}px;
    font-weight: 600;
}}
QFrame#metricDivider {{
    background: {BORDER};
    max-width: 1px;
}}

/* ------------------------- status bar + tooltip */
QStatusBar {{
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}
QStatusBar QLabel {{ color: {TEXT_MUTED}; }}
QToolTip {{
    background: {BG_RAISED};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 8px;
}}
"""


def apply(app) -> None:
    """Install the theme on a QApplication."""
    from PySide6.QtGui import QFont

    app.setFont(QFont("SF Pro Text", FS_BODY))
    app.setStyleSheet(stylesheet())
