import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import APP_NAME, distro, i18n, sensors, settings, theme, diagnostics
from .logo import load_logo
from .brand import app_icon
from .update_manager import UpdateManager


def main():
    sys.excepthook = diagnostics.exception_hook
    from .window import MainWindow
    app = QApplication(sys.argv)
    # Hiding the final window must not kill the tray icon and sampler.
    # MainWindow.closeEvent explicitly quits on a genuine Exit command.
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName("vitalux")  # KDE/Pop!_OS/COSMIC app launcher and taskbar association
    lang = settings.get("lang") or ("de" if os.environ.get("LANG", "").lower().startswith("de") else "en")
    i18n.set_lang(lang)
    info = distro.info()
    requested_theme = settings.get('theme', 'glass')
    theme.set_mode(requested_theme)
    if requested_theme != theme.mode():
        settings.set('theme', theme.mode())  # Migrate removed/unknown themes to Glass.
    user_accent = settings.get('accent', 'auto')  # Distribution is the default accent.
    theme.set_accent(info['color'] if user_accent == 'auto' else user_accent)
    app.setStyleSheet(theme.stylesheet())
    logo = load_logo(info, 96)
    app.setWindowIcon(app_icon())
    sensors.prime()
    manager = UpdateManager()
    win = MainWindow(info, logo, manager)
    win.show()
    QTimer.singleShot(4000, manager.check)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
