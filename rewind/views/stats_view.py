"""Stats view — breakdowns for the selected timeframe.

Top apps and sites each carry a "Where you go next" column: the top 3
destinations reached immediately after leaving that item, computed from
consecutive event pairs in the same window (rewind/transitions.py).
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import theme, transitions
from ..db import EventStore
from .timeframe import TimeframeSelector


def _table(headers: list[str], stretch_col: int = 0) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(stretch_col, QHeaderView.Stretch)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setAlternatingRowColors(True)
    return t


def _section(label: str, table: QTableWidget) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.SPACE_SM)
    l = QLabel(label)
    l.setObjectName("sectionLabel")
    lay.addWidget(l)
    lay.addWidget(table)
    return box


class StatsView(QWidget):
    def __init__(self, store: EventStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.start, self.end = 0.0, 1.0

        self.timeframe = TimeframeSelector()
        head = QHBoxLayout()
        head.addWidget(self.timeframe)
        head.addStretch(1)

        self.apps_table = _table(
            ["Application", "Time", "Samples", "Where you go next"], stretch_col=3
        )
        self.sites_table = _table(
            ["Site", "Time", "Samples", "Where you go next"], stretch_col=3
        )
        self.pages_table = _table(
            ["Application", "Page or document", "Time"], stretch_col=1
        )
        self.hours_table = _table(["Hour", "Switches"])

        left = QVBoxLayout()
        left.addWidget(_section("Top applications", self.apps_table), stretch=1)
        left.addWidget(_section("Sites", self.sites_table), stretch=1)
        right = QVBoxLayout()
        right.addWidget(_section("Pages and documents", self.pages_table), stretch=1)
        right.addWidget(_section("Context switches per hour", self.hours_table), stretch=1)
        cols = QHBoxLayout()
        cols.setSpacing(theme.SPACE_XL)
        cols.addLayout(left, stretch=1)
        cols.addLayout(right, stretch=1)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            theme.SPACE_LG, theme.SPACE_MD, theme.SPACE_LG, theme.SPACE_LG
        )
        root.setSpacing(theme.SPACE_MD)
        root.addLayout(head)
        root.addLayout(cols, stretch=1)

        self.timeframe.rangeChanged.connect(self._set_range)
        self.refresh()

    def _set_range(self, start: float, end: float) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.start, self.end = self.timeframe.range()
        start, end = self.start, self.end
        events_dicts = transitions.to_event_dicts(
            self.store.events_in_range(start, end)
        )

        # Top applications + where the user goes after leaving each app
        apps = self.store.top_apps_in_range(start, end, limit=12)
        self.apps_table.setRowCount(len(apps))
        for i, (name, dur, n) in enumerate(apps):
            nxt, _total = transitions.top_next_for_app(events_dicts, name)
            cells = (name, _fmt_dur(dur), str(n), transitions.format_next(nxt))
            for j, text in enumerate(cells):
                self.apps_table.setItem(i, j, QTableWidgetItem(text))

        # Sites + where the user goes after leaving each site
        sites = self.store.top_domains_in_range(start, end, limit=12)
        self.sites_table.setRowCount(len(sites))
        for i, (domain, dur, n) in enumerate(sites):
            nxt, _total = transitions.top_next(events_dicts, domain)
            cells = (domain, _fmt_dur(dur), str(n), transitions.format_next(nxt))
            for j, text in enumerate(cells):
                self.sites_table.setItem(i, j, QTableWidgetItem(text))

        # Exact pages / documents
        pages = self.store.top_titles_in_range(start, end, limit=15)
        self.pages_table.setRowCount(len(pages))
        for i, (app, title, dur, _n) in enumerate(pages):
            for j, text in enumerate((app, title, _fmt_dur(dur))):
                self.pages_table.setItem(i, j, QTableWidgetItem(text))

        # Switches per hour
        switches = self.store.switches_in_range(start, end)
        per_hour: dict[int, int] = {}
        for (ts, *_rest) in switches:
            h = datetime.fromtimestamp(ts).hour
            per_hour[h] = per_hour.get(h, 0) + 1
        hours = sorted(per_hour)
        self.hours_table.setRowCount(len(hours))
        for i, h in enumerate(hours):
            self.hours_table.setItem(i, 0, QTableWidgetItem(f"{h:02d}:00"))
            self.hours_table.setItem(i, 1, QTableWidgetItem(str(per_hour[h])))


def _fmt_dur(s: float) -> str:
    s = int(s)
    if s >= 3600:
        return f"{s // 3600}h {(s % 3600) // 60}m"
    if s >= 60:
        return f"{s // 60}m {s % 60}s"
    return f"{s}s"
