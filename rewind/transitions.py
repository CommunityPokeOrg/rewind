"""Context-transition aggregation: where attention goes next.

Pure Python — no Qt — so it is testable off-macOS.

Item identity matches the breakdown lists: an event's identity is its
``domain`` when present (browser page/site), else its ``app_name``. A
transition is a consecutive pair of events (A then B) inside the selected
timeframe where A and B have different identities; percentages are of all
transitions *out of* A.

Boundary rule: only pairs fully inside the passed event list count — an
event leaving the window pairs with nothing before it.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence


def ident(app_name: str | None, domain: str | None) -> str:
    """Canonical breakdown identity: domain for browsers, else app name."""
    d = (domain or "").strip()
    if d:
        return d
    return (app_name or "").strip()


def iter_pairs(events: Sequence) -> Iterable[tuple]:
    """Consecutive (A, B) pairs, in order."""
    for i in range(len(events) - 1):
        yield events[i], events[i + 1]


def top_next(
    events: Sequence,
    key: str,
    top_n: int = 3,
) -> tuple[list[tuple[str, int, float]], int]:
    """Top destinations reached immediately after identity ``key``.

    ``events`` are rows containing app_name + domain (dicts or the
    ``events_in_range`` tuples). Returns ``([(dest, count, pct_of_leaves)],
    total_leaves)`` with ``top_n`` entries at most.
    """
    counts: Counter[str] = Counter()
    for a, b in iter_pairs(events):
        ia, ib = ident(a["app_name"], a["domain"]), ident(b["app_name"], b["domain"])
        if ia == key and ib != key:
            counts[ib] += 1
    total = sum(counts.values())
    top = [(d, n, n / total * 100.0) for d, n in counts.most_common(top_n)]
    return top, total


def top_next_for_app(
    events: Sequence,
    app_name: str,
    top_n: int = 3,
) -> tuple[list[tuple[str, int, float]], int]:
    """Top destinations on actually *leaving* the app ``app_name``.

    App rows key on app_name rather than identity: only pairs where the app
    changes count (tab hops inside the same browser are not 'leaving').
    """
    counts: Counter[str] = Counter()
    for a, b in iter_pairs(events):
        if a["app_name"] == app_name and b["app_name"] != app_name:
            counts[ident(b["app_name"], b["domain"])] += 1
    total = sum(counts.values())
    top = [(d, n, n / total * 100.0) for d, n in counts.most_common(top_n)]
    return top, total


def to_event_dicts(rows: Sequence[tuple]) -> list[dict]:
    """Adapt ``events_in_range`` rows to the dict shape the API expects."""
    return [
        {
            "app_name": r[1],
            "bundle_id": r[2],
            "window_title": r[3],
            "domain": r[6],
        }
        for r in rows
    ]


def format_next(top: Sequence[tuple[str, int, float]]) -> str:
    """'Cursor 45%, Twitter 30%, Slack 15%' — empty string when no data."""
    return ", ".join(f"{d} {p:.0f}%" for d, _n, p in top)
