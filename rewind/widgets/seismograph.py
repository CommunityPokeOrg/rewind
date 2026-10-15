"""EKG / seismograph-style attention-fragmentation trace.

Renders the day's context switches as a cardiac-monitor strip: a calm
baseline that spikes sharply at each frontmost-app switch, with amplitude
shaped by the bucketed switches-per-minute series. A playhead sweeps the
trace during replay. As the replay playhead sweeps past each switch, the
spike emits an expanding hairline ripple — the "ripple effect" that marks
where attention broke. Flat colors and 1px hairlines only — no gradients.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Sequence

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..theme import (
    BASE_LINE,
    GRID_LINE,
    PLAYHEAD,
    TEXT_TERTIARY,
    TRACE,
)


RIPPLE_LIFE_MS = 2600      # how long one ripple expands/fades
RIPPLE_TICK_MS = 33        # animation cadence while ripples are alive


class SeismographWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._series: list[tuple[float, float]] = []  # (bucket_ts, switches/min)
        self._spikes: list[float] = []                # exact switch timestamps
        self._start = 0.0
        self._end = 1.0
        self._playhead: Optional[float] = None

        self._clock = QElapsedTimer()
        self._clock.start()
        self._ripples: list[tuple[float, float]] = []  # (spike_ts, born_ms)
        self._ripple_timer = QTimer(self)
        self._ripple_timer.setInterval(RIPPLE_TICK_MS)
        self._ripple_timer.timeout.connect(self._age_ripples)

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
        if ts is None:
            self._ripples.clear()
            self._ripple_timer.stop()
        else:
            prev = self._playhead
            if prev is not None and ts > prev:
                now = self._clock.elapsed()
                for s in self._spikes:
                    if prev < s <= ts:
                        self._ripples.append((s, now))
            if not self._ripple_timer.isActive():
                self._ripple_timer.start()
        self._playhead = ts
        self.update()

    def _age_ripples(self) -> None:
        now = self._clock.elapsed()
        self._ripples = [
            (ts, born) for ts, born in self._ripples
            if now - born < RIPPLE_LIFE_MS
        ]
        if not self._ripples and self._playhead is None:
            self._ripple_timer.stop()
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

        # ripples: flat hairline ellipses expanding from each switch the
        # playhead has crossed — alpha fades as the ring grows (no gradients,
        # just a single stroked ring per ripple).
        if self._ripples:
            now = self._clock.elapsed()
            p.setBrush(Qt.NoBrush)
            for ts, born in self._ripples:
                age = (now - born) / RIPPLE_LIFE_MS
                if age < 0 or age > 1:
                    continue
                center = QPointF(x0 + self._x(ts, w), base)
                rx = 6.0 + age * 44.0
                color = QColor(PLAYHEAD)
                color.setAlpha(int(190 * (1 - age)))
                p.setPen(QPen(color, 1.2))
                p.drawEllipse(center, rx, rx * 0.34)
                color.setAlpha(int(90 * (1 - age)))
                p.setPen(QPen(color, 1.0))
                p.drawEllipse(center, rx * 0.6, rx * 0.2)

        # playhead + its continuous ripple pulse (sonar ping at the sweep
        # point, two rings offset half a cycle so one is always expanding)
        if self._playhead is not None and self._start <= self._playhead <= self._end:
            x = x0 + self._x(self._playhead, w)
            now = self._clock.elapsed()
            p.setBrush(Qt.NoBrush)
            for offset in (0.0, 0.5):
                phase = ((now + offset * 700.0) % 700.0) / 700.0
                rr = 5.0 + phase * 30.0
                color = QColor(PLAYHEAD)
                color.setAlpha(int(150 * (1 - phase)))
                p.setPen(QPen(color, 1.0))
                p.drawEllipse(QPointF(x, base), rr, rr * 0.34)
            p.setPen(QPen(QColor(PLAYHEAD), 1.5))
            p.drawLine(QPointF(x, y0 + 2), QPointF(x, y0 + plot_h - 2))
            p.setBrush(QColor(PLAYHEAD))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, y0 + 4), 3, 3)
        p.end()
