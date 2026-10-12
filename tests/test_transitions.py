"""Tests for context-transition aggregation (rewind/transitions.py)."""

from rewind.transitions import (
    format_next,
    ident,
    iter_pairs,
    top_next,
    top_next_for_app,
)


def ev(app, domain=None, ts=0.0):
    return {"app_name": app, "domain": domain, "ts": ts}


def test_ident_prefers_domain():
    assert ident("Safari", "github.com") == "github.com"
    assert ident("Slack", None) == "Slack"
    assert ident("Slack", "  ") == "Slack"  # blank domain falls back to app


def test_iter_pairs_consecutive_order():
    pairs = list(iter_pairs([ev("A"), ev("B"), ev("C")]))
    assert [(a["app_name"], b["app_name"]) for a, b in pairs] == [("A", "B"), ("B", "C")]


def test_top_next_counts_and_percentages():
    events = [
        ev("Safari", "github.com"),
        ev("Cursor"),
        ev("Safari", "github.com"),
        ev("Cursor"),
        ev("Safari", "github.com"),
        ev("Slack"),
        ev("Safari", "github.com"),
        ev("Cursor"),
        ev("Safari", "github.com"),  # trailing event: 4 leaves total
    ]
    top, total = top_next(events, "github.com")
    assert total == 4
    assert top[0][0] == "Cursor" and top[0][1] == 3
    assert top[0][2] == pytest_approx(75.0)
    assert top[1][0] == "Slack" and top[1][2] == pytest_approx(25.0)


def test_self_transitions_skipped():
    # domain->domain inside the same browser is still an identity change
    # (github.com -> youtube.com counts); A->A never counts.
    events = [
        ev("Safari", "github.com"),
        ev("Safari", "github.com"),  # same item, must be skipped
        ev("Slack"),
        ev("Slack"),
    ]
    top, total = top_next(events, "github.com")
    assert total == 1
    assert top == [("Slack", 1, 100.0)]


def test_top_three_truncation():
    dests = ["A", "B", "C", "D", "E"]
    events = []
    for d in dests:
        events += [ev("Safari", "github.com"), ev(d)]
    top, total = top_next(events, "github.com", top_n=3)
    assert total == 5
    assert len(top) == 3
    assert {d for d, _n, _p in top} <= set(dests)


def test_timeframe_boundary_events_excluded():
    # Filtering upstream: only pairs fully inside the window count.
    # If the window starts after the "outside" event, no pair includes it.
    inside = [ev("Slack"), ev("Cursor"), ev("Slack")]
    top, total = top_next(inside, "Slack")
    assert total == 1  # Slack -> Cursor; outside event never enters a pair
    assert top[0][0] == "Cursor"


def test_top_next_for_app_requires_app_change():
    events = [
        ev("Safari", "github.com"),
        ev("Safari", "youtube.com"),  # tab hop: not "leaving" Safari
        ev("Slack"),
    ]
    top, total = top_next_for_app(events, "Safari")
    assert total == 1
    assert top == [("Slack", 1, pytest_approx(100.0))]

    # destination keeps its domain-or-app identity
    events += [ev("Safari", "github.com"), ev("Cursor")]
    top, total = top_next_for_app(events, "Safari")
    assert total == 2


def test_format_next():
    top = [("Cursor", 3, 45.0), ("Twitter", 2, 30.0), ("Slack", 1, 15.0)]
    assert format_next(top) == "Cursor 45%, Twitter 30%, Slack 15%"
    assert format_next([]) == ""


def pytest_approx(x):
    import pytest

    return pytest.approx(x)
