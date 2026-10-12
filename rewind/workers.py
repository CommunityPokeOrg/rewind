"""QThread workers — all background work happens off the UI thread."""

from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal

from . import tracker
from .db import EventStore
from .switches import SwitchCounter


class TrackerWorker(QThread):
    """Polls the frontmost app/window, writes events, emits UI signals.

    Signals:
        sampled(dict):    every raw sample that was stored.
        switched(dict):   only when the frontmost PID changed (context switch).
        refreshed():      light nudge so views can reload the day.
    """

    sampled = Signal(dict)
    switched = Signal(dict)
    refreshed = Signal()

    def __init__(
        self,
        store: EventStore,
        poll_interval: float = 2.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.poll_interval = poll_interval
        self.counter = SwitchCounter()
        self._running = True

    def run(self) -> None:  # noqa: D401 - QThread entry point
        while self._running:
            s = tracker.sample()
            if s:
                self.store.log_event(
                    s["ts"], s["app_name"], s["bundle_id"], s["window_title"], s["pid"]
                )
                self.sampled.emit(s)
                ev = self.counter.observe(s["pid"], s["app_name"], s["ts"])
                if ev:
                    self.store.log_switch(
                        ev.ts, ev.from_pid, ev.to_pid, ev.from_app, ev.to_app
                    )
                    self.switched.emit(
                        {
                            "ts": ev.ts,
                            "from_pid": ev.from_pid,
                            "to_pid": ev.to_pid,
                            "from_app": ev.from_app,
                            "to_app": ev.to_app,
                        }
                    )
                self.refreshed.emit()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False
