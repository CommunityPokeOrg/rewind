"""Main window — a macOS-style sidebar shell wiring the worker to the views."""

from __future__ import annotations

import html
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .db import EventStore
from .theme import TRACE
from .views import RewindView, StatsView, TimelineView
from .workers import TrackerWorker


class RewindWindow(QMainWindow):
    def __init__(self, store: EventStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rewind")
        self.resize(980, 640)
        self.store = store

        central = QWidget(self)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- sidebar: source list + tracking footer -------------------------
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(204)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 16, 12, 14)
        side.setSpacing(4)

        self.nav = QListWidget()
        self.nav.setObjectName("sidebarNav")
        self.nav.setFocusPolicy(Qt.NoFocus)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for title in ("Rewind", "Timeline", "Statistics"):
            QListWidgetItem(title, self.nav)
        self.nav.setFixedHeight(3 * 30)
        side.addWidget(self.nav)
        side.addStretch(1)

        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setTextFormat(Qt.RichText)
        self.count_label = QLabel()
        self.count_label.setObjectName("countLabel")
        self.track_btn = QPushButton("Pause tracking")
        self.track_btn.clicked.connect(self._toggle_tracking)
        side.addWidget(self.status_label)
        side.addWidget(self.count_label)
        side.addSpacing(6)
        side.addWidget(self.track_btn)

        divider = QFrame()
        divider.setObjectName("hairlineV")
        divider.setFrameShape(QFrame.VLine)

        # -- pages ------------------------------------------------------------
        self.pages = QStackedWidget()
        self.rewind_view = RewindView(store)
        self.timeline_view = TimelineView(store)
        self.stats_view = StatsView(store)
        for view in (self.rewind_view, self.timeline_view, self.stats_view):
            self.pages.addWidget(view)

        root.addWidget(sidebar)
        root.addWidget(divider)
        root.addWidget(self.pages, 1)
        self.setCentralWidget(central)

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)

        self._tracking = True
        self._switches_today = len(store.switches_for_day(date.today()))
        self.worker = TrackerWorker(store, poll_interval=2.0, parent=self)
        self.worker.sampled.connect(self._on_sample)
        self.worker.switched.connect(self._on_switch)
        self.worker.start()
        self._refresh_status()

    # ---------------------------------------------------------------- tracking

    def _toggle_tracking(self) -> None:
        if self._tracking:
            self.worker.stop()
            self.worker.wait(2000)
            self._tracking = False
            self.track_btn.setText("Resume tracking")
            self._set_status("Paused", dot=None)
        else:
            self.worker = TrackerWorker(self.store, poll_interval=2.0, parent=self)
            self.worker.sampled.connect(self._on_sample)
            self.worker.switched.connect(self._on_switch)
            self.worker.start()
            self._tracking = True
            self.track_btn.setText("Pause tracking")
            self._set_status("Tracking")
        self._refresh_status()

    def _on_sample(self, s: dict) -> None:
        text = s["app_name"] + (
            f" — {s['window_title']}" if s.get("window_title") else ""
        )
        self._set_status(text)

    def _set_status(self, text: str, dot: str | None = TRACE) -> None:
        metrics = QFontMetrics(self.status_label.font())
        elided = metrics.elidedText(
            text, Qt.ElideMiddle, self.status_label.contentsRect().width()
        )
        prefix = f'<span style="color:{dot}">●</span> ' if dot else ""
        self.status_label.setText(prefix + html.escape(elided))

    def _on_switch(self, ev: dict) -> None:
        self._switches_today += 1
        self._refresh_status()
        # refresh visible views cheaply
        self.rewind_view.show_day(self.rewind_view.day)
        self.timeline_view.show_day(self.timeline_view.day)
        self.stats_view.show_day(self.stats_view.day)

    def _refresh_status(self) -> None:
        self.count_label.setText(f"{self._switches_today} switches today")
        if self._tracking:
            self._set_status("Tracking")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.worker.stop()
        self.worker.wait(2000)
        super().closeEvent(event)
