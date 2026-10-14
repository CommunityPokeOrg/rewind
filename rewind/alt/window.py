"""Ledger window — the alternate UI for Rewind.

One ruled page instead of tabs: a masthead, the nav strip, the pond
viewport (the same RippleWidget the main window replays on, kept dark
inside a paper frame), a scrubber, then the day's session log beside a
tally rail. No existing widget files are touched — this window reuses
RippleWidget, TimeframeSelector, TrackerWorker and the store as they are.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import transitions
from ..db import EventStore, day_bounds
from ..views.timeframe import TimeframeSelector
from ..widgets import RippleWidget
from ..workers import TrackerWorker
from . import theme

SCRUB_STEPS = 1000


def _rule(vertical: bool = False) -> QFrame:
    line = QFrame()
    line.setObjectName("vrule" if vertical else "rule")
    line.setFrameShape(QFrame.VLine if vertical else QFrame.HLine)
    return line


def _dwell(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} s"
    if seconds < 3600:
        return f"{seconds / 60:.0f} m"
    return f"{seconds / 3600:.1f} h"


def _ledger_row(name: str, value: str = "—") -> QFrame:
    """A ruled figure line: name on the left, figure on the right."""
    row = QFrame()
    row.setObjectName("ledgerRow")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 5, 0, 5)
    lay.setSpacing(theme.SPACE_SM)
    n = QLabel(name)
    n.setObjectName("listName")
    v = QLabel(value)
    v.setObjectName("metricValue")
    v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lay.addWidget(n)
    lay.addStretch(1)
    lay.addWidget(v)
    row.value_label = v
    return row


def _list_row(name: str, value: str) -> QFrame:
    """A ruled entry line for the top-apps / top-sites lists."""
    row = QFrame()
    row.setObjectName("ledgerRow")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 4, 0, 4)
    lay.setSpacing(theme.SPACE_SM)
    n = QLabel(name)
    n.setObjectName("listName")
    v = QLabel(value)
    v.setObjectName("listValue")
    v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lay.addWidget(n, stretch=1)
    lay.addWidget(v)
    return row


class AltRewindWindow(QMainWindow):
    def __init__(self, store: EventStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rewind — day ledger")
        self.resize(1100, 720)
        self.store = store
        self.start, self.end = 0.0, 1.0
        self._offset = 0.0
        self._replay_ts: float | None = None
        self._scrubbing = False
        self._switches_today = 0

        # --------------------------------------------------------- masthead
        self.toolbar = QToolBar("Ledger", self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        wordmark = QLabel("Rewind — day ledger")
        wordmark.setObjectName("wordmark")
        self.toolbar.addWidget(wordmark)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        self.track_btn = self.toolbar.addAction("Pause tracking")
        self.track_btn.setCheckable(True)
        self.track_btn.toggled.connect(self._toggle_tracking)

        # ------------------------------------------------------------ nav
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setToolTip("Step back one window")
        self.next_btn = QPushButton("›")
        self.next_btn.setToolTip("Step forward one window")
        self.timeframe = TimeframeSelector()
        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
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

        # -------------------------------------------------------- the pond
        self.ripple = RippleWidget()
        self.ripple.setMinimumHeight(300)
        pond_caption = QLabel("pond — one ring per context switch")
        pond_caption.setObjectName("pondCaption")
        pond_lay = QVBoxLayout()
        pond_lay.setContentsMargins(1, 1, 1, 1)
        pond_lay.setSpacing(0)
        pond_lay.addWidget(self.ripple, stretch=1)
        cap_row = QHBoxLayout()
        cap_row.setContentsMargins(10, 0, 10, 6)
        cap_row.addWidget(pond_caption)
        cap_row.addStretch(1)
        pond_lay.addLayout(cap_row)
        pond = QFrame()
        pond.setObjectName("pondFrame")
        pond.setLayout(pond_lay)

        self.scrubber = QSlider(Qt.Horizontal)
        self.scrubber.setRange(0, SCRUB_STEPS)
        self.scrubber.setValue(0)
        self.scrubber.setSingleStep(1)
        self.scrubber.setToolTip("Scrub the replay")
        self.clock = QLabel("—")
        self.clock.setObjectName("clockLabel")
        scrub_row = QHBoxLayout()
        scrub_row.setSpacing(theme.SPACE_SM)
        scrub_row.addWidget(self.scrubber, stretch=1)
        scrub_row.addWidget(self.clock)

        # ------------------------------------------------- the ledger page
        log_label = QLabel("Session log")
        log_label.setObjectName("sectionLabel")
        self.log = QTableWidget(0, 4)
        self.log.setHorizontalHeaderLabels(["Time", "App", "Document", "Time spent"])
        self.log.verticalHeader().setVisible(False)
        self.log.setShowGrid(False)
        self.log.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.log.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.log.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        left = QVBoxLayout()
        left.setSpacing(theme.SPACE_SM)
        left.addWidget(log_label)
        left.addWidget(self.log, stretch=1)

        tally_label = QLabel("Tally")
        tally_label.setObjectName("sectionLabel")
        self.m_tracked = _ledger_row("Tracked")
        self.m_switches = _ledger_row("Context switches")
        self.m_rate = _ledger_row("Switches per hour")
        self.m_top = _ledger_row("Most time in")
        apps_label = QLabel("Top apps")
        apps_label.setObjectName("sectionLabel")
        self.apps_col = QVBoxLayout()
        self.apps_col.setSpacing(0)
        sites_label = QLabel("Top sites")
        sites_label.setObjectName("sectionLabel")
        self.sites_col = QVBoxLayout()
        self.sites_col.setSpacing(0)
        next_label = QLabel("Where you go next")
        next_label.setObjectName("sectionLabel")
        self.next_text = QLabel("—")
        self.next_text.setObjectName("nextLabel")
        self.next_text.setWordWrap(True)
        right = QVBoxLayout()
        right.setSpacing(theme.SPACE_XS)
        right.addWidget(tally_label)
        for m in (self.m_tracked, self.m_switches, self.m_rate, self.m_top):
            right.addWidget(m)
        right.addSpacing(theme.SPACE_MD)
        right.addWidget(apps_label)
        right.addLayout(self.apps_col)
        right.addSpacing(theme.SPACE_MD)
        right.addWidget(sites_label)
        right.addLayout(self.sites_col)
        right.addSpacing(theme.SPACE_MD)
        right.addWidget(next_label)
        right.addWidget(self.next_text)
        right.addStretch(1)
        right_wrap = QWidget()
        right_wrap.setLayout(right)
        right_wrap.setFixedWidth(300)

        split = QHBoxLayout()
        split.setSpacing(theme.SPACE_LG)
        left_wrap = QWidget()
        left_wrap.setLayout(left)
        split.addWidget(left_wrap, stretch=1)
        split.addWidget(_rule(vertical=True))
        split.addWidget(right_wrap)

        root = QVBoxLayout()
        root.setContentsMargins(
            theme.SPACE_LG, theme.SPACE_MD, theme.SPACE_LG, theme.SPACE_LG
        )
        root.setSpacing(theme.SPACE_MD)
        root.addLayout(nav)
        root.addWidget(pond, stretch=3)
        root.addLayout(scrub_row)
        root.addWidget(_rule())
        root.addLayout(split, stretch=4)
        page = QWidget()
        page.setLayout(root)
        self.setCentralWidget(page)

        # --------------------------------------------------- status + data
        self.status = QLabel()
        self.statusBar().addPermanentWidget(self.status)
        self.statusBar().showMessage("Tracking")

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick_replay)

        self.prev_btn.clicked.connect(lambda: self._shift_window(-1))
        self.next_btn.clicked.connect(lambda: self._shift_window(+1))
        self.timeframe.rangeChanged.connect(self._set_range)
        self.replay_btn.clicked.connect(self._toggle_replay)
        self.scrubber.sliderPressed.connect(self._scrub_start)
        self.scrubber.sliderReleased.connect(self._scrub_end)
        self.scrubber.sliderMoved.connect(self._scrub_to)

        self.worker = self._spawn_worker()
        self.worker.start()
        self._refresh_status()
        self.refresh()

    # ---------------------------------------------------------------- tracking

    def _spawn_worker(self) -> TrackerWorker:
        w = TrackerWorker(self.store, poll_interval=2.0, parent=self)
        w.sampled.connect(self._on_sample)
        w.switched.connect(self._on_switch)
        return w

    def _toggle_tracking(self, paused: bool) -> None:
        if paused:
            self.worker.stop()
            self.track_btn.setText("Resume tracking")
            self.statusBar().showMessage("Paused")
        else:
            self.worker = self._spawn_worker()
            self.worker.start()
            self.track_btn.setText("Pause tracking")
            self.statusBar().showMessage("Tracking")
        self._refresh_status()

    def _on_sample(self, s: dict) -> None:
        title = s.get("window_title")
        self.statusBar().showMessage(
            f"Tracking: {s['app_name']}" + (f" ({title})" if title else "")
        )

    def _on_switch(self, _ev: dict) -> None:
        self._switches_today += 1
        self._refresh_status()
        self.refresh()

    def _refresh_status(self) -> None:
        self.status.setText(f"{self._switches_today} switches today")

    # ------------------------------------------------------------------ range

    def _set_range(self, _start: float, _end: float) -> None:
        self._offset = 0.0
        self.refresh()

    def _shift_window(self, direction: int) -> None:
        self._offset += direction * self.timeframe.window_seconds()
        self.refresh()

    @staticmethod
    def _fill_list(layout: QVBoxLayout, rows: list[tuple[str, str]]) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.setParent(None)  # detach now so a stale row can't linger
                w.deleteLater()
        for name, value in rows:
            layout.addWidget(_list_row(name, value))

    def refresh(self) -> None:
        """Recompute the ledger page from the store."""
        base_start, base_end = self.timeframe.range()
        self.start, self.end = base_start + self._offset, base_end + self._offset
        start, end = self.start, self.end
        self._stop_replay()
        self.date_label.setText(self._range_label(start, end))

        events = self.store.events_in_range(start, end)
        switches = self.store.switches_in_range(start, end)

        blocks = [
            (ts, max(dwell, 0.0), domain or app)
            for ts, app, _bid, _title, _pid, dwell, domain in events
        ]
        self.ripple.set_data(blocks, start, end)
        self.scrubber.setValue(0)

        tracked = self.store.tracked_seconds_in_range(start, end)
        n = len(switches)
        rate = n / (tracked / 3600.0) if tracked > 0 else 0.0
        top = self.store.top_apps_in_range(start, end, limit=5)
        self.m_tracked.value_label.setText(f"{tracked / 3600.0:.1f} h")
        self.m_switches.value_label.setText(str(n))
        self.m_rate.value_label.setText(f"{rate:.1f}")
        self.m_top.value_label.setText(top[0][0] if top else "None")

        self._fill_list(
            self.apps_col,
            [(name, _dwell(dur)) for name, dur, _n in top],
        )
        self._fill_list(
            self.sites_col,
            [
                (dom, _dwell(dur))
                for dom, dur, _n in self.store.top_domains_in_range(start, end, limit=5)
            ],
        )

        if top:
            dicts = transitions.to_event_dicts(events)
            nxt, _total = transitions.top_next_for_app(dicts, top[0][0])
            self.next_text.setText(
                f"After {top[0][0]}: {transitions.format_next(nxt)}"
                if nxt
                else "No transitions yet."
            )
        else:
            self.next_text.setText("Nothing tracked in this window.")

        self.log.setRowCount(len(events))
        for i, (ts, app, _bid, title, _pid, dwell, domain) in enumerate(events):
            doc = domain or title or "—"
            for col, text in enumerate(
                (
                    datetime.fromtimestamp(ts).strftime("%H:%M"),
                    app,
                    doc,
                    _dwell(max(dwell, 0.0)),
                )
            ):
                self.log.setItem(i, col, QTableWidgetItem(text))

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
            if self._replay_ts is None:
                self._replay_ts = self.start
            self.replay_btn.setText("Stop")
            self._timer.start()

    def _stop_replay(self) -> None:
        self._timer.stop()
        self._replay_ts = None
        self.replay_btn.setText("Replay")
        self.ripple.set_playhead(None)
        self.scrubber.setValue(0)
        self.clock.setText("—")

    def _tick_replay(self) -> None:
        span = self.end - self.start
        step = span / 600.0  # ~30 s sweep for any window
        self._replay_ts = (self._replay_ts or self.start) + step
        if self._replay_ts >= self.end:
            self._stop_replay()
            return
        self.ripple.set_playhead(self._replay_ts)
        self.clock.setText(
            datetime.fromtimestamp(self._replay_ts).strftime("%H:%M")
        )
        if not self._scrubbing:
            frac = (self._replay_ts - self.start) / span
            self.scrubber.setValue(round(frac * SCRUB_STEPS))

    # ------------------------------------------------------------------ scrub

    def _scrub_start(self) -> None:
        self._scrubbing = True

    def _scrub_end(self) -> None:
        self._scrub_to(self.scrubber.value())
        self._scrubbing = False

    def _scrub_to(self, value: int) -> None:
        span = self.end - self.start
        ts = self.start + span * value / SCRUB_STEPS
        # remember the position — a running replay resumes from it, and
        # pressing Replay after a dry scrub starts there too
        self._replay_ts = ts
        self.ripple.set_playhead(ts)
        self.clock.setText(datetime.fromtimestamp(ts).strftime("%H:%M"))

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.worker.stop()
        self.worker.wait(2000)
        super().closeEvent(event)
