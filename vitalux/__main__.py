import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import APP_NAME, distro, i18n, sensors, settings, theme, diagnostics, hover_hints
from .logo import load_logo
from .brand import app_icon
from .update_manager import UpdateManager


def main():
    sys.excepthook = diagnostics.exception_hook
    diagnostics.enable_native_crash_trace()
    from .window import MainWindow
    app = QApplication(sys.argv)
    # Disable transient hover help across the entire application, not just navigation.
    app._vitalux_hover_guard = hover_hints.install(app)
    # Hiding the final window must not kill the tray icon and sampler.
    # MainWindow.closeEvent explicitly quits on a genuine Exit command.
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    # Desktop-portal app IDs require an installed .desktop entry; avoid asking
    # the portal to register an unknown ID when using Vitalux portably.
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    if os.path.isfile(os.path.join(xdg_data, "applications", "vitalux.desktop")):
        app.setDesktopFileName("vitalux")
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
    QTimer.singleShot(0, manager.check)
    # Let the window appear and the update check start before offering the
    # optional tutorial. Only the first run (or an explicit 'Later') prompts.
    from .guide import offer_first_start_guide
    QTimer.singleShot(1800, lambda: offer_first_start_guide(win))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
