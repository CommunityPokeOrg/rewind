"""Main window — wires the tracker worker to the modular views."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QTabWidget,
    QToolBar,
    QWidget,
)

from .db import EventStore
from .views import RewindView, StatsView, TimelineView
from .workers import TrackerWorker


class RewindWindow(QMainWindow):
    def __init__(self, store: EventStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rewind")
        self.resize(980, 640)
        self.store = store

        self.tabs = QTabWidget()
        self.rewind_view = RewindView(store)
        self.timeline_view = TimelineView(store)
        self.stats_view = StatsView(store)
        self.tabs.addTab(self.rewind_view, "Rewind")
        self.tabs.addTab(self.timeline_view, "Timeline")
        self.tabs.addTab(self.stats_view, "Stats")
        self.setCentralWidget(self.tabs)

        self.toolbar = QToolBar("Tracking", self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.track_btn = self.toolbar.addAction("Pause tracking")
        self.track_btn.setCheckable(True)
        self.track_btn.toggled.connect(self._toggle_tracking)

        self.status = QLabel()
        self.statusBar().addPermanentWidget(self.status)
        self.statusBar().showMessage("Tracking")

        self._switches_today = 0
        self.worker = self._spawn_worker()
        self.worker.start()
        self._refresh_status()

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

    def _on_switch(self, ev: dict) -> None:
        self._switches_today += 1
        self._refresh_status()
        self.rewind_view.show_day(self.rewind_view.day)
        self.timeline_view.show_day(self.timeline_view.day)
        self.stats_view.show_day(self.stats_view.day)

    def _refresh_status(self) -> None:
        self.status.setText(f"{self._switches_today} switches today")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.worker.stop()
        self.worker.wait(2000)
        super().closeEvent(event)
