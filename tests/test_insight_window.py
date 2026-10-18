"""MainWindow integration regression: sampling, Graphics tab, Insights, locale, focus.

Runs headless with the normal Qt desktop app classes, without live hardware writes
or network requests. The sampler's background thread is intentionally disabled.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QColor

from vitalux import i18n, settings, theme
from vitalux.sensors import collect
from vitalux.update_manager import UpdateManager
from vitalux.window import MainWindow, Sampler


def check_window():
    app = QApplication.instance() or QApplication([])
    theme.set_mode("glass")
    app.setStyleSheet(theme.stylesheet())
    with tempfile.TemporaryDirectory() as folder:
        prior = settings.PATH
        previous_start = Sampler.start
        window = None
        try:
            settings.PATH = str(Path(folder) / "settings.json")
            settings.set("close_to_tray", False)
            Sampler.start = lambda self: None  # Deterministic manual sampling.
            manager = UpdateManager()
            logo = QPixmap(96, 96)
            logo.fill(QColor("#52d3ff"))
            window = MainWindow({"name": "TestLinux", "short": "Test",
                                 "version": "2026.10"}, logo, manager)
            window.resize(1100, 780)
            window.show()
            app.processEvents()
            data = collect()
            window.on_sample(data)
            window._switch_page(2)
            app.processEvents()
            panel = window.pages[2][1].lab_panel
            assert panel is not None
            assert len(window.lab.history) == 1
            assert panel.last_sample is data
            window.open_focus_window()
            app.processEvents()
            assert window._focus_window.isVisible()
            window.set_language("en")
            assert "Focus mode" in window._focus_window.windowTitle()
            assert panel.compare_group.title() == "Before / after comparison"
            window.set_language("de")
            assert "Fokusmodus" in window._focus_window.windowTitle()
            window._focus_window.close()
            window._force_quit = True
            assert window.close()
            app.processEvents()
            print("Full window integration, sampling, locale, GPU and focus: PASS")
        finally:
            Sampler.start = previous_start
            if window and window.isVisible():
                window._force_quit = True
                window.close()
            settings.PATH = prior


if __name__ == "__main__":
    check_window()
