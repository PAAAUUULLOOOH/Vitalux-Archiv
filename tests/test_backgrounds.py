"""Wallpaper regression: fixed palettes, intrinsic animation and readable colors."""
import os
import sys
import tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QEvent, QPoint, QSize
from PySide6.QtGui import QColor, QHelpEvent
from PySide6.QtWidgets import QApplication, QWidget

from vitalux import backdrops, theme, settings, hover_hints
from vitalux.glass import AmbientScene, GlassSidebar


def run():
    app = QApplication.instance() or QApplication([])
    guard = hover_hints.install(app)
    example = QWidget()
    example.setToolTip('Suppressed')
    example.show()
    assert guard.eventFilter(example, QHelpEvent(QEvent.ToolTip, QPoint(4, 4), QPoint(4, 4)))
    assert not guard.eventFilter(example, QEvent(QEvent.Enter))

    previous = settings.PATH
    with tempfile.TemporaryDirectory(prefix='vitalux-backdrops-') as tmp:
        try:
            settings.PATH = os.path.join(tmp, 'settings.json')
            settings.set('theme', 'glass')
            theme.set_mode('glass')
            theme.set_accent('#4f8cff')
            assert len(backdrops.PRESETS) == 19
            assert backdrops.resolve('legacy', 'glass') == 'glass'
            assert backdrops.resolve('theme_default', 'light') == 'light'
            assert backdrops.ANIMATED_PRESETS == frozenset((
                'animated_sparkle', 'animated_aurora',
                'animated_waves', 'animated_mist'))
            for removed in ('pastel_rainbow', 'animated_rainbow',
                            'animated_fade', 'animated_light'):
                assert removed not in backdrops.KEYS
                assert backdrops.resolve(removed, 'glass') == 'glass'
            assert 'adaptive' in backdrops.KEYS
            assert not {'aurora', 'obsidian', 'nebula', 'arctic'} & set(backdrops.KEYS)

            scene = AmbientScene()
            scene.resize(640, 400)
            scene.show()
            app.processEvents()
            for key in backdrops.KEYS:
                settings.set('background_style', key)
                scene.sync_background()
                sharp = scene.sharp_backdrop()
                soft = scene.soft_backdrop()
                assert not sharp.isNull() and not soft.isNull(), key
                assert sharp.size() == QSize(640, 400), key
                assert not scene.grab().isNull(), key

            # Fixed presets never schedule a wallpaper timer.
            for style in ('theme_default', 'glass', 'pearl', 'prism',
                          'deep_ocean', 'minimal', 'adaptive'):
                settings.set('background_style', style)
                scene.sync_background()
                assert not scene._wallpaper_timer.isActive(), style

            # Funkeln and the three quieter new designs move automatically,
            # even when global UI animations are turned off.
            settings.set('motion', 'off')
            for style in backdrops.ANIMATED_PRESETS:
                settings.set('background_style', style)
                scene.sync_background()
                assert scene._wallpaper_timer.isActive(), style
                first = scene.sharp_backdrop().toImage()
                for _ in range(12):
                    scene._advance_backdrop()
                later = scene.sharp_backdrop().toImage()
                assert first != later, 'Background frozen: ' + style

            # Existing light wallpapers are still light under Glass; neither
            # scene composition nor cards should tint the canvas dark.
            theme.set_mode('glass')
            for style in ('light', 'pearl', 'ice'):
                settings.set('background_style', style)
                scene.sync_background()
                pixel = scene.sharp_backdrop().toImage().pixelColor(320, 190)
                total = pixel.red() + pixel.green() + pixel.blue()
                assert total > 420, (style, pixel.name(), total)
            settings.set('background_style', 'deep_ocean')
            scene.sync_background()
            pixel = scene.sharp_backdrop().toImage().pixelColor(320, 190)
            assert pixel.red() + pixel.green() + pixel.blue() < 420

            # The three replacements share a dark Glass-level mood. Distinct
            # blue/petrol/violet palettes remain visible without neon highlights.
            for style in ('animated_aurora', 'animated_waves', 'animated_mist'):
                settings.set('background_style', style)
                scene.sync_background()
                frame = scene.sharp_backdrop().toImage()
                samples = [frame.pixelColor(x, y) for x, y in (
                    (80, 80), (320, 190), (560, 320), (420, 70), (175, 270))]
                luminance = [int(.2126*c.red() + .7152*c.green() + .0722*c.blue())
                             for c in samples]
                assert 8 < sum(luminance)/len(luminance) < 104, (
                    style, luminance)
                assert max(luminance) < 150, (style, luminance)

            settings.set('background_style', 'adaptive')
            theme.set_accent('#4f8cff')
            blue = scene.sharp_backdrop().toImage()
            theme.set_accent('#ef4444')
            red = scene.sharp_backdrop().toImage()
            assert blue != red

            # Sidebar remains fixed on the left and samples the chosen image.
            rail = GlassSidebar(scene)
            rail.resize(170, 290)
            rail.show()
            app.processEvents()
            assert not rail.grab().isNull()
            rail.close()
            settings.set('background_style', 'minimal')
            theme.set_mode('minimal')
            scene.set_low_power(True)
            assert scene._sharp_cache.isNull()
            assert not scene._wallpaper_timer.isActive()
            scene.close()
        finally:
            settings.PATH = previous
    example.close()
    print('Darker four-animation collection, removed presets, static themes and adaptive hue: PASS')


if __name__ == '__main__':
    run()
