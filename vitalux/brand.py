"""Vitalux Pulse Core identity.

The logo and original, custom-drawn wordmark are packaged SVG vectors.  The
sidebar's animated instance uses the same vector as the desktop app icon.
No external font or image download is required.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSizePolicy, QWidget


_ASSETS = Path(__file__).resolve().parent.parent / "assets"


@lru_cache(maxsize=4)
def _renderer(filename):
    renderer = QSvgRenderer(str(_ASSETS / filename))
    if not renderer.isValid():
        raise RuntimeError(f"Vitalux design asset not readable: {filename}")
    return renderer


def _pixmap(filename, width, height, ratio=1.0):
    width, height = max(1, int(width)), max(1, int(height))
    ratio = max(1.0, float(ratio))
    pixmap = QPixmap(round(width * ratio), round(height * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    _renderer(filename).render(p, QRectF(0, 0, width, height))
    p.end()
    return pixmap


def icon_pixmap(size=96):
    return _pixmap("vitalux-pulse.svg", size, size)


def wordmark_pixmap(width=205, height=44):
    from . import theme
    filename = "vitalux-wordmark-light.svg" if theme.mode() == "light" else "vitalux-wordmark.svg"
    return _pixmap(filename, width, height, ratio=2.0)


def app_icon():
    icon = QIcon()
    for size in (32, 48, 64, 128, 256, 512):
        icon.addPixmap(icon_pixmap(size))
    return icon


class PulseCore(QWidget):
    """Low-power CPU-responsive light orbit around the Vitalux brand symbol.

    All UI changes run in the main Qt thread; the monitoring worker only sends
    its existing, once-per-second CPU sample through the MainWindow signal.
    """
    def __init__(self, size=152, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._cpu = 0.0
        self._display_cpu = 0.0
        self._phase = 0.0
        self.setToolTip("Vitalux · Live CPU activity")
        self._timer = QTimer(self)
        self._timer.setInterval(90)  # ~11 fps, negligible UI overhead
        self._timer.timeout.connect(self._advance)

    def set_cpu_load(self, value):
        try:
            self._cpu = max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            self._cpu = 0.0
        self.setToolTip(f"CPU {self._cpu:.0f}% · Live telemetry")
        if not self._low_power():
            self.update()

    @staticmethod
    def _low_power():
        from . import theme
        return theme.mode() == "minimal"

    def sync_theme(self):
        if self._low_power():
            self._timer.stop()
        elif self.isVisible():
            self._timer.start()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_theme()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _advance(self):
        if self._low_power():
            self._timer.stop()
            return
        # Smooth values so short CPU spikes don't make the animation flicker.
        self._display_cpu += (self._cpu - self._display_cpu) * 0.09
        self._phase = (self._phase + 0.55 + self._display_cpu * 0.009) % 360.0
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        if self._low_power():
            # Retain the recognizable logo; skip the moving halo and orbit.
            _renderer("vitalux-pulse.svg").render(painter, QRectF(self.rect()))
            painter.end()
            return
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(self.width(), self.height())
        left = (self.width() - size) / 2
        top = (self.height() - size) / 2
        rect = QRectF(left, top, size, size)

        # Light reacts to actual load; static artwork stays recognizable.
        strength = min(1.0, self._display_cpu / 100.0)
        aura = QRadialGradient(rect.center(), size * 0.51)
        inner = QColor(70, 213, 255, int(12 + 40 * strength))
        edge = QColor(84, 98, 242, 0)
        aura.setColorAt(0.0, inner)
        aura.setColorAt(0.65, QColor(66, 153, 250, int(4 + 18 * strength)))
        aura.setColorAt(1.0, edge)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(aura))
        painter.drawEllipse(rect)
        _renderer("vitalux-pulse.svg").render(painter, rect)

        # A single slowly travelling highlight on the outer broken circuit.
        painter.save()
        painter.translate(rect.center())
        painter.rotate(self._phase)
        diameter = size * 0.836
        orbit = QRectF(-diameter / 2, -diameter / 2, diameter, diameter)
        highlight = QColor(215, 250, 255, int(45 + 90 * strength))
        painter.setPen(QPen(highlight, max(1.5, size * 0.016), Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(orbit, -14 * 16, 23 * 16)
        painter.restore()

        # A tiny heartbeat at the bottom of the central waveform.
        t = 0.5 + 0.5 * math.sin(math.radians(self._phase * 3.2))
        highlight = QColor(204, 250, 255, int(15 + (30 + 55 * strength) * t))
        painter.setPen(Qt.NoPen)
        painter.setBrush(highlight)
        radius = size * (0.027 + 0.014 * strength) * (0.9 + 0.1 * t)
        painter.drawEllipse(QRectF(rect.left() + size * 132 / 256 - radius,
                                   rect.top() + size * 163 / 256 - radius,
                                   2 * radius, 2 * radius))
        painter.end()
