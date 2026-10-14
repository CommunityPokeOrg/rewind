"""EKG / seismograph-style attention-fragmentation trace.

Renders the day's context switches as a cardiac-monitor strip: a calm
baseline that spikes sharply at each frontmost-app switch, with amplitude
shaped by the bucketed switches-per-minute series. A playhead sweeps the
trace during replay. Flat colors and 1px hairlines only — no gradients.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..theme import (
    BASE_LINE,
    GRID_LINE,
    PLAYHEAD,
    TEXT_TERTIARY,
    TRACE,
)


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

        # paint inside the stylesheet's hairline border + padding
        area = self.contentsRect().adjusted(10, 8, -10, -8)
        x0, y0 = area.left(), area.top()
        w, h = area.width(), area.height()
        label_h = 14                      # strip reserved for hour labels
        plot_h = h - label_h
        base = y0 + plot_h * 0.62
        max_rate = max([r for _, r in self._series] + [1.0])

        # hourly hairline grid + hour labels every 3 h
        label_font = p.font()
        label_font.setPointSizeF(8.0)
        p.setFont(label_font)
        hour = 3600.0
        t = math.ceil(self._start / hour) * hour
        while t < self._end:
            x = x0 + self._x(t, w)
            p.setPen(QPen(GRID_LINE, 1))
            p.drawLine(QPointF(x, y0 + 2), QPointF(x, y0 + plot_h - 2))
            h_of_day = datetime.fromtimestamp(t).hour
            if h_of_day % 3 == 0:
                p.setPen(QColor(TEXT_TERTIARY))
                p.drawText(
                    QRectF(x - 20, y0 + plot_h + 2, 40, label_h),
                    Qt.AlignHCenter | Qt.AlignTop,
                    f"{h_of_day % 12 or 12}{'a' if h_of_day < 12 else 'p'}",
                )
            t += hour
        p.setPen(QPen(BASE_LINE, 1, Qt.DashLine))
        p.drawLine(QPointF(x0, base), QPointF(x0 + w, base))

        if not self._spikes and not any(r for _, r in self._series):
            p.setPen(QColor(TEXT_TERTIARY))
            f = p.font()
            f.setPointSizeF(10.0)
            p.setFont(f)
            p.drawText(
                QRectF(x0, y0, w, plot_h),
                Qt.AlignCenter,
                "No activity recorded",
            )
            p.end()
            return

        # EKG trace: baseline + QRS-like spikes at each switch, amplitude
        # modulated by the bucketed fragmentation rate.
        p.setPen(QPen(QColor(TRACE), 1.8))
        path = QPainterPath(QPointF(x0, base))
        i = 0
        spikes = self._spikes
        for ts, rate in self._series:
            x = x0 + self._x(ts, w)
            while i < len(spikes) and spikes[i] < ts:
                sx = x0 + self._x(spikes[i], w)
                amp = 24 + 10 * rate / max_rate
                path.lineTo(QPointF(sx - 4, base))
                path.lineTo(QPointF(sx, base - amp))   # R peak
                path.lineTo(QPointF(sx + 3, base + amp * 0.35))
                path.lineTo(QPointF(sx + 6, base))
                i += 1
            path.lineTo(QPointF(x, base - rate / max_rate * plot_h * 0.35))
        while i < len(spikes):
            sx = x0 + self._x(spikes[i], w)
            path.lineTo(QPointF(sx - 4, base))
            path.lineTo(QPointF(sx, base - 24))
            path.lineTo(QPointF(sx + 3, base + 8))
            path.lineTo(QPointF(sx + 6, base))
            i += 1
        path.lineTo(QPointF(x0 + w, base))
        p.drawPath(path)

        # playhead
        if self._playhead is not None and self._start <= self._playhead <= self._end:
            x = x0 + self._x(self._playhead, w)
            p.setPen(QPen(QColor(PLAYHEAD), 1.5))
            p.drawLine(QPointF(x, y0 + 2), QPointF(x, y0 + plot_h - 2))
            p.setBrush(QColor(PLAYHEAD))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, y0 + 4), 3, 3)
        p.end()
