"""Offscreen smoke test for the ripple replay widget."""

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from rewind import theme  # noqa: E402
from rewind.widgets import RippleWidget  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    theme.apply(a)
    yield a


def _blocks(start):
    return [
        (start + 60, 900.0, "Xcode"),       # long focus: wide slow ring
        (start + 1200, 12.0, "Safari"),     # brief check: droplet
        (start + 2400, 300.0, "github.com"),  # medium block, domain label
    ]


def test_ripples_spawn_and_fade(app):
    w = RippleWidget()
    w.resize(800, 400)
    start, end = 0.0, 3600.0
    w.set_data(_blocks(start), start, end)
    assert not w._ripples

    w.set_playhead(start + 100)   # crosses the first block
    assert len(w._ripples) == 1
    assert w._ripples[0].label == "Xcode"
    assert not w._ripples[0].droplet

    w.set_playhead(start + 2500)  # crosses both remaining blocks
    labels = [r.label for r in w._ripples]
    assert "Safari" in labels and "github.com" in labels
    droplet = next(r for r in w._ripples if r.label == "Safari")
    ring = next(r for r in w._ripples if r.label == "Xcode")
    assert droplet.droplet and ring.max_r > droplet.max_r
    assert 1.5 <= ring.life <= 2.5

    w.grab()  # must render without error offscreen


def test_scrub_backwards_drops_future_ripples(app):
    w = RippleWidget()
    w.resize(800, 400)
    start, end = 0.0, 3600.0
    w.set_data(_blocks(start), start, end)

    w.set_playhead(start + 2500)
    assert len(w._ripples) == 3
    w.set_playhead(start + 100)  # scrub back before blocks 2 and 3
    assert [r.label for r in w._ripples] == ["Xcode"]
    w.set_playhead(start + 2500)  # re-play: ripples spawn again
    assert len(w._ripples) == 3


def test_ripples_expire_and_render(app):
    w = RippleWidget()
    w.resize(800, 400)
    start, end = 0.0, 3600.0
    w.set_data(_blocks(start), start, end)
    w.set_playhead(start + 60)
    assert w._ripples
    # expire every ripple artificially, then paint once
    for r in w._ripples:
        r.born = time.monotonic() - r.life - 0.01
    w.grab()
    assert not w._ripples  # paint culls expired ripples


def test_empty_window_message_renders(app):
    w = RippleWidget()
    w.resize(800, 400)
    w.set_data([], 0.0, 3600.0)
    w.set_playhead(100.0)
    img = w.grab().toImage()
    assert not img.isNull()
