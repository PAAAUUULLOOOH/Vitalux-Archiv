"""Vitalux Pulse Core identity.

The logo and original, custom-drawn wordmark are packaged SVG vectors.  The
sidebar's animated instance uses the same vector as the desktop app icon.
No external font or image download is required.
"""
from __future__ import annotations

import math
import os
from tempfile import NamedTemporaryFile
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSizePolicy, QWidget


_ASSETS = Path(__file__).resolve().parent.parent / "assets"


@lru_cache(maxsize=48)
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


# Only predefined accent choices receive new, *separately authored SVG assets*.
# 'Distribution' and arbitrary custom colors retain the original artwork.
ACCENT_VARIANTS = {
    "#4f8cff": "blue",
    "#52d3ff": "cyan",
    "#a78bfa": "violet",
    "#73ba25": "green",
    "#f59e0b": "orange",
    "#facc15": "yellow",
    "#ef4444": "red",
    "#f472b6": "pink",
}


def _selected_variant():
    from . import settings
    chosen = settings.get("accent", "#4f8cff")
    return ACCENT_VARIANTS.get(str(chosen).lower())


def _brand_asset(icon):
    from . import theme
    variant = _selected_variant()
    if icon:
        return f"brand/vitalux-pulse-{variant}.svg" if variant else "vitalux-pulse.svg"
    if variant:
        suffix = "-light" if theme.mode() == "light" else ""
        return f"brand/vitalux-wordmark-{variant}{suffix}.svg"
    return "vitalux-wordmark-light.svg" if theme.mode() == "light" else "vitalux-wordmark.svg"


def themed_icon_pixmap(size=152):
    return _pixmap(_brand_asset(icon=True), size, size)


def wordmark_pixmap(width=205, height=44):
    return _pixmap(_brand_asset(icon=False), width, height, ratio=2.0)


def app_icon():
    icon = QIcon()
    for size in (32, 48, 64, 128, 256, 512):
        icon.addPixmap(themed_icon_pixmap(size))
    return icon


def sync_installed_icon():
    """Keep the user-installed KDE launcher icon in sync with the accent.

    A distinct icon *path* per preset avoids KDE's stale hicolor/desktop-entry
    icon cache. No shared/system desktop file is touched.
    """
    import re
    base = Path(os.environ.get('XDG_DATA_HOME') or
                (Path.home() / '.local' / 'share'))
    desktop = base / 'applications' / 'vitalux.desktop'
    directory = base / 'icons' / 'hicolor' / 'scalable' / 'apps'
    original = directory / 'vitalux.svg'
    if (not desktop.is_file() or desktop.is_symlink()
            or not original.is_file() or original.is_symlink()
            or directory.is_symlink()):
        return False
    try:
        data = desktop.read_text(encoding='utf-8')
        if 'Name=Vitalux' not in data:
            return False
        found = re.search(r'^Icon=(.*)$', data, flags=re.MULTILINE)
        if not found:
            return False
        old_icon = found.group(1).strip()
        if old_icon != 'vitalux' and not (
                old_icon.startswith(str(directory / 'vitalux-'))
                and old_icon.endswith('.svg')):
            return False
        variant = _selected_variant()
        source = _ASSETS / _brand_asset(icon=True)
        if not source.is_file():
            return False
        # The selected color changes the icon *filename*, not just its bytes:
        # Plasma consequently refreshes pinned launchers more reliably.
        target = directory / ('vitalux-' + (variant or 'original') + '.svg')
        new_bytes = source.read_bytes()
        if not target.is_file() or target.read_bytes() != new_bytes:
            with NamedTemporaryFile(dir=directory, prefix='.vitalux-color-',
                                    suffix='.svg', delete=False) as fd:
                tmp = Path(fd.name)
                fd.write(new_bytes)
                fd.flush()
                os.fsync(fd.fileno())
            try:
                os.replace(tmp, target)
            finally:
                if tmp.exists():
                    tmp.unlink()
        updated = re.sub(r'^Icon=.*$', 'Icon=' + str(target), data,
                         count=1, flags=re.MULTILINE)
        if updated != data:
            with NamedTemporaryFile(dir=desktop.parent,
                                    prefix='.vitalux-entry-',
                                    suffix='.desktop', delete=False) as fd:
                tmp = Path(fd.name)
                fd.write(updated.encode('utf-8'))
                fd.flush()
                os.fsync(fd.fileno())
            try:
                os.chmod(tmp, desktop.stat().st_mode & 0o777)
                os.replace(tmp, desktop)
            finally:
                if tmp.exists():
                    tmp.unlink()
        return True
    except OSError:
        # Window and tray color changes still work without desktop integration.
        return False


class TrayPulse(QObject):
    """Low-frequency, accent-matched animated glow around the real tray logo.

    A standard QIcon is restored immediately after an update is installed.
    There are no extra notifications or background threads.
    """

    def __init__(self, tray, parent=None):
        super().__init__(parent)
        self.tray = tray
        self.active = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(190)
        self._timer.timeout.connect(self._advance)

    def _render(self, phase):
        from . import theme
        size = 64
        px = QPixmap(size, size)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        beat = .5 + .5 * math.sin(phase)
        color = QColor(theme.accent())
        glow = QRadialGradient(QPointF(32, 32), 31)
        center = QColor(color); center.setAlpha(int(88 + 145 * beat))
        mid = QColor(color); mid.setAlpha(int(40 + 100 * beat))
        edge = QColor(color); edge.setAlpha(0)
        glow.setColorAt(0, center)
        glow.setColorAt(.62, mid)
        glow.setColorAt(1, edge)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QRectF(0, 0, 64, 64))
        ring = QColor(color).lighter(130)
        ring.setAlpha(int(115 + 140 * beat))
        p.setPen(QPen(ring, 2 + beat * 2.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(3, 3, 58, 58))
        p.drawPixmap(8, 8, 48, 48, themed_icon_pixmap(48))
        # A visible light pip survives Plasma's 22px tray scaling.
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, int(75 + 180*beat)))
        p.drawEllipse(QPointF(54, 10), 2 + beat * 1.8, 2 + beat * 1.8)
        p.end()
        return px

    def _advance(self):
        if not self.active:
            return
        self._phase = (self._phase + .38) % (2 * math.pi)
        pix = self._render(self._phase)
        icon = QIcon()
        icon.addPixmap(pix)
        # Explicit small render sizes avoid smooth-downscaling away the glow.
        for target in (22, 32, 48):
            icon.addPixmap(pix.scaled(target, target, Qt.KeepAspectRatio,
                                      Qt.SmoothTransformation))
        self.tray.setIcon(icon)

    def set_active(self, active):
        active = bool(active)
        if self.active == active:
            return
        self.active = active
        if active:
            self._phase = 0.0
            self._advance()
            self._timer.start()
        else:
            self._timer.stop()
            self.tray.setIcon(app_icon())

    def refresh(self):
        if self.active:
            self._advance()

    def stop(self):
        self.set_active(False)


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
        self._update_available = False
        self._update_clock = 0.0
        self.setToolTip("Vitalux · Live CPU activity")
        self._timer = QTimer(self)
        self._timer.setInterval(90)  # ~11 fps, negligible UI overhead
        self._timer.timeout.connect(self._advance)

    def set_update_available(self, available):
        status = bool(available)
        if status != self._update_available:
            self._update_available = status
            self.sync_theme()

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
        if self._low_power() and not self._update_available:
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
        if self._low_power() and not self._update_available:
            self._timer.stop()
            return
        # Smooth values so short CPU spikes don't make the animation flicker.
        self._update_clock = (self._update_clock + .17) % (2 * math.pi)
        self._display_cpu += (self._cpu - self._display_cpu) * 0.09
        self._phase = (self._phase + 0.55 + self._display_cpu * 0.009) % 360.0
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        if self._low_power() and not self._update_available:
            # Retain the recognizable logo; skip the moving halo and orbit.
            size = min(self.width(), self.height())
            _renderer(_brand_asset(icon=True)).render(painter, QRectF(self.rect()))
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
        from . import theme
        tint = QColor(theme.accent())
        inner = QColor(tint)
        inner.setAlpha(int(12 + 40 * strength))
        edge = QColor(theme.secondary_accent())
        edge.setAlpha(0)
        aura.setColorAt(0.0, inner)
        middle = QColor(tint)
        middle.setAlpha(int(4 + 18 * strength))
        aura.setColorAt(0.65, middle)
        aura.setColorAt(1.0, edge)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(aura))
        painter.drawEllipse(rect)
        if self._update_available:
            # The same bright breathing glow used by the system tray.
            beat = .5 + .5 * math.sin(self._update_clock)
            ring_glow = QRadialGradient(rect.center(), size * .55)
            bloom = QColor(tint); bloom.setAlpha(int(70 + 95 * beat))
            middle = QColor(tint); middle.setAlpha(int(27 + 63 * beat))
            clear = QColor(tint); clear.setAlpha(0)
            ring_glow.setColorAt(0, bloom)
            ring_glow.setColorAt(.53, middle)
            ring_glow.setColorAt(1, clear)
            painter.setBrush(QBrush(ring_glow))
            painter.drawEllipse(rect)
        _renderer(_brand_asset(icon=True)).render(painter, rect)

        if self._update_available:
            # A restrained heartbeat around the main Vitalux mark.
            beat = .5 + .5 * math.sin(self._update_clock)
            halo = QColor(theme.accent())
            halo.setAlpha(int(65 + 105 * beat))
            painter.setPen(QPen(halo, 1.3 + beat * 1.2))
            painter.setBrush(Qt.NoBrush)
            span = size * (.887 + beat * .019)
            painter.drawEllipse(QRectF(rect.center().x()-span/2,
                                       rect.center().y()-span/2, span, span))

        # A single slowly travelling highlight on the outer broken circuit.
        painter.save()
        painter.translate(rect.center())
        painter.rotate(self._phase)
        diameter = size * 0.836
        orbit = QRectF(-diameter / 2, -diameter / 2, diameter, diameter)
        highlight = QColor(theme.accent())
        highlight.setAlpha(int(45 + 90 * strength))
        painter.setPen(QPen(highlight, max(1.5, size * 0.016), Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(orbit, -14 * 16, 23 * 16)
        painter.restore()

        # A tiny heartbeat at the bottom of the central waveform.
        t = 0.5 + 0.5 * math.sin(math.radians(self._phase * 3.2))
        highlight = QColor(theme.secondary_accent())
        highlight.setAlpha(int(15 + (30 + 55 * strength) * t))
        painter.setPen(Qt.NoPen)
        painter.setBrush(highlight)
        radius = size * (0.027 + 0.014 * strength) * (0.9 + 0.1 * t)
        painter.drawEllipse(QRectF(rect.left() + size * 132 / 256 - radius,
                                   rect.top() + size * 163 / 256 - radius,
                                   2 * radius, 2 * radius))
        painter.end()
