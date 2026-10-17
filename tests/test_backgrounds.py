"""Native backdrop and tooltip regression tests, including cached glass."""
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QWidget
from vitalux.appearance_slider import AppearanceSlider
from vitalux import backdrops, theme, settings, hover_hints
from vitalux.glass import AmbientScene, GlassSidebar


def run():
    app = QApplication.instance() or QApplication([])
    guard = hover_hints.install(app)
    example = QWidget()
    example.setToolTip('This popup should be suppressed')
    example.show()
    assert guard.eventFilter(example, QHelpEvent(QEvent.ToolTip, QPoint(4, 4), QPoint(4, 4)))
    assert not guard.eventFilter(example, QEvent(QEvent.Enter))

    previous_settings = settings.PATH
    with tempfile.TemporaryDirectory(prefix='vitalux-visuals-') as tmp:
        try:
            settings.PATH = os.path.join(tmp, 'settings.json')
            settings.set('theme', 'glass')
            settings.set('motion', 'smooth')
            settings.set('background_intensity', 60)
            settings.set('background_softness', 65)
            settings.set('background_animate', False)
            theme.set_mode('glass')
            theme.set_accent('#4f8cff')
            scene = AmbientScene()
            scene.resize(640, 400)
            scene.show()
            app.processEvents()
            assert len(backdrops.PRESETS) == 15
            assert not {'aurora', 'obsidian', 'nebula', 'arctic', 'adaptive'} & set(backdrops.KEYS)
            slider = AppearanceSlider()
            slider.resize(230, 42)
            slider.setRange(0, 100)
            slider.setValue(15)
            slider.show()
            app.processEvents()
            first_slider = slider.grab().toImage()
            slider.setValue(85)
            app.processEvents()
            second_slider = slider.grab().toImage()
            assert not first_slider.isNull()
            assert first_slider != second_slider, "Slider handle/rail is not visibly changing"
            slider.close()
            assert [key for key in backdrops.DEFAULT_THEMES] == [
                'dark', 'light', 'glass', 'black_glass', 'minimal']
            for scheme in backdrops.DEFAULT_THEMES:
                assert backdrops.resolve('theme_default', scheme) == scheme
                assert backdrops.resolve('legacy', scheme) == scheme
            assert backdrops.resolve('aurora', 'glass') == 'glass'
            for name in backdrops.KEYS:
                settings.set('background_style', name)
                scene.sync_background()
                app.processEvents()
                image = scene.sharp_backdrop()
                soft = scene.soft_backdrop()
                assert not image.isNull() and not soft.isNull(), name
                assert image.size() == scene.size(), name
                assert soft.size() == scene.size(), name
                assert not scene.grab().isNull(), name

            # The five matching originals stay available and keep their names.
            for key in backdrops.DEFAULT_THEMES:
                settings.set('background_style', key)
                scene.sync_background()
                assert not scene.sharp_backdrop().isNull(), key
            settings.set('background_style', 'theme_default')
            scene.sync_background()
            assert not scene.sharp_backdrop().isNull()
            assert scene._asset_mode == 'glass', "Automatic should use original Glass"
            # The restored frosted sidebar samples the same complete scene,
            # but retains the original softly contrasting material and seam.
            sidebar = GlassSidebar(scene)
            sidebar.resize(170, 290)
            sidebar.move(0, 0)
            sidebar.show()
            app.processEvents()
            for chosen in ('glass', 'light', 'black_glass', 'pearl', 'pastel_rainbow', 'midnight'):
                settings.set('background_style', chosen)
                scene.sync_background()
                app.processEvents()
                full = scene.sharp_backdrop().toImage()
                rail = sidebar.grab().toImage()
                for x, y in ((16, 45), (85, 170), (140, 225)):
                    bg = full.pixelColor(x, y)
                    fg = rail.pixelColor(x, y)
                    delta = max(abs(getattr(bg, k)() - getattr(fg, k)())
                                for k in ('red', 'green', 'blue'))
                    assert delta <= 195, (chosen, x, y, delta, bg.name(), fg.name())
            sidebar.hide()
            sidebar.close()

            # The intensity slider must affect all five built-in wallpapers,
            # not only the new gradient presets.
            for preset in ('dark', 'light', 'glass', 'black_glass', 'minimal'):
                settings.set('background_style', preset)
                settings.set('background_intensity', 0)
                scene.sync_background()
                before = scene.sharp_backdrop().toImage()
                settings.set('background_intensity', 100)
                scene.sync_background()
                after = scene.sharp_backdrop().toImage()
                assert not before.isNull() and not after.isNull(), preset
                assert before != after, ('Intensity ignored for built-in background', preset)
            settings.set('background_intensity', 60)
            settings.set('background_style', 'prism')

            # Every new background palette subtly echoes the accent choice,
            # without losing its predefined light/rainbow/dark identity.
            settings.set('background_style', 'pastel_rainbow')
            scene.sync_background()
            theme.set_accent('#4f8cff')
            original = scene.sharp_backdrop().toImage()
            theme.set_accent('#e34b87')
            changed = scene.sharp_backdrop().toImage()
            assert original != changed

            # Intensity and softness also invalidate the cache.
            settings.set('background_intensity', 0)
            flat = scene.sharp_backdrop().toImage()
            settings.set('background_intensity', 100)
            bright = scene.sharp_backdrop().toImage()
            assert flat != bright
            settings.set('background_softness', 90)
            soft_cache = scene.soft_backdrop()
            assert not soft_cache.isNull()

            # Minimal never pays for the wallpaper; returning to glass must
            # fully restore all caches even if settings stayed unchanged.
            theme.set_mode('minimal')
            scene.set_low_power(True)
            settings.set('background_intensity', 0)
            app.processEvents()
            minimal_dim = scene.grab().toImage()
            settings.set('background_intensity', 100)
            scene.sync_background()
            app.processEvents()
            minimal_bright = scene.grab().toImage()
            assert minimal_dim != minimal_bright, 'Minimal intensity ignored'
            settings.set('background_intensity', 60)
            assert scene._sharp_cache.isNull()
            assert scene._soft_cache.isNull()
            assert not scene._motion_timer.isActive()
            theme.set_mode('glass')
            scene.set_low_power(False)
            assert not scene.sharp_backdrop().isNull()
            assert not scene.soft_backdrop().isNull()

            settings.set('background_animate', True)
            scene.sync_background()
            assert scene._motion_timer.isActive()
            before_animation = scene.sharp_backdrop().toImage()
            for _ in range(9):
                scene._advance_backdrop()
            after_animation = scene.sharp_backdrop().toImage()
            assert before_animation != after_animation, "Animated colors did not move"
            settings.set('motion', 'off')
            scene.sync_background()
            assert not scene._motion_timer.isActive()
            scene.close()
        finally:
            settings.PATH = previous_settings
    example.close()
    print('Native backgrounds, independent styles, caching, animation and hover suppression: PASS')


if __name__ == '__main__':
    run()
