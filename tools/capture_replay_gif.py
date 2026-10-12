"""Render an animated GIF of the Replay scrubber sweeping the day's trace.

Offscreen (QT_QPA_PLATFORM=offscreen), same seeded day as
capture_screenshots.py: the Rewind view's Replay playhead is driven across
the window while frames are grabbed with QWidget.grab(), then assembled
with Pillow (scaled down, ~50 frames, held final frame) under
docs/screenshots/rewind-replay.gif.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "screenshots" / "rewind-replay.gif"

from capture_screenshots import seed_day  # noqa: E402  (same seed data)

FRAMES = 48            # sweep frames across the window
FRAME_MS = 90          # per-frame duration
HOLD_MS = 1600         # hold on the last frame
MAX_WIDTH = 900        # keeps the GIF small


def main() -> None:
    from PIL import Image
    from PySide6.QtGui import QPixmap
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
        win.resize(1200, 760)
        win.show()
        app.processEvents()

        view = win.rewind_view
        start, end = view.start, view.end

        # arm the replay UI so the button reads 'Stop' like a real replay
        view._toggle_replay()
        app.processEvents()

        frames: list[Image.Image] = []
        for i in range(FRAMES):
            ts = start + (end - start) * i / (FRAMES - 1)
            view.seismograph.set_playhead(ts)
            app.processEvents()
            pix = view.grab()
            img = pix.toImage()
            pil = Image.frombytes(
                "RGBA",
                (img.width(), img.height()),
                img.bits().tobytes(),
            ).convert("RGB")
            frames.append(pil)

        win.close()
        app.processEvents()
        store.close()

    # downscale + assemble
    w, h = frames[0].size
    if w > MAX_WIDTH:
        frames = [
            f.resize((MAX_WIDTH, int(h * MAX_WIDTH / w)), Image.LANCZOS)
            for f in frames
        ]
    durations = [FRAME_MS] * (len(frames) - 1) + [HOLD_MS]
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(frames)} frames)")


if __name__ == "__main__":
    main()
