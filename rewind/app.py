"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import theme
from .db import EventStore
from .ui import RewindWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Rewind")
    app.setOrganizationName("CommunityPokeOrg")
    theme.apply(app)
    store = EventStore()
    win = RewindWindow(store)
    win.show()
    rc = app.exec()
    store.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
