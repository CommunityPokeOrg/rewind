"""Render the alternate ledger UI offscreen into docs/screenshots/.

Same seeded day as capture_screenshots.py; the replay playhead is swept
partway across the pond so rings are mid-flight when the frame is grabbed.

    QT_QPA_PLATFORM=offscreen python tools/capture_alt_ui.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs" / "screenshots" / "alt_ui_replay.png"

from capture_screenshots import seed_day  # noqa: E402  (same seed data)

SIZE = (1200, 780)
SWEEP_S = 2.4     # real-time sweep so rings land at staggered ages
SETTLE_S = 0.9    # let droplets die and big rings thin before the shot
FROM_FRAC = 0.34  # sweep start (fraction of the window) — calm morning
TO_FRAC = 0.55    # sweep end — playhead rests here for the shot


def main() -> None:
    from PySide6.QtWidgets import QApplication

    from rewind.alt import theme
    from rewind.alt.window import AltRewindWindow
    from rewind.db import EventStore

    app = QApplication([])
    theme.apply(app)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        store = EventStore(Path(td) / "demo.db")
        seed_day(store, date.today())

        win = AltRewindWindow(store)
        win.resize(*SIZE)
        win.show()
        app.processEvents()

        win.timeframe.setCurrentIndex(3)  # "Today" — covers the seeded day
        app.processEvents()
        start, end = win.start, win.end
        span = end - start

        # sweep the playhead in real time, like the mp4 capture: ripples
        # spawn as the playhead crosses them and age on their own clock
        win._replay_ts = start + span * FROM_FRAC
        win.replay_btn.setText("Stop")
        t0 = time.monotonic()
        while True:
            elapsed = time.monotonic() - t0
            if elapsed > SWEEP_S:
                break
            frac = FROM_FRAC + (TO_FRAC - FROM_FRAC) * (elapsed / SWEEP_S)
            ts = start + span * frac
            win._replay_ts = ts
            win.ripple.set_playhead(ts)
            win.scrubber.setValue(round(frac * 1000))
            win.clock.setText(datetime.fromtimestamp(ts).strftime("%H:%M"))
            app.processEvents()
            time.sleep(0.016)

        # let the youngest rings breathe for a beat, then take the shot
        t1 = time.monotonic()
        while time.monotonic() - t1 < SETTLE_S:
            app.processEvents()
            time.sleep(0.016)
        win.repaint()  # clear any stale paint left by the relayout
        win.grab().save(str(OUT))

        win.close()  # stops the tracker worker before interpreter teardown
        app.processEvents()
        store.close()

    print("wrote", OUT)


if __name__ == "__main__":
    main()
