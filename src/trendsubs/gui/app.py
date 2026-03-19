from __future__ import annotations

from PySide6.QtWidgets import QApplication

from trendsubs.gui.window import TrendSubsWindow


def launch_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = TrendSubsWindow()
    window.show()
    return app.exec()
