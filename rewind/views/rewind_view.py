"""Daily rewind view — the EKG replay of an attention window.

Layout: a quiet nav strip (‹ › window stepping + timeframe selector),
the hero seismograph, then a divided metric strip. All visual decisions
come from rewind.theme tokens.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..db import EventStore, day_bounds
from ..switches import fragmentation_series
from ..widgets import SeismographWidget
from .timeframe import TimeframeSelector


def _metric(value: str, label: str) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.SPACE_XS)
    v = QLabel(value)
    v.setObjectName("metricValue")
    l = QLabel(label)
    l.setObjectName("metricLabel")
    lay.addWidget(v)
    lay.addWidget(l)
    box.value_label = v  # refreshed on refresh()
    return box


class RewindView(QWidget):
    def __init__(self, store: EventStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.start, self.end = 0.0, 1.0
        self._offset = 0.0  # ‹ › stepping, applied to the anchored window
        self._replay_ts: float | None = None

        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setToolTip("Step back one window")
        self.next_btn = QPushButton("›")
        self.next_btn.setToolTip("Step forward one window")
        self.timeframe = TimeframeSelector()
        self.replay_btn = QPushButton("Replay")
        self.replay_btn.setProperty("accent", True)

        nav = QHBoxLayout()
        nav.setSpacing(theme.SPACE_SM)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.timeframe)
        nav.addStretch(1)
        nav.addWidget(self.date_label)
        nav.addStretch(1)
        nav.addWidget(self.replay_btn)

        self.seismograph = SeismographWidget()

        self.m_tracked = _metric("0.0 h", "Tracked")
        self.m_switches = _metric("0", "Context switches")
        self.m_rate = _metric("0.0", "Switches / hour")
        self.m_top = _metric("None", "Most time in")
        metrics = QHBoxLayout()
        metrics.setSpacing(theme.SPACE_XL)
        for i, m in enumerate((self.m_tracked, self.m_switches, self.m_rate, self.m_top)):
            if i:
                div = QFrame()
                div.setObjectName("metricDivider")
                div.setFrameShape(QFrame.VLine)
                metrics.addWidget(div)
            metrics.addWidget(m, stretch=1)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            theme.SPACE_LG, theme.SPACE_MD, theme.SPACE_LG, theme.SPACE_LG
        )
        root.setSpacing(theme.SPACE_MD)
        root.addLayout(nav)
        root.addWidget(self.seismograph, stretch=1)
        root.addLayout(metrics)

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick_replay)

        self.prev_btn.clicked.connect(lambda: self._shift_window(-1))
        self.next_btn.clicked.connect(lambda: self._shift_window(+1))
        self.timeframe.rangeChanged.connect(self._set_range)
        self.replay_btn.clicked.connect(self._toggle_replay)

        self.refresh()

    # ------------------------------------------------------------------ range

    def _set_range(self, start: float, end: float) -> None:
        self._offset = 0.0
        self.refresh()

    def _shift_window(self, direction: int) -> None:
        self._offset += direction * self.timeframe.window_seconds()
        self.refresh()

    def refresh(self) -> None:
        """Recompute the visible window from the store."""
        base_start, base_end = self.timeframe.range()
        self.start, self.end = base_start + self._offset, base_end + self._offset
        start, end = self.start, self.end
        self._stop_replay()
        self.date_label.setText(self._range_label(start, end))

        switches = self.store.switches_in_range(start, end)
        spike_times = [s[0] for s in switches]
        bucket_s = max(60.0, (end - start) / 240)
        series = fragmentation_series(spike_times, start, end, bucket_s=bucket_s)
        self.seismograph.set_data(series, spike_times, start, end)

        tracked = self.store.tracked_seconds_in_range(start, end)
        n = len(switches)
        rate = n / (tracked / 3600.0) if tracked > 0 else 0.0
        top = self.store.top_apps_in_range(start, end, limit=1)
        self.m_tracked.value_label.setText(f"{tracked / 3600.0:.1f} h")
        self.m_switches.value_label.setText(str(n))
        self.m_rate.value_label.setText(f"{rate:.1f}")
        self.m_top.value_label.setText(top[0][0] if top else "None")

    @staticmethod
    def _range_label(start: float, end: float) -> str:
        s, e = datetime.fromtimestamp(start), datetime.fromtimestamp(end)
        today_start, today_end = day_bounds(s.date())
        if start == today_start and end == today_end:
            return s.strftime("%A, %B %-d, %Y")
        if s.date() == e.date():
            return s.strftime("%b %-d, %H:%M") + " to " + e.strftime("%H:%M")
        return (
            s.strftime("%b %-d, %H:%M")
            + " to "
            + e.strftime("%b %-d, %H:%M")
        )

    # ----------------------------------------------------------------- replay

    def _toggle_replay(self) -> None:
        if self._timer.isActive():
            self._stop_replay()
        else:
            self._replay_ts = self.start
            self.replay_btn.setText("Stop")
            self._timer.start()

    def _stop_replay(self) -> None:
        self._timer.stop()
        self._replay_ts = None
        self.replay_btn.setText("Replay")
        self.seismograph.set_playhead(None)

    def _tick_replay(self) -> None:
        span = self.end - self.start
        step = span / 600.0  # ~30 s sweep for any window
        self._replay_ts = (self._replay_ts or self.start) + step
        if self._replay_ts >= self.end:
            self._stop_replay()
            return
        self.seismograph.set_playhead(self._replay_ts)
