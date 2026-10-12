"""Local-first SQLite storage for Rewind.

The database lives on disk in WAL mode so the background poller thread and
the UI thread can share one connection without blocking each other. All data
is local metadata only — no screenshots, no content capture.

Schema versioning uses ``PRAGMA user_version``:

* v1: ``events`` (ts, app_name, bundle_id, window_title, pid, duration_s)
      and ``switches`` (ts, from/to pid, from/to app).
* v2: adds ``events.domain`` — the browser tab's derived domain, so dwell
      time can be aggregated per site.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 2

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL    NOT NULL,          -- observation start, unix seconds
    app_name     TEXT    NOT NULL,
    bundle_id    TEXT,
    window_title TEXT,
    pid          INTEGER,
    duration_s   REAL    NOT NULL DEFAULT 0 -- dwell on this app/window
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS switches (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       REAL NOT NULL,
    from_pid INTEGER,
    to_pid   INTEGER,
    from_app TEXT,
    to_app   TEXT
);
CREATE INDEX IF NOT EXISTS idx_switches_ts ON switches(ts);
"""


def default_db_path() -> Path:
    """Where Rewind keeps its database (Application Support on macOS)."""
    import sys

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Rewind"
    else:  # dev/testing on other platforms
        base = Path.home() / ".local" / "share" / "rewind"
    return base / "rewind.db"


def day_bounds(day: date) -> tuple[float, float]:
    """Epoch-second bounds [start, end) for a calendar day in local time."""
    start = datetime(day.year, day.month, day.day).timestamp()
    end = (datetime(day.year, day.month, day.day) + timedelta(days=1)).timestamp()
    return start, end


def last_hours(n: int, now: Optional[float] = None) -> tuple[float, float]:
    """Epoch bounds [start, end) covering the trailing ``n`` hours."""
    import time

    end = time.time() if now is None else now
    return end - n * 3600.0, end


class EventStore:
    """Thread-sharable SQLite store (WAL) for events and context switches."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: poller QThread + UI thread share this file;
        # WAL mode keeps readers and the writer out of each other's way.
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Bring the schema up to SCHEMA_VERSION, preserving existing data."""
        (version,) = self.conn.execute("PRAGMA user_version").fetchone()
        if version < 1:
            self.conn.executescript(SCHEMA_V1)
            version = 1
        if version < 2:
            self.conn.execute("ALTER TABLE events ADD COLUMN domain TEXT")
            version = 2
        self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    # ------------------------------------------------------------------ writes

    def log_event(
        self,
        ts: float,
        app_name: str,
        bundle_id: Optional[str],
        window_title: Optional[str],
        pid: Optional[int],
        domain: Optional[str] = None,
    ) -> int:
        """Insert an observation; backfill the previous event's dwell time."""
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT id, ts FROM events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            cur.execute(
                "UPDATE events SET duration_s = ? WHERE id = ?",
                (max(0.0, ts - row[1]), row[0]),
            )
        cur.execute(
            "INSERT INTO events (ts, app_name, bundle_id, window_title, pid, domain)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (ts, app_name, bundle_id, window_title, pid, domain),
        )
        self.conn.commit()
        return cur.lastrowid

    def log_switch(
        self,
        ts: float,
        from_pid: Optional[int],
        to_pid: Optional[int],
        from_app: Optional[str],
        to_app: Optional[str],
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO switches (ts, from_pid, to_pid, from_app, to_app)"
            " VALUES (?, ?, ?, ?, ?)",
            (ts, from_pid, to_pid, from_app, to_app),
        )
        self.conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------ reads
    # All range queries take [start, end) epoch seconds.

    def events_in_range(self, start: float, end: float) -> list[tuple]:
        return self.conn.execute(
            "SELECT ts, app_name, bundle_id, window_title, pid, duration_s, domain"
            " FROM events WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start, end),
        ).fetchall()

    def switches_in_range(self, start: float, end: float) -> list[tuple]:
        return self.conn.execute(
            "SELECT ts, from_pid, to_pid, from_app, to_app"
            " FROM switches WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start, end),
        ).fetchall()

    def tracked_seconds_in_range(self, start: float, end: float) -> float:
        (total,) = self.conn.execute(
            "SELECT COALESCE(SUM(duration_s), 0) FROM events"
            " WHERE ts >= ? AND ts < ?",
            (start, end),
        ).fetchone()
        return float(total)

    def top_apps_in_range(
        self, start: float, end: float, limit: int = 10
    ) -> list[tuple]:
        """(app_name, total_duration_s, samples) by total dwell."""
        return self.conn.execute(
            "SELECT app_name, SUM(duration_s), COUNT(*) FROM events"
            " WHERE ts >= ? AND ts < ? GROUP BY app_name"
            " ORDER BY SUM(duration_s) DESC LIMIT ?",
            (start, end, limit),
        ).fetchall()

    def top_titles_in_range(
        self, start: float, end: float, limit: int = 15
    ) -> list[tuple]:
        """(app_name, window_title, total_duration_s, samples).

        Aggregates dwell per exact window/document title so the Stats view
        can show which pages and documents actually consumed the time.
        """
        return self.conn.execute(
            "SELECT app_name, COALESCE(NULLIF(window_title, ''), '(no title)'),"
            " SUM(duration_s), COUNT(*) FROM events"
            " WHERE ts >= ? AND ts < ?"
            " GROUP BY app_name, window_title"
            " ORDER BY SUM(duration_s) DESC LIMIT ?",
            (start, end, limit),
        ).fetchall()

    def top_domains_in_range(
        self, start: float, end: float, limit: int = 15
    ) -> list[tuple]:
        """(domain, total_duration_s, samples) — browser events only."""
        return self.conn.execute(
            "SELECT domain, SUM(duration_s), COUNT(*) FROM events"
            " WHERE ts >= ? AND ts < ? AND domain IS NOT NULL AND domain != ''"
            " GROUP BY domain ORDER BY SUM(duration_s) DESC LIMIT ?",
            (start, end, limit),
        ).fetchall()

    # ----------------------------------------------------- day conveniences

    def events_for_day(self, day: date) -> list[tuple]:
        return self.events_in_range(*day_bounds(day))

    def switches_for_day(self, day: date) -> list[tuple]:
        return self.switches_in_range(*day_bounds(day))

    def tracked_seconds(self, day: date) -> float:
        return self.tracked_seconds_in_range(*day_bounds(day))

    def top_apps(self, day: date, limit: int = 10) -> list[tuple]:
        return self.top_apps_in_range(*day_bounds(day), limit)

    def close(self) -> None:
        self.conn.close()
