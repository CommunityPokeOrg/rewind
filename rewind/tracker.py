"""Frontmost-application sampler for macOS.

Reads, on each poll:

* the frontmost app via ``NSWorkspace`` (pid, name, bundle id),
* its front window title via ``Quartz.CGWindowListCopyWindowInfo`` (falls back
  to the Accessibility API when the window-server list hides the name),
* the active browser tab title via AppleScript for known browsers.

No screenshots are ever taken — metadata only, all stored locally.
On non-Darwin platforms every function is a safe no-op so the rest of the
app remains importable/testable elsewhere.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Optional

IS_MACOS = sys.platform == "darwin"

# bundle id -> AppleScript that returns "Tab Title" for the active tab.
BROWSER_TAB_SCRIPTS = {
    "com.apple.Safari": (
        'tell application "Safari" to get name of front document'
    ),
    "com.google.Chrome": (
        'tell application "Google Chrome" to get title of active tab of front window'
    ),
    "com.brave.Browser": (
        'tell application "Brave Browser" to get title of active tab of front window'
    ),
    "com.microsoft.edgemac": (
        'tell application "Microsoft Edge" to get title of active tab of front window'
    ),
    "org.mozilla.firefox": (
        # Firefox exposes no tab AppleScript; window title already includes it.
        ""
    ),
    "company.thebrowser.Browser": (  # Arc
        'tell application "Arc" to get title of active tab of front window'
    ),
}


def frontmost_app() -> Optional[dict]:
    """{pid, app_name, bundle_id} for the app owning keyboard focus."""
    if not IS_MACOS:
        return None
    try:
        from AppKit import NSWorkspace  # pyobjc-framework-Cocoa

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        return {
            "pid": int(app.processIdentifier()),
            "app_name": str(app.localizedName() or "Unknown"),
            "bundle_id": str(app.bundleIdentifier() or ""),
        }
    except Exception:
        return None


def frontmost_window_title(pid: int) -> Optional[str]:
    """Best-effort front window title for ``pid`` via the window server."""
    if not IS_MACOS:
        return None
    try:
        from Quartz import (  # pyobjc-framework-Quartz
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListOptionOnScreenOnly,
        )

        opts = kCGWindowListOptionOnScreenOnly
        for info in CGWindowListCopyWindowInfo(opts, kCGNullWindowID) or []:
            if info.get("kCGWindowOwnerPID") != pid:
                continue
            if info.get("kCGWindowLayer", 0) != 0:
                continue
            name = info.get("kCGWindowName")
            if name:
                return str(name)
            break  # frontmost window of the app has no listed name
    except Exception:
        pass
    return _ax_window_title(pid)


def _ax_window_title(pid: int) -> Optional[str]:
    """Accessibility-API fallback (requires Accessibility permission)."""
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
        )

        app_el = AXUIElementCreateApplication(pid)
        err, win = AXUIElementCopyAttributeValue(
            app_el, "AXFocusedWindow", None
        )
        if err or win is None:
            return None
        err, title = AXUIElementCopyAttributeValue(win, "AXTitle", None)
        return str(title) if not err and title else None
    except Exception:
        return None


def browser_tab_title(bundle_id: Optional[str]) -> Optional[str]:
    """Active tab title for known browsers via AppleScript.

    Triggers macOS's Automation permission prompt on first use per browser;
    failure (denied/unsupported) returns None quietly.
    """
    if not IS_MACOS or not bundle_id:
        return None
    script = BROWSER_TAB_SCRIPTS.get(bundle_id)
    if not script:
        return None
    try:
        out = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=3,
        )
        title = out.stdout.strip()
        return title or None
    except Exception:
        return None


def sample() -> Optional[dict]:
    """One observation of the frontmost app/window. None when unavailable."""
    app = frontmost_app()
    if not app:
        return None
    title = frontmost_window_title(app["pid"])
    tab = browser_tab_title(app["bundle_id"])
    if tab:
        title = tab  # browser tab titles are the meaningful window title
    return {
        "ts": time.time(),
        "pid": app["pid"],
        "app_name": app["app_name"],
        "bundle_id": app["bundle_id"],
        "window_title": title,
    }
