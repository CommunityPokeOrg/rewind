"""Render Rewind offscreen and save PNGs to docs/screenshots/.

Seeds a temp database with a plausible day (deep-focus morning, fragmented
afternoon, browser events carrying domains), then grabs the real widgets —
no fake markup. Run:

    QT_QPA_PLATFORM=offscreen python tools/capture_screenshots.py
"""

from __future__ import annotations

import os
import random
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "screenshots"

# (app, bundle id, window title, domain-or-None)
APPS = [
    ("Xcode", "com.apple.dt.Xcode", "rewind - tracker.py", None),
    ("Safari", "com.apple.Safari", "Pull requests - CommunityPokeOrg/rewind", "github.com"),
    ("Terminal", "com.apple.Terminal", "pytest -q", None),
    ("Slack", "com.tinyspeck.slackmacgap", "#design", None),
    ("Safari", "com.apple.Safari", "QThread - Qt for Python", "doc.qt.io"),
    ("Safari", "com.apple.Safari", "YouTube", "youtube.com"),
    ("Mail", "com.apple.mail", "Inbox", None),
    ("Safari", "com.apple.Safari", "Hacker News", "news.ycombinator.com"),
    ("Figma", "com.figma.Desktop", "Rewind UI mocks", None),
    ("Music", "com.apple.Music", "Focus", None),
]


def seed_day(store, day: date) -> None:
    rng = random.Random(42)
    start = datetime(day.year, day.month, day.day, 8, 30).timestamp()
    end = datetime(day.year, day.month, day.day, 18, 15).timestamp()
    t = start
    app_i = 0
    last_pid = None
    last_name = None
    pid_map: dict[int, int] = {}
    while t < end:
        # calm deep-focus morning; fragmented afternoon bursts
        dense = datetime.fromtimestamp(t).hour >= 14
        dwell = rng.randint(30, 140) if dense else rng.randint(240, 900)
        name, bundle, title, domain = APPS[app_i % len(APPS)]
        pid = pid_map.setdefault(app_i, 500 + app_i)
        store.log_event(t, name, bundle, title, pid, domain=domain)
        if last_pid is not None and pid != last_pid:
            store.log_switch(t, last_pid, pid, last_name, name)
        last_pid, last_name = pid, name
        app_i += rng.randint(0, 2) if dense else rng.choice([0, 0, 1])
        t += dwell


def main() -> None:
    from PySide6.QtWidgets import QApplication

    from rewind import theme
    from rewind.db import EventStore
    from rewind.ui import RewindWindow

    app = QApplication([])
    theme.apply(app)

    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        store = EventStore(Path(td) / "demo.db")
        seed_day(store, date.today())

        win = RewindWindow(store)
        win.resize(1200, 760)
        win.show()
        app.processEvents()

        win.grab().save(str(OUT / "main-window.png"))
        win.rewind_view.grab().save(str(OUT / "rewind-timeline.png"))

        win.tabs.setCurrentWidget(win.stats_view)
        app.processEvents()
        win.stats_view.grab().save(str(OUT / "stats-tab.png"))

        win.tabs.setCurrentWidget(win.timeline_view)
        app.processEvents()
        win.timeline_view.grab().save(str(OUT / "timeline-tab.png"))

        win.close()  # stops the tracker worker before interpreter teardown
        app.processEvents()
        store.close()

    for p in sorted(OUT.glob("*.png")):
        print("wrote", p)


if __name__ == "__main__":
    main()
