# Rewind

A **macOS, local-first time tracker** that watches your attention like a heart
monitor. Rewind passively records which app and window is in front, counts your
context switches, and replays the day as a seismograph/EKG-style trace so you
can *see* where your focus fragmented.

## What it tracks (and what it never does)

- Frontmost application (name, bundle id, PID) via `NSWorkspace`.
- Front window title via the window server / Accessibility API.
- Active browser **tab title** for known browsers via AppleScript.
- Context switches between frontmost processes, with a fragmentation rate
  (switches per minute/hour) over time.

**Privacy:** no screenshots, no keylogging, no network calls, no content
capture — local metadata only, stored in a SQLite database on your machine.

## Requirements

- macOS 13+ (Cocoa/Quartz APIs)
- Python 3.12+
- PySide6 (Qt for Python)

## Setup

```bash
git clone https://github.com/CommunityPokeOrg/rewind.git
cd rewind
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # or: pip install -e .
```

Run it:

```bash
python -m rewind        # or just `rewind` if installed with pip install -e .
```

## macOS permissions

Rewind works with reduced data when permissions are missing — nothing breaks:

- **Accessibility** (System Settings → Privacy & Security → Accessibility):
  lets Rewind read front window titles when the window server redacts them.
- **Automation** (prompted on first use, per browser): lets AppleScript read
  the active tab title of Safari/Chrome/Arc/etc. Deny it and Rewind still
  records the browser's window title.

## Where your data lives

`~/Library/Application Support/Rewind/rewind.db` — SQLite in **WAL mode** so
the background poller (a `QThread`) and the UI can share it safely.

Schema: `events` (timestamp, app name, bundle id, window title, pid, duration)
and `switches` (timestamp, from/to pid, from/to app).

## Using it

- **Rewind tab** — the seismograph: a heartbeat trace of your day. Each spike
  is a context switch; taller, denser spikes = more fragmented attention.
  Navigate days with the arrows, or hit **Replay day** to sweep a playhead
  across the trace.
- **Timeline tab** — every observation, chronologically.
- **Stats tab** — top apps by dwell time and switches per hour.
- The toolbar's **Pause tracking** stops the poller; Resume picks it back up.

## Project layout

```
rewind/
  app.py            # QApplication entry point
  ui.py             # main window, tabs, tracking toggle
  tracker.py        # NSWorkspace / Quartz / AppleScript sampler (macOS)
  workers.py        # QThread poller -> EventStore + Qt signals
  switches.py       # context-switch counter + fragmentation math (pure)
  db.py             # SQLite WAL schema + queries (pure)
  theme.py          # design tokens (color/type/spacing) + central QSS
  views/            # RewindView, TimelineView, StatsView
  widgets/          # SeismographWidget (custom-painted EKG trace)
tools/
  capture_screenshots.py  # offscreen renders into docs/screenshots/
docs/screenshots/   # rendered UI screenshots
tests/              # pytest suite for the pure modules
```

## The interface

A single dark, slate-charcoal window: a slim toolbar strip on top (Pause
tracking), three tabs, and a status bar at the bottom.

- **Rewind** — day navigation, the seismograph trace (hour grid, one EKG
  spike per context switch, replay playhead), and a hairline-divided metric
  strip: tracked hours, context switches, switches/hour, most-used app.
- **Timeline** — the day's observations in a hairline-gridded table.
- **Stats** — top apps by dwell time and switches per hour.

The visual system lives in `rewind/theme.py`: one accent color (phosphor
green, the trace itself), one radius scale, hairline borders and negative
space instead of card chrome, and a system type stack. Views consume tokens;
the stylesheet is generated once by `theme.stylesheet()`.

![Rewind main window](docs/screenshots/main-window.png)
![Daily rewind seismograph view](docs/screenshots/rewind-timeline.png)
![Timeline tab](docs/screenshots/timeline-tab.png)

Regenerate the docs images against a seeded day (works headless):

```bash
QT_QPA_PLATFORM=offscreen python tools/capture_screenshots.py
```

## Tests

```bash
pip install pytest
pytest
```

(The suite covers the storage and fragmentation logic, which are Qt-free.)

## License

MIT — Copyright (c) 2026 CommunityPokeOrg. See [LICENSE](LICENSE).
