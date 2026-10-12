"""EKG / seismograph-style attention-fragmentation trace.

The hero of the app: a cardiac-monitor strip for attention. A quiet
baseline runs across the day; every context switch fires one sharp
QRS-like spike whose height follows the local switches-per-minute rate.
During replay a playhead sweeps the trace. Colors come exclusively from
rewind.theme tokens.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .. import theme


class SeismographWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self._series: list[tuple[float, float]] = []  # (bucket_ts, switches/min)
        self._spikes: list[float] = []                # exact switch timestamps
        self._start = 0.0
        self._end = 1.0
        self._playhead: Optional[float] = None
        self._empty = True

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
        self._empty = not self._series and not self._spikes
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
        base = h * 0.60

        p.fillRect(self.rect(), QColor(theme.BG_RAISED))

        # hourly grid + hour labels in muted type
        p.setPen(QPen(QColor(theme.BORDER), 1))
        hour = 3600.0
        t = math.ceil(self._start / hour) * hour
        hours: list[tuple[float, int]] = []
        while t < self._end:
            x = self._x(t, w)
            p.drawLine(QPointF(x, 10), QPointF(x, h - 24))
            hours.append((x, int(t // hour) % 24))
            t += hour
        p.setPen(QColor(theme.TEXT_MUTED))
        for x, hr in hours:
            p.drawText(int(x) + 4, h - 8, f"{hr:02d}:00")

        # baseline
        p.setPen(QPen(QColor(theme.BORDER_STRONG), 1, Qt.DashLine))
        p.drawLine(QPointF(0, base), QPointF(w, base))

        if self._empty:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(
                self.rect(),
                Qt.AlignCenter,
                "No activity recorded for this day.",
            )
            p.end()
            return

        max_rate = max([r for _, r in self._series] + [1.0])

        # EKG trace: baseline + one QRS complex per switch, amplitude scaled
        # by local fragmentation; a thin rate line threads the buckets.
        trace_pen = QPen(QColor(theme.ACCENT), 1.8)
        trace_pen.setCapStyle(Qt.RoundCap)
        trace_pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(trace_pen)

        path = QPainterPath(QPointF(0, base))
        i = 0
        for ts, rate in self._series:
            x = self._x(ts, w)
            y = base - rate / max_rate * h * 0.30
            while i < len(self._spikes) and self._spikes[i] < ts:
                sx = self._x(self._spikes[i], w)
                amp = 18 + 26 * rate / max_rate
                path.lineTo(QPointF(sx - 5, base))
                path.lineTo(QPointF(sx - 2, base + 4))    # small P wave
                path.lineTo(QPointF(sx, base - amp))      # R peak
                path.lineTo(QPointF(sx + 2, base + amp * 0.4))
                path.lineTo(QPointF(sx + 5, base))
                i += 1
            path.lineTo(QPointF(x, y))
        while i < len(self._spikes):
            sx = self._x(self._spikes[i], w)
            path.lineTo(QPointF(sx - 5, base))
            path.lineTo(QPointF(sx, base - 22))
            path.lineTo(QPointF(sx + 2, base + 8))
            path.lineTo(QPointF(sx + 5, base))
            i += 1
        path.lineTo(QPointF(w, base))
        p.drawPath(path)

        # playhead — the one piece of motion, justified by replay state
        if self._playhead is not None and self._start <= self._playhead <= self._end:
            x = self._x(self._playhead, w)
            p.setPen(QPen(QColor(theme.ALERT), 1.6))
            p.drawLine(QPointF(x, 8), QPointF(x, h - 24))
            p.setBrush(QColor(theme.ALERT))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, 8), 3.0, 3.0)
        p.end()
