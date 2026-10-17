"""Regression: wallpaper colors follow imported photos and theme changes."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from vitalux import settings, theme, wallpaper_accents, user_background, i18n
from vitalux.control import PreferencesPage
from vitalux.theme import accent


class FakeWindow:
    def __init__(self):
        self._tray = object()
        self.last_sample = None
        self.distro = {'color': '#4f8cff'}
        self.applied = 0

    def apply_appearance(self):
        theme.set_mode(settings.get('theme', 'glass'))
        color = wallpaper_accents.resolve_accent(settings.get('accent', '#4f8cff'),
                                                  self.distro['color'])
        theme.set_accent(color)
        self.applied += 1
        if hasattr(self, 'page'):
            self.page.refresh_appearance()

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
            assert page.accent_tabs.count() == 2
            assert page.accent_tabs.tabText(1) == 'Passend zum Hintergrund'
            assert page.accent_tabs.currentIndex() == 1
            assert page.wallpaper_auto_button.isChecked()
            assert len(page.wallpaper_color_buttons) == 5
            win.apply_appearance()

            # Change wallpaper with automatic accent retained.
            settings.set('custom_background_selected', red_copy['file'])
            page.refresh_background_images()
            win.apply_appearance()
            red_suggestions = wallpaper_accents.suggestions()
            assert 0 <= QColor(red_suggestions[0]).hue() <= 28, red_suggestions
            assert accent() != suggestions[0]
            assert settings.get('accent') == wallpaper_accents.AUTO

            # Pick the second suggested swatch; it should track another wallpaper.
            page.wallpaper_color_buttons[1].click()
            assert settings.get('accent') == 'wallpaper_1'
            assert QColor(wallpaper_accents.resolve_accent('wallpaper_1')).isValid()
            page.accent_combo.setCurrentIndex(page.accent_combo.findData('#4f8cff'))
            assert settings.get('accent') == '#4f8cff'

            # Built-in backgrounds also yield stable results for all five themes.
            for mode in ('glass', 'dark', 'light', 'black_glass', 'minimal'):
                theme.set_mode(mode)
                settings.set('background_style', 'theme_default')
                a = wallpaper_accents.suggestions()
                b = wallpaper_accents.suggestions()
                assert a == b and len(a) == 5 and all(QColor(c).isValid() for c in a)

            # English names inside the new accent tabs are translated.
            i18n.set_lang('en')
            page.refresh_appearance()
            assert page.accent_tabs.tabText(1) == 'Match background'
            page.close()
        finally:
            settings.PATH = old_path
            i18n.set_lang(old_lang)


if __name__ == '__main__':
    run()
    print('Wallpaper-matched accent regression passed')
