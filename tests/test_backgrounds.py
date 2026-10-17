"""Native backdrop and tooltip regression tests, including cached glass."""
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QWidget
from vitalux import backdrops, theme, settings, hover_hints
from vitalux.glass import AmbientScene


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
            assert len(backdrops.PRESETS) == 6
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

            # The user accent must change the adaptive background without
            # requiring restart, even if window dimensions do not change.
            settings.set('background_style', 'adaptive')
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
