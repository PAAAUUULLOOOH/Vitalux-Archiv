"""Smooth, refresh-rate-aware mouse-wheel scrolling for Qt Widgets.

Only coarse wheel steps are interpolated. Touchpad pixel deltas, keyboard
navigation and scroll-bar drags retain Qt's native low-latency behaviour.
The target rate follows the *configured* refresh rate of the actual screen;
this module never changes system display modes or promises compositor FPS.
"""
import math

from PySide6.QtCore import QElapsedTimer, Qt, QTimer
from PySide6.QtWidgets import QApplication, QScrollArea

from . import motion


def frame_interval_ms(refresh_rate):
    """Nearest practical millisecond timer interval for the active screen."""
    try:
        hz = float(refresh_rate)
    except (TypeError, ValueError):
        hz = 60.0
    if not math.isfinite(hz) or hz < 24:
        hz = 60.0
    return max(2, round(1000.0 / hz))


class AdaptiveScrollArea(QScrollArea):
    """Smooth mouse-wheel steps only, without a permanent rendering loop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scroll_targets = {}
        self._clock = QElapsedTimer()
        self._frame_timer = QTimer(self)
        self._frame_timer.setTimerType(Qt.PreciseTimer)
        self._frame_timer.setInterval(frame_interval_ms(60))
        self._frame_timer.timeout.connect(self._advance_scroll)
        self._bound_window = None
        self._bound_screen = None
        self.verticalScrollBar().sliderPressed.connect(self._cancel_scroll)
        self.horizontalScrollBar().sliderPressed.connect(self._cancel_scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self._bind_display()

    def _bind_display(self):
        # QWidget children have no windowHandle; use the top-level QWindow.
        window = self.window().windowHandle()
        if window is not self._bound_window:
            if self._bound_window is not None:
                try:
                    self._bound_window.screenChanged.disconnect(self._screen_changed)
                except (RuntimeError, TypeError):
                    pass
            self._bound_window = window
            if window is not None:
                window.screenChanged.connect(self._screen_changed)
        screen = window.screen() if window is not None else QApplication.primaryScreen()
        if screen is not self._bound_screen:
            if self._bound_screen is not None:
                try:
                    self._bound_screen.refreshRateChanged.disconnect(self._update_timing)
                except (RuntimeError, TypeError):
                    pass
            self._bound_screen = screen
            if screen is not None:
                screen.refreshRateChanged.connect(self._update_timing)
        self._update_timing()

    def _screen_changed(self, _screen):
        self._bind_display()

    def _update_timing(self, *_):
        screen = self._bound_screen
        self._frame_timer.setInterval(frame_interval_ms(
            screen.refreshRate() if screen is not None else 60.0))

    def _cancel_scroll(self):
        self._frame_timer.stop()
        self._scroll_targets.clear()

    def wheelEvent(self, event):
        # Pixel-precise touchpads and disabled/reduced-interface modes use Qt's
        # normal event path: no interpolation and no extra input latency.
        if (not motion.enabled() or not event.pixelDelta().isNull()
                or bool(event.modifiers() & Qt.ControlModifier)):
            self._cancel_scroll()
            super().wheelEvent(event)
            return

        delta = event.angleDelta()
        horizontal = abs(delta.x()) > abs(delta.y())
        if event.modifiers() & Qt.ShiftModifier and delta.y():
            horizontal = True
        bar = self.horizontalScrollBar() if horizontal else self.verticalScrollBar()
        amount = delta.x() if horizontal and delta.x() else delta.y()
        if not amount or bar.maximum() <= bar.minimum():
            super().wheelEvent(event)
            return

        lines = max(1, QApplication.wheelScrollLines())
        distance = (amount / 120.0) * max(1, bar.singleStep()) * lines
        origin = self._scroll_targets.get(bar, float(bar.value()))
        destination = max(bar.minimum(), min(bar.maximum(), origin - distance))
        if abs(destination - bar.value()) < 0.5:
            # Preserve wheel-event propagation from already reached edges.
            event.ignore()
            return

        self._scroll_targets[bar] = destination
        if not self._frame_timer.isActive():
            self._clock.start()
            self._frame_timer.start()
        event.accept()

    def _advance_scroll(self):
        elapsed = max(0.001, min(0.2, self._clock.restart() / 1000.0))
        # Time-based damping keeps scrolling consistent at 60, 144 or 240 Hz
        # and catches up rather than accumulating frames when Qt is busy.
        tau = 0.035 if motion.level() == "reduced" else 0.060
        fraction = 1.0 - math.exp(-elapsed / tau)
        for bar, target in list(self._scroll_targets.items()):
            target = max(bar.minimum(), min(bar.maximum(), target))
            previous = bar.value()
            remaining = target - previous
            next_value = round(previous + remaining * fraction)
            if abs(remaining) <= 1 or next_value == previous:
                next_value = round(target)
            bar.setValue(next_value)
            if next_value == round(target):
                self._scroll_targets.pop(bar, None)
        if not self._scroll_targets:
            self._frame_timer.stop()
