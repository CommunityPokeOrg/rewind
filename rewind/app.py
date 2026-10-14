"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .db import EventStore
from .theme import apply_theme
from .ui import RewindWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Rewind")
    app.setOrganizationName("CommunityPokeOrg")
    apply_theme(app)
    store = EventStore()
    win = RewindWindow(store)
    win.show()
    rc = app.exec()
    store.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
