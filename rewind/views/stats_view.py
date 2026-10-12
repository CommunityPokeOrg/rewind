"""Per-day stats: top apps by dwell and switches per hour."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..db import EventStore


class StatsView(QWidget):
    def __init__(self, store: EventStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.day = date.today()

        self.apps_label = QLabel("Top applications")
        self.apps_label.setObjectName("sectionLabel")
        self.apps_table = QTableWidget(0, 3)
        self.apps_table.setHorizontalHeaderLabels(["Application", "Time", "Samples"])
        self.apps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.apps_table.verticalHeader().setVisible(False)
        self.apps_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.hours_label = QLabel("Context switches per hour")
        self.hours_label.setObjectName("sectionLabel")
        self.hours_table = QTableWidget(0, 2)
        self.hours_table.setHorizontalHeaderLabels(["Hour", "Switches"])
        self.hours_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.hours_table.verticalHeader().setVisible(False)
        self.hours_table.setEditTriggers(QTableWidget.NoEditTriggers)

        root = QVBoxLayout(self)
        root.addWidget(self.apps_label)
        root.addWidget(self.apps_table, stretch=1)
        root.addWidget(self.hours_label)
        root.addWidget(self.hours_table, stretch=1)

        self.show_day(self.day)

    def show_day(self, day: date) -> None:
        self.day = day

        apps = self.store.top_apps(day, limit=15)
        self.apps_table.setRowCount(len(apps))
        for i, (name, dur, n) in enumerate(apps):
            for j, text in enumerate((name, _fmt_dur(dur), str(n))):
                self.apps_table.setItem(i, j, QTableWidgetItem(text))

        switches = self.store.switches_for_day(day)
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
