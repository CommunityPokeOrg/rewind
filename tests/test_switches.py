"""Tests for the context-switch counter and fragmentation metrics."""

from rewind.switches import (
    SwitchCounter,
    fragmentation_rate,
    fragmentation_series,
)


def test_counts_only_pid_changes():
    c = SwitchCounter()
    assert c.observe(10, "A", ts=100.0) is None   # first sample initializes
    assert c.observe(10, "A", ts=101.0) is None   # same pid, no switch
    ev = c.observe(20, "B", ts=102.0)
    assert ev is not None
    assert (ev.from_pid, ev.to_pid, ev.from_app, ev.to_app) == (10, 20, "A", "B")
    assert c.count == 1
    assert c.observe(20, "B", ts=103.0) is None
    assert c.count == 1


def test_none_pid_ignored():
    c = SwitchCounter()
    assert c.observe(None) is None
    assert c.count == 0


def test_fragmentation_rate():
    now = 1000.0
    times = [now - 10, now - 30, now - 4000]  # last is outside a 1h window
    assert fragmentation_rate(times, 3600, now=now) == 2 / 60.0


def test_fragmentation_series_buckets():
    times = [0.5, 1.5, 61.0]
    series = fragmentation_series(times, start=0.0, end=120.0, bucket_s=60.0)
    assert len(series) == 2
    assert series[0][1] == 2 / 1.0   # 2 switches per 60s bucket => 2/min
    assert series[1][1] == 1 / 1.0


def test_fragmentation_series_rejects_bad_bucket():
    try:
        fragmentation_series([], 0, 10, bucket_s=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
