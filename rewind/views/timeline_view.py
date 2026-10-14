"""Chronological event table for the selected day."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..db import EventStore


class TimelineView(QWidget):
    def __init__(self, store: EventStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.day = date.today()

        title = QLabel("Timeline")
        title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(self.subtitle)

        header = QHBoxLayout()
        header.addLayout(title_col)
        header.addStretch(1)

        rule = QFrame()
        rule.setObjectName("hairlineH")
        rule.setFrameShape(QFrame.HLine)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Application", "Window", "Duration"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 16)
        root.setSpacing(12)
        root.addLayout(header)
        root.addWidget(rule)
        root.addWidget(self.table, stretch=1)

        self.show_day(self.day)

    def show_day(self, day: date) -> None:
        self.day = day
        rows = self.store.events_for_day(day)
        self.subtitle.setText(
            f"{len(rows)} events · {day.strftime('%A, %B %-d')}"
        )
        self.table.setRowCount(len(rows))
        for i, (ts, app, _bid, title, _pid, dur) in enumerate(rows):
            cells = (
                datetime.fromtimestamp(ts).strftime("%H:%M:%S"),
                app or "",
                title or "—",
                self._fmt_dur(dur),
            )
            for j, text in enumerate(cells):
                self.table.setItem(i, j, QTableWidgetItem(text))

    @staticmethod
    def _fmt_dur(s: float) -> str:
        s = int(s)
        if s >= 3600:
            return f"{s // 3600}h {(s % 3600) // 60}m"
        if s >= 60:
            return f"{s // 60}m {s % 60}s"
        return f"{s}s"
