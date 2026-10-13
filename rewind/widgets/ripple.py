"""Pond-ripple / raindrop replay canvas.

The replay surface of the app: a dark, still pond. As the replay playhead
crosses the window, each active block (and therefore each context switch,
since every switch opens a block) drops a ripple at its moment on the
timeline. Rings expand outward and fade to nothing; the app or domain
label sits centered on the ring.

Weighting follows dwell: a long, continuous focus session lands as a wide,
slow ring; a sub-30-second check is a small droplet that dissipates
quickly. Scrubbing backwards removes ripples whose moment is still ahead
of the playhead, so seeking re-plays causally. Colors come exclusively
from rewind.theme tokens — one accent, hairline strokes, muted type.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .. import theme

BRIEF_S = 30.0          # under this dwell a block is a droplet, not a ring
HEAVY_S = 900.0         # dwell saturating the size/speed scale (15 min)
MIN_LIFE_S = 1.5        # ring fade window bounds
MAX_LIFE_S = 2.5


@dataclass
class _Ripple:
    x_frac: float
    y_frac: float
    born: float            # monotonic seconds
    life: float
    max_r: float
    label: str
    droplet: bool
    block_i: int


@dataclass
class _Block:
    ts: float
    dwell: float
    label: str


class RippleWidget(QWidget):
    """QPainter canvas animating attention as expanding pond ripples."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self._blocks: list[_Block] = []
        self._start = 0.0
        self._end = 1.0
        self._playhead: Optional[float] = None
        self._ripples: list[_Ripple] = []
        self._spawned = 0  # blocks with index < _spawned already dropped
        self._anim = QTimer(self)
        self._anim.setInterval(16)  # ~60 fps
        self._anim.timeout.connect(self.update)

    # ------------------------------------------------------------------ data

    def set_data(
        self,
        blocks: Sequence[tuple[float, float, str]],
        start: float,
        end: float,
    ) -> None:
        """``blocks`` are (ts, dwell_seconds, label) sorted by ts."""
        self._blocks = sorted(
            (_Block(ts, dwell, label) for ts, dwell, label in blocks),
            key=lambda b: b.ts,
        )
        self._start, self._end = start, max(end, start + 1)
        self._ripples.clear()
        self._spawned = 0
        self._playhead = None
        self._anim.stop()
        self.update()

    def set_playhead(self, ts: Optional[float]) -> None:
        if ts is None:
            self._ripples.clear()
            self._spawned = 0
            self._playhead = None
            self._anim.stop()
            self.update()
            return
        prev = self._playhead
        self._playhead = ts
        if prev is None or ts < prev:
            # seek backwards / re-arm: drop ripples ahead of the playhead
            self._ripples = [r for r in self._ripples if self._blocks[r.block_i].ts <= ts]
            self._spawned = sum(1 for b in self._blocks[: self._spawned] if b.ts <= ts)
        now = time.monotonic()
        while self._spawned < len(self._blocks) and self._blocks[self._spawned].ts <= ts:
            self._ripples.append(self._make_ripple(self._spawned, now))
            self._spawned += 1
        if self._ripples and not self._anim.isActive():
            self._anim.start()
        self.update()

    # ------------------------------------------------------------- weighting

    def _make_ripple(self, i: int, now: float) -> _Ripple:
        b = self._blocks[i]
        x_frac = (b.ts - self._start) / (self._end - self._start)
        # deterministic scatter across rows so labels rarely collide
        rows = 7
        row = i % rows
        # stable hash so the layout is identical across runs/machines
        h = sum((k + 1) * ord(c) for k, c in enumerate(b.label))
        jitter = ((h % 100) / 100.0 - 0.5) * 0.06
        y_frac = 0.12 + (row + 0.5) / rows * 0.76 + jitter

        if b.dwell < BRIEF_S:
            life = 0.9 + (b.dwell / BRIEF_S) * 0.6          # 0.9–1.5 s
            max_r = 10.0 + (b.dwell / BRIEF_S) * 14.0       # 10–24 px
            return _Ripple(x_frac, y_frac, now, life, max_r, b.label, True, i)
        w = min(b.dwell, HEAVY_S) / HEAVY_S                 # 0..1 weight
        life = MIN_LIFE_S + w * (MAX_LIFE_S - MIN_LIFE_S)   # 1.5–2.5 s
        max_r = 30.0 + w * min(self.height(), 320) * 0.42   # wider for depth
        return _Ripple(x_frac, y_frac, now, life, max_r, b.label, False, i)

    # ------------------------------------------------------------------ paint

    def _x(self, ts: float, w: float) -> float:
        return (ts - self._start) / (self._end - self._start) * w

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(self.rect(), QColor(theme.BG_RAISED))

        # hour grid + labels, same quiet furniture the pond replaces beneath
        p.setPen(QPen(QColor(theme.BORDER), 1))
        hour = 3600.0
        span = self._end - self._start
        step = hour if span > 3 * hour else max(300.0, span / 12)
        t = math.ceil(self._start / step) * step
        marks: list[tuple[float, float]] = []
        while t < self._end:
            x = self._x(t, w)
            p.drawLine(QPointF(x, 10), QPointF(x, h - 24))
            marks.append((x, t))
            t += step
        p.setPen(QColor(theme.TEXT_MUTED))
        for x, ts in marks:
            p.drawText(
                int(x) + 4, h - 8, datetime.fromtimestamp(ts).strftime("%H:%M")
            )

        if not self._blocks:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(
                self.rect(), Qt.AlignCenter, "No activity recorded for this window."
            )
            p.end()
            return

        now = time.monotonic()
        alive: list[_Ripple] = []
        accent = QColor(theme.ACCENT)
        label_color = QColor(theme.TEXT)
        font = QFont(p.font())
        font.setPixelSize(theme.FS_CAPTION)
        p.setFont(font)
        fm = QFontMetricsF(font)

        for r in self._ripples:
            age = now - r.born
            if age >= r.life:
                continue
            alive.append(r)
            t = age / r.life                        # 0..1
            ease = 1.0 - (1.0 - t) ** 3             # fast start, slow drift
            radius = r.max_r * ease
            alpha = 1.0 - t                          # linear fade to zero
            cx, cy = r.x_frac * w, r.y_frac * h

            if r.droplet:
                fill = QColor(accent)
                fill.setAlphaF(0.28 * alpha)
                p.setPen(Qt.NoPen)
                p.setBrush(fill)
                p.drawEllipse(QPointF(cx, cy), max(radius, 1.5), max(radius, 1.5))
                ring = QColor(accent)
                ring.setAlphaF(0.55 * alpha)
                p.setPen(QPen(ring, 1.0))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), radius + 2, radius + 2)
            else:
                for k, scale in enumerate((1.0, 0.62)):
                    ring = QColor(accent)
                    ring.setAlphaF(alpha * (0.75 if k == 0 else 0.35))
                    p.setPen(QPen(ring, 1.2 if k == 0 else 1.0))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(QPointF(cx, cy), radius * scale, radius * scale)

            # label centered on the ring; it fades meaningfully faster
            # than the line so dense bursts don't pile labels up
            if r.label:
                label = r.label
                max_w = 150.0
                if fm.horizontalAdvance(label) > max_w:
                    label = fm.elidedText(label, Qt.ElideRight, max_w)
                label_alpha = max(0.0, 1.0 - t * 1.7) * 0.85
                label_color.setAlphaF(label_alpha)
                p.setPen(label_color)
                tw = fm.horizontalAdvance(label)
                p.drawText(
                    QPointF(cx - tw / 2, cy + fm.ascent() / 2 - 1), label
                )

        self._ripples = alive
        if not alive:
            self._anim.stop()

        # playhead — the one structural mark, kept from the old trace
        if self._playhead is not None and self._start <= self._playhead <= self._end:
            x = self._x(self._playhead, w)
            p.setPen(QPen(QColor(theme.ALERT), 1.6))
            p.drawLine(QPointF(x, 8), QPointF(x, h - 24))
            p.setBrush(QColor(theme.ALERT))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, 8), 3.0, 3.0)
        p.end()
