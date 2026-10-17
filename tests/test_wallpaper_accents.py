"""Regression: wallpaper colors follow imported photos and theme changes."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QTabWidget

from vitalux import settings, theme, wallpaper_accents, user_background, i18n
from vitalux.control import PreferencesPage
from vitalux.theme import accent


class FakeWindow:
    def __init__(self):
        self._tray = object()
        self.last_sample = None
        self.distro = {'color': '#4f8cff'}
        self.applied = 0
        self.render_backend_active = 'software'
        self.restarts = 0

    def apply_appearance(self):
        theme.set_mode(settings.get('theme', 'glass'))
        color = wallpaper_accents.resolve_accent(settings.get('accent', '#4f8cff'),
                                                  self.distro['color'])
        theme.set_accent(color)
        self.applied += 1
        if hasattr(self, 'page'):
            self.page.refresh_appearance()

    def restart_for_renderer(self):
        self.restarts += 1
        return True

    def set_interval(self, value):
        pass


def run():
    app = QApplication.instance() or QApplication([])
    old_path = settings.PATH
    old_lang = i18n.lang()
    with tempfile.TemporaryDirectory(prefix='wallpaper-colors-') as temp:
        try:
            settings.PATH = str(Path(temp) / 'settings.json')
            theme.set_mode('glass')
            theme.set_accent('#4f8cff')

            first = QImage(120, 60, QImage.Format_RGB32)
            first.fill(QColor('#1078e9'))
            blue = Path(temp) / 'blue.png'
            assert first.save(str(blue))
            second = QImage(120, 60, QImage.Format_RGB32)
            second.fill(QColor('#db4533'))
            red = Path(temp) / 'red.png'
            assert second.save(str(red))

            blue_copy = user_background.import_image(blue)
            red_copy = user_background.import_image(red)
            settings.set('custom_backgrounds', [blue_copy, red_copy])
            settings.set('custom_background_selected', blue_copy['file'])
            settings.set('custom_background_fit', 'cover')
            settings.set('background_style', 'custom_image')
            suggestions = wallpaper_accents.suggestions()
            assert len(suggestions) == 5 and all(QColor(c).isValid() for c in suggestions)
            blue_hue = QColor(suggestions[0]).hue()
            assert 185 <= blue_hue <= 245, suggestions

            settings.set('accent', wallpaper_accents.AUTO)
            assert wallpaper_accents.resolve_accent(wallpaper_accents.AUTO) == suggestions[0]

            win = FakeWindow()
            page = PreferencesPage(win)
            win.page = page
            page.show()
            app.processEvents()
            assert not page.findChildren(QTabWidget), 'Unwanted accent tabs'
            assert page.accent_combo.currentData() == wallpaper_accents.AUTO
            assert page.accent_combo.findData(wallpaper_accents.AUTO) >= 0
            assert all(page.accent_combo.findData(f'wallpaper_{i}') == -1
                       for i in range(5)), 'Numbered palettes still visible'
            page.resize(560, 900)
            app.processEvents()
            assert page.accent_combo.width() >= 80, 'Combo became too narrow'
            # Restart button appears only while switching renderer.
            assert not page.render_restart_button.isVisible()
            page.render_combo.setCurrentIndex(page.render_combo.findData('opengl'))
            assert page.render_restart_button.isVisible()
            page.render_restart_button.click()
            assert win.restarts == 1
            page.render_combo.setCurrentIndex(page.render_combo.findData('software'))
            assert not page.render_restart_button.isVisible()
            win.apply_appearance()

            # Change wallpaper with automatic accent retained.
            settings.set('custom_background_selected', red_copy['file'])
            page.refresh_background_images()
            win.apply_appearance()
            red_suggestions = wallpaper_accents.suggestions()
            assert 0 <= QColor(red_suggestions[0]).hue() <= 28, red_suggestions
            assert accent() != suggestions[0]
            assert settings.get('accent') == wallpaper_accents.AUTO

            # Manual choices remain fully available.
            page.accent_combo.setCurrentIndex(page.accent_combo.findData('#4f8cff'))
            assert settings.get('accent') == '#4f8cff'
            # Previous 1–5 choices migrate to the single automatic choice.
            settings.set('accent', 'wallpaper_3')
            legacy = PreferencesPage(win)
            assert legacy.accent_combo.currentData() == wallpaper_accents.AUTO
            assert settings.get('accent') == wallpaper_accents.AUTO
            legacy.close()

            # Built-in backgrounds also yield stable results for all five themes.
            for mode in ('glass', 'dark', 'light', 'black_glass', 'minimal'):
                theme.set_mode(mode)
                settings.set('background_style', 'theme_default')
                a = wallpaper_accents.suggestions()
                b = wallpaper_accents.suggestions()
                assert a == b and len(a) == 5 and all(QColor(c).isValid() for c in a)

            # New single automatic choice is translatable.
            i18n.set_lang('en')
            from vitalux.i18n import tr
            assert tr('Hintergrundfarbe automatisch') == 'Automatically match background'
            page.close()
        finally:
            settings.PATH = old_path
            i18n.set_lang(old_lang)


if __name__ == '__main__':
    run()
    print('Wallpaper-matched accent regression passed')
