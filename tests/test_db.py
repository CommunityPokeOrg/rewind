"""Tests for the SQLite WAL event store (no Qt required)."""

from datetime import date, datetime

import pytest

from rewind.db import EventStore, day_bounds


@pytest.fixture
def store(tmp_path):
    s = EventStore(tmp_path / "test.db")
    yield s
    s.close()


def test_wal_mode(store):
    (mode,) = store.conn.execute("PRAGMA journal_mode").fetchone()
    assert mode == "wal"


def test_log_event_backfills_duration(store):
    t0 = day_bounds(date.today())[0]
    store.log_event(t0, "Finder", "com.apple.finder", "Desktop", 100)
    store.log_event(t0 + 5, "Safari", "com.apple.Safari", "Docs", 200)
    rows = store.conn.execute(
        "SELECT app_name, duration_s FROM events ORDER BY id"
    ).fetchall()
    assert rows[0][1] == pytest.approx(5.0)
    assert rows[1][1] == 0.0


def test_events_and_switches_scoped_to_day(store):
    today = date.today()
    start, end = day_bounds(today)
    store.log_event(start + 10, "Safari", "com.apple.Safari", "Tab", 1)
    store.log_event(start - 60, "Yesterday", "x.y", "old", 9)  # previous day
    store.log_switch(start + 10, 1, 2, "Safari", "Xcode")

    assert len(store.events_for_day(today)) == 1
    assert len(store.switches_for_day(today)) == 1


def test_top_apps_and_tracked_seconds(store):
    today = date.today()
    start, _ = day_bounds(today)
    for i, app in enumerate(["Safari", "Safari", "Xcode"]):
        store.log_event(start + i * 10, app, None, "w", i)
    # durations: 10, 10, 0
    top = store.top_apps(today)
    assert top[0][0] == "Safari"
    assert top[0][1] == pytest.approx(20.0)
    assert store.tracked_seconds(today) == pytest.approx(20.0)


def test_day_bounds():
    d = date(2026, 1, 15)
    start, end = day_bounds(d)
    assert end - start == 86400
    assert datetime.fromtimestamp(start).date() == d
