"""Daily rewind view — the EKG replay of a day's attention."""

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

from ..db import EventStore, day_bounds
from ..switches import fragmentation_series
from ..widgets import SeismographWidget

REPLAY_MS_PER_SECOND_OF_DAY = 4  # a full day replays in ~5.8 minutes


class RewindView(QWidget):
    """Seismograph trace + day navigation + replay controls + day summary."""

    def __init__(self, store: EventStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.day = date.today()
        self._replay_ts: float | None = None

        title = QLabel("Rewind")
        title.setObjectName("pageTitle")
        self.date_label = QLabel()
        self.date_label.setObjectName("pageSubtitle")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(self.date_label)

        self.prev_btn = QPushButton("‹")
        self.prev_btn.setObjectName("navButton")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.setToolTip("Previous day")
        self.next_btn = QPushButton("›")
        self.next_btn.setObjectName("navButton")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.setToolTip("Next day")
        self.today_btn = QPushButton("Today")
        self.replay_btn = QPushButton("Replay day")
        self.replay_btn.setProperty("accent", True)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addLayout(title_col)
        header.addStretch(1)
        header.addWidget(self.prev_btn)
        header.addWidget(self.next_btn)
        header.addWidget(self.today_btn)
        header.addWidget(self.replay_btn)

        rule = QFrame()
        rule.setObjectName("hairlineH")
        rule.setFrameShape(QFrame.HLine)

        self.seismograph = SeismographWidget()
        self.seismograph.setObjectName("chartPanel")

        self.summary_label = QLabel()
        self.summary_label.setObjectName("summaryLabel")

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 16)
        root.setSpacing(12)
        root.addLayout(header)
        root.addWidget(rule)
        root.addWidget(self.seismograph, stretch=1)
        root.addWidget(self.summary_label)

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
        spikes = [(s[0], s[4]) for s in switches]  # (ts, to_app)
        self.seismograph.set_data(series, spikes, start, end)

        tracked = self.store.tracked_seconds(day)
        n = len(switches)
        rate = n / (tracked / 3600.0) if tracked > 0 else 0.0
        top = self.store.top_apps(day, limit=1)
        top_txt = f" · most time in {top[0][0]}" if top else ""
        self.summary_label.setText(
            f"{tracked / 3600.0:.1f} h tracked · {n} context switches"
            f" · {rate:.1f} switches/h{top_txt}"
        )

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
        self.seismograph.set_replay_position(None)

    def _tick_replay(self) -> None:
        start, end = day_bounds(self.day)
        step = (50 / 1000.0) / (REPLAY_MS_PER_SECOND_OF_DAY / 1000.0)
        self._replay_ts = (self._replay_ts or start) + step
        if self._replay_ts >= end:
            self._stop_replay()
            return
        self.seismograph.set_replay_position(self._replay_ts)
