"""Design tokens and stylesheet for the alternate ledger interface.

Design read: the same attention data written up as a field log — a light,
ruled page where the dark pond survives as one framed viewport. Hairline
rules are the structure; there are no cards, shadows, or gradients.

Principles applied:
- ONE accent, locked: deep pond green — the phosphor trace translated to
  ink so it stays legible on paper. Amber/red appear only as data colors.
- ONE light theme, locked. The pond viewport is the only dark surface and
  the page's one memorable thing.
- Square edges throughout: ruled-paper corners, no radius.
- Serif hand for the masthead and date; system sans elsewhere; mono for
  figures that tabulate (clocks, dwell times).
"""

# ------------------------------------------------------------------ palette

PAPER = "#FBFBF9"         # page
RAISED = "#F3F4EF"        # inset fills, hover
BORDER = "#E3E4DD"        # hairlines
BORDER_STRONG = "#C2C5BA" # focused/pressed edges, pond frame

INK = "#1D1F1C"           # primary text
MUTED = "#6E726A"         # secondary text, captions, grid labels

ACCENT = "#177A4C"        # pond green on paper: rules that matter, primary action
ACCENT_PRESS = "#116139"
WARN = "#A96F15"          # moderate fragmentation (data color)
ALERT = "#C03A30"         # high fragmentation (data color)

POND = "#1B1E25"          # the viewport keeps the pond's own dark water
POND_TEXT = "#8D93A1"     # caption ink on the dark viewport

# ------------------------------------------------------------------ type

FONT_FAMILY = (
    '-apple-system, "SF Pro Text", "Helvetica Neue", "Segoe UI", sans-serif'
)
FONT_SERIF = 'Georgia, "New York", "Times New Roman", serif'
FONT_MONO = '"SF Mono", "Menlo", "Consolas", monospace'
FS_CAPTION = 11
FS_BODY = 13
FS_TITLE = 17
FS_METRIC = 15

# ------------------------------------------------------------------ spacing

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24


def stylesheet() -> str:
    """The single QSS stylesheet every ledger widget inherits."""
    return f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: {FS_BODY}px;
    color: {INK};
    outline: none;
}}

QMainWindow, QWidget {{
    background: {PAPER};
}}

/* ------------------------- toolbar: masthead rule */
QToolBar {{
    background: {PAPER};
    border: none;
    border-bottom: 1px solid {BORDER_STRONG};
    padding: 6px 10px;
    spacing: 8px;
}}
QToolButton {{
    background: transparent;
    border: 1px solid {BORDER_STRONG};
    color: {INK};
    padding: 4px 12px;
}}
QToolButton:hover {{ background: {RAISED}; }}
QToolButton:checked {{
    background: {RAISED};
    border-color: {ACCENT};
    color: {ACCENT};
}}

/* ------------------------- buttons: paper rectangles, hairline edge */
QPushButton {{
    background: {PAPER};
    border: 1px solid {BORDER_STRONG};
    padding: 6px 14px;
    min-height: 18px;
}}
QPushButton:hover {{
    background: {RAISED};
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
    color: {PAPER};
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{ background: {ACCENT_PRESS}; }}
QPushButton[accent="true"]:pressed {{ background: {ACCENT_PRESS}; }}

/* ------------------------- combo boxes: same hairline shape */
QComboBox {{
    background: {PAPER};
    border: 1px solid {BORDER_STRONG};
    padding: 5px 12px;
    min-height: 18px;
}}
QComboBox:hover {{ background: {RAISED}; }}
QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {PAPER};
    border: 1px solid {BORDER_STRONG};
    selection-background-color: {RAISED};
    selection-color: {INK};
    outline: none;
}}

/* ------------------------- slider: a ruled line the playhead rides */
QSlider::groove:horizontal {{
    height: 2px;
    background: {BORDER_STRONG};
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; }}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 10px;
    height: 10px;
    margin: -5px 0;
}}
QSlider::handle:horizontal:hover {{ background: {INK}; }}

/* ------------------------- tables: ledger rows, no card chrome */
QTableWidget {{
    background: {PAPER};
    border: none;
    border-top: 1px solid {BORDER_STRONG};
    gridline-color: {BORDER};
    selection-background-color: {RAISED};
    selection-color: {INK};
    alternate-background-color: {PAPER};
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QTableWidget::item:selected {{ background: {RAISED}; }}
QHeaderView::section {{
    background: {PAPER};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER_STRONG};
    padding: 6px 10px;
    font-size: {FS_CAPTION}px;
}}

/* ------------------------- scrollbars: quiet hairline thumbs */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ------------------------- labels and ledger figures */
QLabel#wordmark {{
    font-family: {FONT_SERIF};
    font-size: {FS_TITLE}px;
    font-weight: 600;
}}
QLabel#dateLabel {{
    font-family: {FONT_SERIF};
    font-size: {FS_TITLE}px;
}}
QLabel#sectionLabel {{
    color: {MUTED};
    font-size: {FS_CAPTION}px;
    font-weight: 600;
}}
QLabel#metricName {{
    color: {MUTED};
}}
QLabel#metricValue {{
    font-family: {FONT_MONO};
    font-size: {FS_METRIC}px;
    font-weight: 600;
}}
QLabel#clockLabel {{
    font-family: {FONT_MONO};
    font-size: {FS_CAPTION}px;
    color: {MUTED};
}}
QLabel#pondCaption {{
    font-family: {FONT_MONO};
    font-size: {FS_CAPTION}px;
    color: {POND_TEXT};
}}
QLabel#listName {{
    color: {INK};
}}
QLabel#listValue {{
    font-family: {FONT_MONO};
    color: {MUTED};
}}
QLabel#nextLabel {{
    color: {MUTED};
}}

/* ------------------------- rules and frames */
QFrame#rule {{ background: {BORDER}; max-height: 1px; }}
QFrame#vrule {{ background: {BORDER}; max-width: 1px; }}
QFrame#pondFrame {{
    background: {POND};
    border: 1px solid {BORDER_STRONG};
}}
QFrame#ledgerRow {{ border-bottom: 1px solid {BORDER}; }}
QFrame#ledgerRow QLabel {{ border: none; }}

/* ------------------------- status bar + tooltip */
QStatusBar {{
    border-top: 1px solid {BORDER_STRONG};
    color: {MUTED};
}}
QStatusBar QLabel {{ color: {MUTED}; }}
QToolTip {{
    background: {PAPER};
    color: {INK};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 8px;
}}
"""


def apply(app) -> None:
    """Install the ledger theme on a QApplication."""
    from PySide6.QtGui import QFont

    app.setFont(QFont("SF Pro Text", FS_BODY))
    app.setStyleSheet(stylesheet())
