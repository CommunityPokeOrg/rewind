"""Daily rewind view — the EKG replay of a day's attention.

Layout: a quiet nav strip, the hero seismograph, then a divided metric
strip (spacing and hairlines, no card chrome). All visual decisions come
from rewind.theme tokens.
"""

from __future__ import annotations

from datetime import date, timedelta

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

REPLAY_MS_PER_SECOND_OF_DAY = 4  # a full day replays in ~5.8 minutes


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
    box.value_label = v  # refreshed on show_day
    return box


class RewindView(QWidget):
    def __init__(self, store: EventStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.day = date.today()
        self._replay_ts: float | None = None

        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setToolTip("Previous day")
        self.next_btn = QPushButton("›")
        self.next_btn.setToolTip("Next day")
        self.today_btn = QPushButton("Today")
        self.replay_btn = QPushButton("Replay day")
        self.replay_btn.setProperty("accent", True)

        nav = QHBoxLayout()
        nav.setSpacing(theme.SPACE_SM)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.today_btn)
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

        self.prev_btn.clicked.connect(lambda: self._shift_day(-1))
        self.next_btn.clicked.connect(lambda: self._shift_day(+1))
        self.today_btn.clicked.connect(self._go_today)
        self.replay_btn.clicked.connect(self._toggle_replay)

        self.show_day(self.day)

    # ------------------------------------------------------------------ days

    def _shift_day(self, delta: int) -> None:
        self.show_day(self.day + timedelta(days=delta))

    def _go_today(self) -> None:
        self.show_day(date.today())

    def show_day(self, day: date) -> None:
        self.day = day
        self._stop_replay()
        self.date_label.setText(day.strftime("%A, %B %-d, %Y"))

        switches = self.store.switches_for_day(day)
        start, end = day_bounds(day)
        spike_times = [s[0] for s in switches]
        series = fragmentation_series(spike_times, start, end, bucket_s=300)
        self.seismograph.set_data(series, spike_times, start, end)

        tracked = self.store.tracked_seconds(day)
        n = len(switches)
        rate = n / (tracked / 3600.0) if tracked > 0 else 0.0
        top = self.store.top_apps(day, limit=1)
        self.m_tracked.value_label.setText(f"{tracked / 3600.0:.1f} h")
        self.m_switches.value_label.setText(str(n))
        self.m_rate.value_label.setText(f"{rate:.1f}")
        self.m_top.value_label.setText(top[0][0] if top else "None")

    # ----------------------------------------------------------------- replay

    def _toggle_replay(self) -> None:
        if self._timer.isActive():
            self._stop_replay()
        else:
            start, _ = day_bounds(self.day)
            self._replay_ts = start
            self.replay_btn.setText("Stop replay")
            self._timer.start()

    def _stop_replay(self) -> None:
        self._timer.stop()
        self._replay_ts = None
        self.replay_btn.setText("Replay day")
        self.seismograph.set_playhead(None)

    def _tick_replay(self) -> None:
        start, end = day_bounds(self.day)
        step = (50 / 1000.0) / (REPLAY_MS_PER_SECOND_OF_DAY / 1000.0)
        self._replay_ts = (self._replay_ts or start) + step
        if self._replay_ts >= end:
            self._stop_replay()
            return
        self.seismograph.set_playhead(self._replay_ts)
