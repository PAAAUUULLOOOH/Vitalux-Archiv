"""Regression: dockable sidebar, mirrored controls and accent-following icons."""
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QStackedWidget, QWidget

from vitalux import settings, theme
from vitalux.brand import app_icon, sync_installed_icon
from vitalux.glass import AmbientScene, GlassSidebar
from vitalux.sidebar_grip import SidebarGrip
from vitalux.widgets import SidebarToggle
from vitalux.window import MainWindow
from vitalux.pages import OverviewPage
from vitalux.control import PreferencesPage


class Board:
    def refresh_geometry(self, animate=False):
        self.refreshed = True


class Overview:
    def __init__(self):
        self.board = Board()
        self.right = None

    def set_sidebar_side(self, right):
        self.right = right


class TestHost(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, 900, 550)
        self.root = AmbientScene(self)
        self.root.setGeometry(self.rect())
        self._outer_layout = QHBoxLayout(self.root)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._sidebar_right = False
        self._sidebar_motion = None
        self._sidebar_collapsed = False
        self.sidebar = GlassSidebar(self.root)
        self.sidebar.setFixedWidth(250)
        self.stack = QStackedWidget(self.root)
        self.stack.addWidget(QWidget())
        self._outer_layout.addWidget(self.sidebar)
        self._outer_layout.addWidget(self.stack, 1)
        self.collapse_button = SidebarToggle(self.sidebar)
        self.sidebar.set_toggle_button(self.collapse_button)
        self.sidebar_grip = SidebarGrip(self.sidebar)
        self.sidebar.set_drag_handle(self.sidebar_grip)
        self.sidebar_grip.dockRequested.connect(self.set_sidebar_position)
        self.pages = [('Übersicht', Overview())]
        self._apply_sidebar_state()

    def centralWidget(self):
        return self.root

    def _apply_sidebar_state(self):
        self.sidebar.setFixedWidth(74 if self._sidebar_collapsed else 250)
        self.sidebar.set_side(self._sidebar_right)
        self.sidebar_grip.set_right(self._sidebar_right)
        self.collapse_button.set_right_side(self._sidebar_right)

    def set_sidebar_position(self, right):
        MainWindow.set_sidebar_position(self, right)


def main():
    app = QApplication.instance() or QApplication([])
    theme.set_mode('glass')
    previous = settings.PATH
    old_xdg = os.environ.get('XDG_DATA_HOME')
    try:
        with tempfile.TemporaryDirectory() as temp:
            settings.PATH = os.path.join(temp, 'prefs.json')
            settings.set('background_animate', False)
            host = TestHost()
            host.show()
            host.root.show()
            app.processEvents()
            assert host.sidebar.x() == 0
            assert host.collapse_button.x() > host.sidebar.width() / 2
            assert host.sidebar_grip.x() < host.collapse_button.x()
            # User clicks the grip to flip; release across midpoint supports
            # actual drag-and-drop with the same signal.
            QTest.mouseClick(host.sidebar_grip, Qt.LeftButton)
            app.processEvents()
            assert host._sidebar_right
            assert settings.get('sidebar_position') == 'right'
            assert host.sidebar.x() > host.stack.x()
            assert host.collapse_button.x() < host.sidebar.width() / 2
            assert host.sidebar_grip.x() > host.collapse_button.x()
            assert host.pages[0][1].right is True
            QTest.mouseClick(host.sidebar_grip, Qt.LeftButton)
            app.processEvents()
            assert not host._sidebar_right
            assert settings.get('sidebar_position') == 'left'

            # The dashboard's own editor arrow moves to the opposite edge.
            fake_distro = {'name': 'Test Linux', 'version': '1.0', 'short': 'Test', 'color': '#4f8cff'}
            page = OverviewPage(fake_distro, QPixmap(96, 96))
            page.resize(850, 720)
            page.show()
            app.processEvents()
            old_x = page.layout_toggle.x()
            page.set_sidebar_side(True)
            app.processEvents()
            assert page.layout_toggle.x() < old_x
            assert page._sidebar_on_right
            page.set_sidebar_side(False)
            assert page.layout_toggle.x() == old_x
            page.layout_toggle._hover_frame(1.0)
            page.layout_toggle.setFocus()
            page.layout_toggle.reset_highlight()
            assert page.layout_toggle._hover_amount == 0.0
            assert not page.layout_toggle.hasFocus()
            page.close()

            # Logo assets for named accent colors really differ in taskbar/tray.
            settings.set('accent', '#4f8cff')
            blue = app_icon().pixmap(64, 64).toImage()
            settings.set('accent', '#a78bfa')
            violet = app_icon().pixmap(64, 64).toImage()
            assert blue != violet
            assert PreferencesPage.DEFAULTS['theme'] == 'glass'
            assert PreferencesPage.DEFAULTS['accent'] == '#4f8cff'

            # Only a trusted Vitalux local launcher may have its icon replaced.
            os.environ['XDG_DATA_HOME'] = temp
            appdir = os.path.join(temp, 'applications')
            icon_dir = os.path.join(temp, 'icons', 'hicolor', 'scalable', 'apps')
            os.makedirs(appdir)
            os.makedirs(icon_dir)
            desktop = os.path.join(appdir, 'vitalux.desktop')
            icon = os.path.join(icon_dir, 'vitalux.svg')
            with open(desktop, 'w', encoding='utf-8') as fd:
                fd.write('[Desktop Entry]\nName=Vitalux\nIcon=vitalux\n')
            with open(icon, 'w', encoding='utf-8') as fd:
                fd.write('<svg/>')
            assert sync_installed_icon()
            with open(icon, 'rb') as fd:
                violet_bytes = fd.read()
            settings.set('accent', '#4f8cff')
            assert sync_installed_icon()
            with open(icon, 'rb') as fd:
                assert violet_bytes != fd.read()
            host.close()
    finally:
        settings.PATH = previous
        if old_xdg is None:
            os.environ.pop('XDG_DATA_HOME', None)
        else:
            os.environ['XDG_DATA_HOME'] = old_xdg
    print('Dockable sidebar, layout chevrons, Glass/blue defaults and palette icons: PASS')


if __name__ == '__main__':
    main()
