"""Record an MP4 of the Replay scrubber rippling across the pond.

Run under a virtual display so real wall-clock drives the animation:

    xvfb-run -a python tools/capture_replay_mp4.py

Same seeded day as capture_screenshots.py: the Rewind view's Replay
playhead is swept across the window in real time while frames are grabbed
with QWidget.grab() and piped raw into ffmpeg (libx264, yuv420p), landing
at docs/screenshots/rewind-ripple-replay.mp4.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "screenshots" / "rewind-ripple-replay.mp4"

from capture_screenshots import seed_day  # noqa: E402  (same seed data)

FPS = 24
SWEEP_S = 22.0     # replay duration captured
TAIL_S = 2.5       # hold after the sweep so the last rings fade out
SIZE = (1200, 760)


def main() -> None:
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication

    from rewind import theme
    from rewind.db import EventStore
    from rewind.ui import RewindWindow

    app = QApplication([])
    theme.apply(app)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        store = EventStore(Path(td) / "demo.db")
        seed_day(store, date.today())

        win = RewindWindow(store)
        win.resize(*SIZE)
        win.show()
        app.processEvents()

        view = win.rewind_view
        view.timeframe.setCurrentIndex(3)  # "Today" — covers the seeded day
        app.processEvents()
        start, end = view.start, view.end

        # look like a running replay without starting the tick timer —
        # we drive the playhead ourselves at the frame rate
        view._replay_ts = start
        view.replay_btn.setText("Stop")

        ff = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-pix_fmt", "rgba",
                "-s", f"{SIZE[0]}x{SIZE[1]}",
                "-r", str(FPS),
                "-i", "-",
                "-an",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "20",
                "-movflags", "+faststart",
                str(OUT),
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        frame_dt = 1.0 / FPS
        t0 = time.monotonic()
        try:
            while True:
                elapsed = time.monotonic() - t0
                if elapsed > SWEEP_S + TAIL_S:
                    break
                if elapsed <= SWEEP_S:
                    # drive the playhead in real time; the ripple widget
                    # animates on its own wall clock
                    ts = start + (end - start) * (elapsed / SWEEP_S)
                    view._replay_ts = ts
                    view.ripple.set_playhead(ts)
                    view.scrubber.setValue(
                        round((ts - start) / (end - start) * 1000)
                    )
                app.processEvents()
                img = win.grab().toImage().convertToFormat(
                    QImage.Format.Format_RGBA8888
                )
                ff.stdin.write(img.bits().tobytes())
                # pace to the frame rate
                lag = (time.monotonic() - t0) - elapsed
                if lag < frame_dt:
                    time.sleep(frame_dt - lag)
        finally:
            ff.stdin.close()
            ff.wait()
            win.close()  # stops the tracker worker before teardown
            app.processEvents()
            store.close()

    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
