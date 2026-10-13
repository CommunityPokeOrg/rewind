"""Context-switch counting and attention-fragmentation metrics.

Pure Python — no Qt — so it is testable off-macOS. The poller calls
``observe`` on every sample; whenever the frontmost PID changes we count a
context switch. Fragmentation is expressed as switches per minute over a
sliding window.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


@dataclass
class SwitchEvent:
    ts: float
    from_pid: Optional[int]
    to_pid: int
    from_app: Optional[str]
    to_app: Optional[str]


class SwitchCounter:
    """Counts changes of the frontmost process ID over time."""

    def __init__(self) -> None:
        self.count = 0
        self._last_pid: Optional[int] = None
        self._last_app: Optional[str] = None

    def observe(
        self,
        pid: Optional[int],
        app_name: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> Optional[SwitchEvent]:
        """Record a sample. Returns a SwitchEvent iff the frontmost PID changed."""
        ts = time.time() if ts is None else ts
        if pid is None:
            return None
        if self._last_pid is None:
            self._last_pid, self._last_app = pid, app_name
            return None
        if pid == self._last_pid:
            return None
        ev = SwitchEvent(
            ts=ts,
            from_pid=self._last_pid,
            to_pid=pid,
            from_app=self._last_app,
            to_app=app_name,
        )
        self.count += 1
        self._last_pid, self._last_app = pid, app_name
        return ev


def fragmentation_rate(
    switch_times: Sequence[float],
    window_s: float,
    now: Optional[float] = None,
) -> float:
    """Switches per minute inside the trailing ``window_s`` seconds."""
    now = time.time() if now is None else now
    cutoff = now - window_s
    recent = sum(1 for t in switch_times if t >= cutoff and t <= now)
    return recent / (window_s / 60.0)


def fragmentation_series(
    switch_times: Sequence[float],
    start: float,
    end: float,
    bucket_s: float = 60.0,
) -> list[tuple[float, float]]:
    """Bucketed switches-per-minute over [start, end) for charting.

    Returns ``[(bucket_start_ts, switches_per_min), ...]``.
    """
    if bucket_s <= 0:
        raise ValueError("bucket_s must be positive")
    series: list[tuple[float, float]] = []
    t = start
    while t < end:
        n = sum(1 for s in switch_times if t <= s < t + bucket_s)
        series.append((t, n / (bucket_s / 60.0)))
        t += bucket_s
    return series
