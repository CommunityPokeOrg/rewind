"""Entry point for the alternate ledger UI — ``python -m rewind.alt``."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ..db import EventStore
from . import theme
from .window import AltRewindWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Rewind")
    app.setOrganizationName("CommunityPokeOrg")
    theme.apply(app)
    store = EventStore()
    win = AltRewindWindow(store)
    win.show()
    rc = app.exec()
    store.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
