"""Tests for the SQLite WAL event store (no Qt required)."""

import sqlite3
from datetime import date, datetime

import pytest

from rewind.db import EventStore, SCHEMA_V1, SCHEMA_VERSION, day_bounds, last_hours


@pytest.fixture
def store(tmp_path):
    s = EventStore(tmp_path / "test.db")
    yield s
    s.close()


def test_wal_mode(store):
    (mode,) = store.conn.execute("PRAGMA journal_mode").fetchone()
    assert mode == "wal"


def test_schema_version_set(store):
    (v,) = store.conn.execute("PRAGMA user_version").fetchone()
    assert v == SCHEMA_VERSION


def test_migration_from_v1(tmp_path):
    """A v1 database gains the domain column and keeps its rows."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_V1)
    conn.execute(
        "INSERT INTO events (ts, app_name, bundle_id, window_title, pid, duration_s)"
        " VALUES (1.0, 'Safari', 'com.apple.Safari', 'GH', 7, 3.5)"
    )
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    s = EventStore(path)
    cols = {r[1] for r in s.conn.execute("PRAGMA table_info(events)")}
    assert "domain" in cols
    rows = s.conn.execute("SELECT app_name, duration_s, domain FROM events").fetchall()
    assert rows == [("Safari", 3.5, None)]
    s.close()


def test_log_event_backfills_duration_and_domain(store):
    t0 = day_bounds(date.today())[0]
    store.log_event(t0, "Safari", "com.apple.Safari", "GH", 1, domain="github.com")
    store.log_event(t0 + 5, "Xcode", "com.apple.dt.Xcode", "rewind", 2)
    rows = store.conn.execute(
        "SELECT app_name, domain, duration_s FROM events ORDER BY id"
    ).fetchall()
    assert rows[0] == ("Safari", "github.com", pytest.approx(5.0))
    assert rows[1] == ("Xcode", None, 0.0)


def test_range_queries(store):
    today = date.today()
    start, end = day_bounds(today)
    store.log_event(start + 10, "A", None, "w", 1)
    store.log_event(start + 20, "B", None, "w", 2, domain="x.com")
    store.log_event(start - 60, "Old", None, "w", 9)
    store.log_switch(start + 20, 1, 2, "A", "B")

    assert len(store.events_in_range(start, end)) == 2
    assert len(store.events_in_range(start, start + 15)) == 1
    assert len(store.switches_in_range(start, end)) == 1
    assert store.tracked_seconds_in_range(start, end) == pytest.approx(10.0)


def test_top_aggregations(store):
    today = date.today()
    start, end = day_bounds(today)
    for i, (app, title, dom) in enumerate(
        [
            ("Safari", "GH pulls", "github.com"),
            ("Safari", "GH pulls", "github.com"),
            ("Safari", "YT", "youtube.com"),
            ("Xcode", "tracker.py", None),
            ("Xcode", "tracker.py", None),
        ]
    ):
        store.log_event(start + i * 10, app, None, title, i, domain=dom)
    apps = store.top_apps_in_range(start, end)
    assert apps[0][0] in ("Safari", "Xcode")

    titles = store.top_titles_in_range(start, end)
    flat = {(a, t): d for a, t, d, _n in titles}
    assert flat[("Safari", "GH pulls")] == pytest.approx(20.0)  # 10+10 dwell
    assert flat[("Xcode", "tracker.py")] == pytest.approx(10.0)  # 10+0 (tail)

    domains = store.top_domains_in_range(start, end)
    assert domains[0][0] == "github.com"
    assert domains[0][1] == pytest.approx(20.0)
    assert all(d for d, *_ in domains)


def test_last_hours():
    s, e = last_hours(6, now=3600 * 30)
    assert e - s == 6 * 3600
