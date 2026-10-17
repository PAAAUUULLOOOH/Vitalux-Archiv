"""Regression: permanently left sidebar and color-responsive application icons."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from vitalux import settings, theme
from vitalux.brand import app_icon, sync_installed_icon
from vitalux.glass import AmbientScene, GlassSidebar
from vitalux.widgets import SidebarToggle
from vitalux.window import MainWindow
from vitalux.pages import OverviewPage
from vitalux.control import PreferencesPage


def main():
    app = QApplication.instance() or QApplication([])
    theme.set_mode('glass')
    prior = settings.PATH
    old_xdg = os.environ.get('XDG_DATA_HOME')
    try:
        with tempfile.TemporaryDirectory() as temp:
            settings.PATH = str(Path(temp) / 'prefs.json')
            root = AmbientScene()
            root.resize(820, 540)
            side = GlassSidebar(root)
            side.resize(250, 540)
            side.move(0, 0)
            toggle = SidebarToggle(side)
            side.set_toggle_button(toggle)
            root.show()
            side.show()
            app.processEvents()

            # No docking controls or methods survive in the app.
            assert not hasattr(MainWindow, 'set_sidebar_position')
            assert not hasattr(side, 'set_side')
            assert not hasattr(side, 'set_drag_handle')
            assert not hasattr(side, '_drag_handle')
            assert not hasattr(toggle, 'set_right_side')
            assert toggle.x() > side.width() // 2

            # Dashboard edit control is fixed on the right again.
            distro = {'name': 'Test Linux', 'version': '1.0',
                      'short': 'Test', 'color': '#4f8cff'}
            page = OverviewPage(distro, QPixmap(96, 96))
            page.resize(850, 720)
            page.show()
            app.processEvents()
            assert page.layout_toggle.x() > page.width() // 2
            assert not hasattr(page, 'set_sidebar_side')
            page.layout_toggle._hover_frame(1)
            page.layout_toggle.setFocus()
            page.layout_toggle.reset_highlight()
            assert page.layout_toggle._hover_amount == 0.0
            assert not page.layout_toggle.hasFocus()
            page.close()

            # Every predefined preset changes the app and tray artwork,
            # including newly added Yellow and Red.
            schemes = ('#4f8cff', '#52d3ff', '#a78bfa',
                       '#73ba25', '#f59e0b', '#facc15',
                       '#ef4444', '#f472b6')
            frames = []
            for color in schemes:
                settings.set('accent', color)
                theme.set_accent(color)
                img = app_icon().pixmap(64, 64).toImage()
                assert not img.isNull(), color
                frames.append(img)
            assert all(frames[i] != frames[j]
                       for i in range(len(frames))
                       for j in range(i+1, len(frames)))
            assert PreferencesPage.DEFAULTS['theme'] == 'glass'
            assert PreferencesPage.DEFAULTS['accent'] == '#4f8cff'

            # A per-color icon filename works around KDE caching.
            os.environ['XDG_DATA_HOME'] = temp
            appl = Path(temp) / 'applications'
            icons = Path(temp) / 'icons' / 'hicolor' / 'scalable' / 'apps'
            appl.mkdir()
            icons.mkdir(parents=True)
            desktop = appl / 'vitalux.desktop'
            (icons / 'vitalux.svg').write_text('<svg/>', encoding='utf-8')
            desktop.write_text('[Desktop Entry]\nName=Vitalux\nIcon=vitalux\n',
                               encoding='utf-8')
            for color, suffix in (('#facc15', 'yellow'), ('#ef4444', 'red'),
                                  ('#4f8cff', 'blue')):
                settings.set('accent', color)
                assert sync_installed_icon()
                expected = icons / ('vitalux-' + suffix + '.svg')
                assert expected.is_file()
                assert 'Icon=' + str(expected) in desktop.read_text()
            root.close()
    finally:
        settings.PATH = prior
        if old_xdg is None:
            os.environ.pop('XDG_DATA_HOME', None)
        else:
            os.environ['XDG_DATA_HOME'] = old_xdg
    print('Fixed-left sidebar, editor arrow, yellow/red palette and KDE icons: PASS')


if __name__ == '__main__':
    main()
