"""EKG / seismograph-style attention-fragmentation trace.

Renders the day's context switches as a cardiac-monitor strip: a calm
baseline that spikes sharply at each frontmost-app switch, with amplitude
shaped by the bucketed switches-per-minute series. Replay has no scrubber:
a minimal monospaced HH:MM watch readout steps rapidly through the day's
clock, and every switch the replay passes emits a radial ripple from the
center of the panel — the destination app's name rides inside it like a
bubble, scaling up on an ease-out curve, holding full opacity, then fading
as the ring expands and dissipates.
Flat colors and 1px hairlines only — no gradients.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Sequence

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..theme import (
    BASE_LINE,
    GRID_LINE,
    RIPPLE,
    TEXT_PRIMARY,
    TEXT_TERTIARY,
    TRACE,
)


RIPPLE_LIFE_MS = 2600      # how long one ripple expands/fades
RIPPLE_TICK_MS = 33        # animation cadence while ripples are alive
LABEL_SCALE_IN = 0.40      # fraction of ripple life the label pops in over
MAX_RIPPLES = 12           # cap concurrent ripples so dense runs stay readable


def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


class SeismographWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._series: list[tuple[float, float]] = []  # (bucket_ts, switches/min)
        self._spikes: list[tuple[float, str]] = []    # (switch_ts, to_app)
        self._start = 0.0
        self._end = 1.0
        self._clock_ts: Optional[float] = None        # replay clock position

        self._clock = QElapsedTimer()
        self._clock.start()
        self._ripples: list[tuple[float, str]] = []  # (born_ms, app_name)
        self._ripple_timer = QTimer(self)
        self._ripple_timer.setInterval(RIPPLE_TICK_MS)
        self._ripple_timer.timeout.connect(self._age_ripples)

    # ------------------------------------------------------------------ data

    def set_data(
        self,
        series: Sequence[tuple[float, float]],
        spikes: Sequence[tuple[float, Optional[str]]],
        start: float,
        end: float,
    ) -> None:
        self._series = list(series)
        self._spikes = sorted((ts, name or "") for ts, name in spikes)
        self._start, self._end = start, max(end, start + 1)
        self.update()

    def set_replay_position(self, ts: Optional[float]) -> None:
        """Move the replay clock; each switch crossed spawns a ripple."""
        if ts is None:
            self._ripples.clear()
            self._ripple_timer.stop()
        else:
            prev = self._clock_ts
            if prev is not None and ts > prev:
                now = self._clock.elapsed()
                for s, name in self._spikes:
                    if prev < s <= ts:
                        self._ripples.append((now, name))
                del self._ripples[:-MAX_RIPPLES]
            if not self._ripple_timer.isActive():
                self._ripple_timer.start()
        self._clock_ts = ts
        self.update()

    def _age_ripples(self) -> None:
        now = self._clock.elapsed()
        self._ripples = [
            (born, name) for born, name in self._ripples
            if now - born < RIPPLE_LIFE_MS
        ]
        if not self._ripples and self._clock_ts is None:
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
        spikes = [ts for ts, _ in self._spikes]
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

        # ripples: flat hairline rings expanding radially from the panel's
        # center — one per switch the replay has crossed. Each carries the
        # destination app's name as a bubble label that pops in on an
        # ease-out curve, holds full opacity, then fades as the ring
        # expands and dissipates (no gradients, just stroked rings).
        center = QPointF(x0 + w / 2.0, y0 + plot_h / 2.0)
        if self._ripples:
            now = self._clock.elapsed()
            max_r = math.hypot(w, plot_h) * 0.38
            p.setBrush(Qt.NoBrush)
            n_live = len(self._ripples)
            for idx, (born, name) in enumerate(self._ripples):
                age = (now - born) / RIPPLE_LIFE_MS
                if age < 0 or age > 1:
                    continue
                r = 8.0 + _ease_out_cubic(age) * max_r
                color = QColor(RIPPLE)
                color.setAlpha(int(180 * (1 - age)))
                p.setPen(QPen(color, 1.2))
                p.drawEllipse(center, r, r)
                color.setAlpha(int(85 * (1 - age)))
                p.setPen(QPen(color, 1.0))
                p.drawEllipse(center, r * 0.62, r * 0.62)
                if name:
                    scale = 0.5 + 0.5 * _ease_out_cubic(
                        min(age / LABEL_SCALE_IN, 1.0)
                    )
                    alpha = int(
                        255 * min(age / 0.15, 1.0)
                        * min((1.0 - age) / 0.45, 1.0)
                    )
                    label_font = p.font()
                    label_font.setPointSizeF(12.0)
                    label_font.setBold(True)
                    # fan concurrent labels apart so each stays readable
                    dy = (idx - (n_live - 1) / 2.0) * 26.0
                    p.setFont(label_font)
                    p.save()
                    p.translate(center.x(), center.y() + dy)
                    p.scale(scale, scale)
                    color = QColor(TEXT_PRIMARY)
                    color.setAlpha(alpha)
                    p.setPen(color)
                    p.drawText(
                        QRectF(-w / 2.0, -12, w, 24),
                        Qt.AlignCenter,
                        name,
                    )
                    p.restore()

        # digital watch readout: while replaying, a monospaced HH:MM steps
        # through the day's clock — replaces the old linear scrubber head.
        if self._clock_ts is not None:
            clock_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            clock_font.setPointSizeF(15.0)
            p.setFont(clock_font)
            color = QColor(TEXT_PRIMARY)
            color.setAlpha(220)
            p.setPen(color)
            p.drawText(
                QRectF(x0, y0 + 4, w, 22),
                Qt.AlignHCenter | Qt.AlignTop,
                datetime.fromtimestamp(self._clock_ts).strftime("%H:%M"),
            )
        p.end()
