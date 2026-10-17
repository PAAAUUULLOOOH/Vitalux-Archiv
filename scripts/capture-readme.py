#!/usr/bin/env python3
"""Capture Vitalux's *real* Qt dashboard in a headless Linux test session.

Called in GitHub Actions against the official ZIP release. No screenshots or
fake readings are hand-drawn: the UI paints itself as in normal use. Hardware
sensors absent on the build runner may appear as unavailable.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app_root = Path.cwd()
sys.path.insert(0, str(app_root))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from vitalux import distro, i18n, sensors, settings, theme
from vitalux.brand import app_icon
from vitalux.logo import load_logo
from vitalux.update_manager import UpdateManager
from vitalux.window import MainWindow


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: capture-readme.py OUTPUT.png")
    output = Path(sys.argv[1]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Config is isolated by the workflow's XDG_CONFIG_HOME, never a real user's.
    settings.set("theme", "glass")
    settings.set("sidebar_collapsed", False)
    i18n.set_lang("de")
    application = QApplication([])
    application.setQuitOnLastWindowClosed(False)
    application.setApplicationName("Vitalux")
    info = distro.info()
    theme.set_mode("glass")
    theme.set_accent(info["color"])
    application.setStyleSheet(theme.stylesheet())
    application.setWindowIcon(app_icon())
    sensors.prime()
    manager = UpdateManager()
    window = MainWindow(info, load_logo(info, 96), manager)
    window.resize(1380, 900)
    window.show()

    def capture():
        application.processEvents()
        # Full-resolution native Qt grab, not a generated approximation.
        pixmap = window.grab()
        ok = not pixmap.isNull() and pixmap.save(str(output), "PNG")
        print(f"Dashboard screenshot: {output}, saved={ok}", flush=True)
        # Sensor/QSystemTray background processes may otherwise delay CI exit.
        sys.stdout.flush()
        os._exit(0 if ok else 2)

    QTimer.singleShot(5000, capture)
    application.exec()


if __name__ == "__main__":
    main()
