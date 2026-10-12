"""EKG / seismograph-style attention-fragmentation trace.

Renders the day's context switches as a cardiac-monitor strip: a calm
baseline that spikes sharply at each frontmost-app switch, with amplitude
shaped by the bucketed switches-per-minute series. A playhead sweeps the
trace during replay.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class SeismographWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._series: list[tuple[float, float]] = []  # (bucket_ts, switches/min)
        self._spikes: list[float] = []                # exact switch timestamps
        self._start = 0.0
        self._end = 1.0
        self._playhead: Optional[float] = None

    # ------------------------------------------------------------------ data

    def set_data(
        self,
        series: Sequence[tuple[float, float]],
        spikes: Sequence[float],
        start: float,
        end: float,
    ) -> None:
        self._series = list(series)
        self._spikes = sorted(spikes)
        self._start, self._end = start, max(end, start + 1)
        self.update()

    def set_playhead(self, ts: Optional[float]) -> None:
        self._playhead = ts
        self.update()

    # ------------------------------------------------------------------ paint

    def _x(self, ts: float, w: float) -> float:
        return (ts - self._start) / (self._end - self._start) * w

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        base = h * 0.62
        max_rate = max([r for _, r in self._series] + [1.0])

        # background
        p.fillRect(self.rect(), QColor(30, 30, 32))

        # hourly grid
        p.setPen(QPen(QColor(70, 70, 74), 1))
        hour = 3600.0
        t = math.ceil(self._start / hour) * hour
        while t < self._end:
            x = self._x(t, w)
            p.drawLine(QPointF(x, 8), QPointF(x, h - 8))
            t += hour
        p.setPen(QPen(QColor(90, 90, 96), 1, Qt.DashLine))
        p.drawLine(QPointF(0, base), QPointF(w, base))

        # EKG trace: baseline + QRS-like spikes at each switch, amplitude
        # modulated by the bucketed fragmentation rate.
        p.setPen(QPen(QColor(48, 209, 88), 2))  # macOS systemGreen
        path = QPainterPath(QPointF(0, base))
        i = 0
        spikes = self._spikes
        for ts, rate in self._series:
            x = self._x(ts, w)
            while i < len(spikes) and spikes[i] < ts:
                sx = self._x(spikes[i], w)
                amp = 24 + 10 * rate / max_rate
                path.lineTo(QPointF(sx - 4, base))
                path.lineTo(QPointF(sx, base - amp))   # R peak
                path.lineTo(QPointF(sx + 3, base + amp * 0.35))
                path.lineTo(QPointF(sx + 6, base))
                i += 1
            path.lineTo(QPointF(x, base - rate / max_rate * h * 0.35))
        while i < len(spikes):
            sx = self._x(spikes[i], w)
            path.lineTo(QPointF(sx - 4, base))
            path.lineTo(QPointF(sx, base - 24))
            path.lineTo(QPointF(sx + 3, base + 8))
            path.lineTo(QPointF(sx + 6, base))
            i += 1
        path.lineTo(QPointF(w, base))
        p.drawPath(path)

        # playhead
        if self._playhead is not None and self._start <= self._playhead <= self._end:
            x = self._x(self._playhead, w)
            p.setPen(QPen(QColor(255, 69, 58), 2))  # macOS systemRed
            p.drawLine(QPointF(x, 6), QPointF(x, h - 6))
        p.end()
