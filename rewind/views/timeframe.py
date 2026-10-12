"""Shared timeframe selector: Last 24h / 12h / 6h / Today.

Emits an [start, end) epoch range; views recompute on ``rangeChanged``.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox

from ..db import day_bounds, last_hours

OPTIONS = [
    ("Last 24 hours", 24),
    ("Last 12 hours", 12),
    ("Last 6 hours", 6),
    ("Today", None),  # None = calendar day bounds
]


class TimeframeSelector(QComboBox):
    rangeChanged = Signal(float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        for label, _hours in OPTIONS:
            self.addItem(label)
        self.setCurrentIndex(0)
        self.currentIndexChanged.connect(self._emit)

    def range(self) -> tuple[float, float]:
        hours = OPTIONS[self.currentIndex()][1]
        if hours is None:
            return day_bounds(date.today())
        return last_hours(hours)

    def window_seconds(self) -> float:
        """Length of the current window — used for ‹ › stepping."""
        start, end = self.range()
        return end - start

    def _emit(self, _index: int) -> None:
        start, end = self.range()
        self.rangeChanged.emit(start, end)
