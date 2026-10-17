"""Regression: scroll rendering, wallpaper downsampling and restart readiness."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget

from vitalux import settings, theme, user_background
from vitalux.window import MainWindow
from vitalux.smooth_scroll import AdaptiveScrollArea, frame_interval_ms
from vitalux.widgets import Card


class ScrollHost(QWidget):
    _is_scrolling_card = staticmethod(MainWindow._is_scrolling_card)
    _optimize_scroll_surfaces = MainWindow._optimize_scroll_surfaces


class StopTimer:
    def stop(self):
        self.stopped = True


class RestartHost:
    def __init__(self, allowed):
        self.restart_requested = False
        self._force_quit = False
        self._tray_click_timer = StopTimer()
        self.allowed = allowed

    def close(self):
        return self.allowed


def run():
    app = QApplication.instance() or QApplication([])
    saved_path = settings.PATH
    with tempfile.TemporaryDirectory(prefix='vitalux-scroll-test-') as temporary:
        try:
            settings.PATH = str(Path(temporary) / 'settings.json')
            theme.set_mode('glass')
            host = ScrollHost()
            scroll = QScrollArea(host)
            scroll.resize(470, 300)
            scroll.setWidgetResizable(True)
            page = QWidget()
            layout = QVBoxLayout(page)
            card = Card('Scrolled card')
            layout.addWidget(card)
            scroll.setWidget(page)
            standalone = Card('Standalone card')
            standalone.setParent(host)
            assert card.graphicsEffect().isEnabled()
            host._optimize_scroll_surfaces()
            assert not card.graphicsEffect().isEnabled(), 'Scrolled shadow is still expensive'
            assert standalone.graphicsEffect().isEnabled(), 'Unscrolled card lost its shadow'
            host.close()

            # Mouse-wheel animation follows the actual display mode rather than
            # imposing a fixed 60 Hz loop. No timer runs while idle.
            assert frame_interval_ms(60) == 17
            assert frame_interval_ms(144) == 7
            assert frame_interval_ms(165) == 6
            assert frame_interval_ms(240) == 4
            assert frame_interval_ms(0) == 17
            assert frame_interval_ms(float('nan')) == 17
            smooth = AdaptiveScrollArea()
            smooth.resize(470, 300)
            tall = QWidget()
            tall.setMinimumSize(450, 1200)
            smooth.setWidget(tall)
            smooth.show()
            app.processEvents()
            assert smooth.verticalScrollBar().maximum() > 0
            assert not smooth._frame_timer.isActive()
            wheel = QWheelEvent(QPointF(20, 20), QPointF(20, 20),
                                QPoint(), QPoint(0, -120), Qt.NoButton,
                                Qt.NoModifier, Qt.NoScrollPhase, False)
            smooth.wheelEvent(wheel)
            assert wheel.isAccepted()
            assert smooth._frame_timer.isActive()
            assert smooth._scroll_targets[smooth.verticalScrollBar()] > 0
            # A precision touchpad bypasses the smoother and cancels pending
            # interpolation, so high-resolution gesture input is not delayed.
            touchpad = QWheelEvent(QPointF(20, 20), QPointF(20, 20),
                                   QPoint(0, -20), QPoint(), Qt.NoButton,
                                   Qt.NoModifier, Qt.NoScrollPhase, False)
            smooth.wheelEvent(touchpad)
            assert not smooth._frame_timer.isActive()
            assert not smooth._scroll_targets
            smooth.close()

            # Two distinctly sized windows can reuse decoded images.
            image = QImage(1600, 960, QImage.Format_RGB32)
            image.fill(QColor('#307bd9'))
            filename = Path(temporary) / 'wallpaper.png'
            assert image.save(str(filename))
            entry = user_background.import_image(filename)
            path = user_background.image_path(entry['file'])
            for placement in ('cover', 'contain', 'stretch', 'center', 'tile'):
                bitmap = user_background.draw(QSize(340, 180), entry['file'], placement)
                assert bitmap.size() == QSize(340, 180), placement
            source = user_background._scaled_image(
                str(path), path.stat().st_mtime_ns, path.stat().st_size,
                340, 180, 'cover')
            assert max(source.width(), source.height()) < 1600, 'Full-size decode was not reduced'
            hit_count = user_background._scaled_image.cache_info().hits
            user_background.draw(QSize(340, 180), entry['file'], 'cover')
            assert user_background._scaled_image.cache_info().hits > hit_count

            ready = RestartHost(allowed=True)
            assert MainWindow.restart_for_renderer(ready)
            assert ready.restart_requested and ready._force_quit
            blocked = RestartHost(allowed=False)
            assert not MainWindow.restart_for_renderer(blocked)
            assert not blocked.restart_requested and not blocked._force_quit
        finally:
            settings.PATH = saved_path


if __name__ == '__main__':
    run()
    print('Scroll renderer, scaled wallpaper and restart regression: OK')
