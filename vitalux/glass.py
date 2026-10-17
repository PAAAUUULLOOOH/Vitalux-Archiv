"""Native glass materials for the Vitalux Qt6 interface.

Glass and Black Glass sample a cached, softly blurred in-app backdrop,
matching each card's actual position. The whole window stays opaque.
No KWin compositor transparency or blur-behind is required.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QFrame, QWidget
from . import theme

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def rgba(r, g, b, a):
    return QColor(r, g, b, a)


def rounded(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


class AmbientScene(QWidget):
    """Single stable image under every translucent Qt widget, cached on resize."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('root')
        self.setAutoFillBackground(False)
        # Every theme repaints all its pixels. The application window is opaque.
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self._asset_mode = None
        self._wallpaper = QPixmap()
        self._soft_wallpaper = QPixmap()
        self._sharp_cache = QPixmap()
        self._soft_cache = QPixmap()
        self._cache_size = None

    def set_low_power(self, enabled):
        """Free the atmospheric pixmaps in Minimalistisch; reload only if needed."""
        if enabled:
            # Minimal releases the pixmaps. Reset the asset key as well; otherwise
            # returning to the same Glass theme skips reloading the cleared images.
            self._asset_mode = None
            self._wallpaper = QPixmap()
            self._soft_wallpaper = QPixmap()
            self._sharp_cache = QPixmap()
            self._soft_cache = QPixmap()
            self._cache_size = None
        self.update()

    def _ensure_cache(self):
        # The entire window stays opaque. The softened
        # atmosphere is an *internal* backdrop sampled under glass widgets.
        if theme.mode() == 'minimal':
            return
        # Switching Glass/Black Glass must never reuse the other theme's cached image.
        material = theme.mode() if theme.mode() == 'black_glass' else 'glass'
        if material != self._asset_mode:
            prefix = 'black-glass' if material == 'black_glass' else 'glass'
            self._wallpaper = QPixmap(str(ASSETS / (prefix + '-atmosphere.jpg')))
            self._soft_wallpaper = QPixmap(str(ASSETS / (prefix + '-atmosphere-blur.jpg')))
            self._asset_mode = material
            self._cache_size = None
            self._sharp_cache = QPixmap()
            self._soft_cache = QPixmap()
        size = self.size()
        if self._cache_size == size:
            return
        self._cache_size = size
        if size.width() <= 0 or size.height() <= 0:
            return

        def cover(image):
            if image.isNull():
                return QPixmap()
            scaled = image.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = max(0, (scaled.width() - size.width()) // 2)
            y = max(0, (scaled.height() - size.height()) // 2)
            return scaled.copy(x, y, size.width(), size.height())

        self._sharp_cache = cover(self._wallpaper)
        self._soft_cache = cover(self._soft_wallpaper)

    def soft_backdrop(self):
        self._ensure_cache()
        return self._soft_cache

    def sharp_backdrop(self):
        self._ensure_cache()
        return self._sharp_cache

    def paintEvent(self, event):
        p = QPainter(self)
        if theme.mode() == "minimal":
            p.fillRect(self.rect(), QColor(theme.BG))
            p.end()
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(theme.BG))
        if theme.mode() in ('glass', 'black_glass'):
            self._ensure_cache()
            if not self._sharp_cache.isNull():
                p.drawPixmap(0, 0, self._sharp_cache)
            tint = QLinearGradient(0, 0, self.width(), self.height())
            if theme.mode() == 'black_glass':
                tint.setColorAt(0, rgba(0, 0, 0, 125))
                tint.setColorAt(1, rgba(0, 0, 0, 165))
            else:
                tint.setColorAt(0, rgba(4, 9, 19, 48))
                tint.setColorAt(1, rgba(5, 9, 25, 35))
            p.fillRect(self.rect(), QBrush(tint))
        elif theme.mode() == "dark":
            g = QLinearGradient(0, 0, self.width(), self.height())
            g.setColorAt(0, QColor('#0b1321'))
            g.setColorAt(1, QColor('#090d16'))
            p.fillRect(self.rect(), QBrush(g))
        else:
            g = QLinearGradient(0, 0, self.width(), self.height())
            g.setColorAt(0, QColor('#f6f9fe'))
            g.setColorAt(1, QColor('#eaf1f9'))
            p.fillRect(self.rect(), QBrush(g))
        p.end()


def scene_for(widget):
    current = widget.parentWidget()
    while current is not None:
        if isinstance(current, AmbientScene):
            return current
        current = current.parentWidget()
    return None


def draw_frosted_backdrop(p, widget, target, opacity=1.0):
    """Sample a cached blur from the *correct viewport position* on each repaint.

    Scroll offsets are handled by Qt's mapTo() on the widget, not by a local
    counter; this avoids cards showing identical/floating backgrounds.
    """
    scene = scene_for(widget)
    if scene is None:
        return
    image = scene.soft_backdrop()
    if image.isNull():
        return
    pos = widget.mapTo(scene, QPoint(0, 0))
    src = QRectF(pos.x() + target.x(), pos.y() + target.y(),
                 target.width(), target.height())
    p.save()
    p.setOpacity(opacity)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawPixmap(target, image, src)
    p.restore()


def paint_rim(p, rect, radius, *, active=False, compact=False):
    """Accent-aware thin light seams, strongest on selected elements."""
    outer = rounded(rect, radius)
    a = theme.accent_qcolor()
    other = QColor(theme.secondary_accent())
    if theme.mode() not in ('glass', 'black_glass'):
        edge = QColor(theme.BORDER)
        if active:
            edge = a
        p.setPen(QPen(edge, 1.4 if active else 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawPath(outer)
        return
    if theme.mode() == 'black_glass':
        # Neutral silver rather than the cyan/violet outline of regular Glass.
        # Keep the distro/user accent for selected/hover elements only.
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        a.setAlpha(142 if active else 16)
        grad.setColorAt(0, rgba(244, 247, 251, 116))
        grad.setColorAt(.27, rgba(196, 200, 211, 47))
        grad.setColorAt(.55, rgba(118, 122, 132, 66))
        grad.setColorAt(.83, a)
        grad.setColorAt(1, rgba(180, 182, 192, 67))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QBrush(grad), 1.3 if active else 1.0))
        p.drawPath(outer)
        top = QLinearGradient(rect.left(), 0, rect.right(), 0)
        top.setColorAt(0, rgba(255, 255, 255, 0))
        top.setColorAt(.24, rgba(255, 255, 255, 101))
        top.setColorAt(.68, rgba(255, 255, 255, 33))
        top.setColorAt(1, rgba(255, 255, 255, 0))
        p.setPen(QPen(QBrush(top), 1.1, Qt.SolidLine, Qt.RoundCap))
        padx = min(radius+8, rect.width()*.2)
        p.drawLine(QPointF(rect.left()+padx,rect.top()+1.2),
                   QPointF(rect.right()-padx,rect.top()+1.2))
        return
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    bright = QColor('#d8f4ff')
    grad.setColorAt(0, rgba(224, 245, 255, 119))
    a.setAlpha(184 if active else 45)
    other.setAlpha(144 if active else 42)
    grad.setColorAt(.3, a)
    grad.setColorAt(.7, rgba(155, 185, 225, 65))
    grad.setColorAt(1, other)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QBrush(grad), 1.35 if active else 1.1))
    p.drawPath(outer)
    inset = rect.adjusted(2.4, 2.4, -2.4, -2.4)
    if inset.width() > 10 and inset.height() > 10:
        shine = QLinearGradient(inset.topLeft(), inset.bottomRight())
        shine.setColorAt(0, rgba(255, 255, 255, 46))
        shine.setColorAt(1, rgba(255, 255, 255, 0))
        p.setPen(QPen(QBrush(shine), 1.0))
        p.drawPath(rounded(inset, max(2, radius - 2.4)))
    top = QLinearGradient(rect.left(), 0, rect.right(), 0)
    top.setColorAt(0, rgba(255, 255, 255, 0))
    top.setColorAt(.17, rgba(246, 253, 255, 118))
    top.setColorAt(.65, rgba(232, 246, 255, 40))
    top.setColorAt(1, rgba(255, 255, 255, 0))
    p.setPen(QPen(QBrush(top), 1.2, Qt.SolidLine, Qt.RoundCap))
    padx = min(radius + 8, rect.width()*.2)
    p.drawLine(QPointF(rect.left()+padx, rect.top()+1.2), QPointF(rect.right()-padx, rect.top()+1.2))
    if rect.height() > 40 and not compact:
        lower = QLinearGradient(rect.left(), 0, rect.right(), 0)
        a.setAlpha(0); other.setAlpha(74)
        lower.setColorAt(0, a)
        a.setAlpha(28)
        lower.setColorAt(.42, a)
        lower.setColorAt(1, other)
        p.setPen(QPen(QBrush(lower), 1.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(rect.left()+padx, rect.bottom()-1.1), QPointF(rect.right()-padx, rect.bottom()-1.1))


def paint_glass_body(p, widget, rect, radius, *, strong=False, compact=False, active=False):
    """Frosted materials sample a shared blurred backdrop; Dark/Light stay opaque."""
    if theme.mode() == "minimal":
        # No frosted backdrop, rounded paths, gradients or specular passes.
        p.fillRect(rect, QColor(theme.CARD))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(rect)
        return
    glass = rounded(rect, radius)
    p.save()
    p.setClipPath(glass)
    if theme.mode() not in ('glass', 'black_glass'):
        # Solid cards are intentional. Dark and Light must not resemble frosted glass.
        bg = QColor(theme.CARD)
        tint = QColor(theme.accent())
        bg2 = QColor(theme.CARD)
        bg2.setRed(round(bg2.red()*.94+tint.red()*.06))
        bg2.setGreen(round(bg2.green()*.94+tint.green()*.06))
        bg2.setBlue(round(bg2.blue()*.94+tint.blue()*.06))
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0, bg2 if strong or active else bg)
        g.setColorAt(1, bg)
        p.fillPath(glass, QBrush(g))
    else:
        draw_frosted_backdrop(p, widget, rect, 1.0)
        overlay = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if theme.mode() == 'black_glass':
            overlay.setColorAt(0, rgba(31, 33, 36, 155 if strong else 122))
            overlay.setColorAt(.50, rgba(10, 11, 13, 178 if strong else 153))
            overlay.setColorAt(1, rgba(18, 19, 23, 179 if strong else 153))
        else:
            overlay.setColorAt(0, rgba(28, 62, 88, 108 if strong else 80))
            overlay.setColorAt(.54, rgba(13, 27, 49, 130 if strong else 103))
            overlay.setColorAt(1, rgba(27, 31, 61, 123 if strong else 103))
        p.fillPath(glass, QBrush(overlay))
        accent = theme.accent_qcolor()
        accent.setAlpha(43 if strong or active else 17)
        shine = QRadialGradient(rect.left() + rect.width()*.19, rect.top() - rect.height()*.13, max(32, rect.width()*.85))
        shine.setColorAt(0, accent)
        end = QColor(accent); end.setAlpha(0)
        shine.setColorAt(1, end)
        p.fillPath(glass, QBrush(shine))
        reflection = QPainterPath()
        reflection.moveTo(rect.left(), rect.top())
        reflection.lineTo(rect.left()+rect.width()*.53, rect.top())
        reflection.lineTo(rect.left()+rect.width()*.14, rect.top()+rect.height()*.72)
        reflection.lineTo(rect.left(), rect.top()+rect.height()*.78)
        reflection.closeSubpath()
        spec = QLinearGradient(rect.left(), rect.top(), rect.left()+rect.width()*.51, rect.bottom())
        if theme.mode() == 'black_glass':
            spec.setColorAt(0, rgba(255, 255, 255, 35))
            spec.setColorAt(.50, rgba(220, 223, 229, 11))
            spec.setColorAt(1, rgba(195, 198, 205, 0))
        else:
            spec.setColorAt(0, rgba(251, 255, 255, 27))
            spec.setColorAt(.50, rgba(210, 234, 255, 10))
            spec.setColorAt(1, rgba(180, 218, 255, 0))
        p.fillPath(reflection, QBrush(spec))
    p.restore()
    paint_rim(p, rect, radius, active=active, compact=compact)


class GlassSidebar(QFrame):
    """A full-height, truly frosted sidebar behind the logo and ALL categories."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sidebar')
        self.setAutoFillBackground(False)
        self._toggle_button = None

    def set_toggle_button(self, button):
        self._toggle_button = button
        button.setParent(self)
        self._position_toggle()
        button.show()
        button.raise_()

    def _position_toggle(self):
        if self._toggle_button is not None:
            # Stable top-right control, aligned to the vertical glass seam.
            self._toggle_button.move(self.width() - self._toggle_button.width() - 5, 13)
            self._toggle_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_toggle()

    def paintEvent(self, event):
        p = QPainter(self)
        if theme.mode() == "minimal":
            p.fillRect(self.rect(), QColor(theme.SIDEBAR))
            p.setPen(QColor(theme.BORDER))
            p.drawLine(self.width()-1, 0, self.width()-1, self.height())
            p.end()
            return
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        if theme.mode() in ('glass', 'black_glass'):
            draw_frosted_backdrop(p, self, rect, 1.0)
            shade = QLinearGradient(0, 0, self.width(), 0)
            if theme.mode() == 'black_glass':
                shade.setColorAt(0, rgba(2, 2, 3, 215))
                shade.setColorAt(1, rgba(13, 13, 16, 179))
            else:
                shade.setColorAt(0, rgba(7, 15, 30, 175))
                shade.setColorAt(1, rgba(15, 28, 47, 133))
            p.fillRect(rect, QBrush(shade))
        else:
            p.fillRect(rect, QColor(theme.SIDEBAR))
        side = QLinearGradient(0, 0, 0, max(1, self.height()))
        a = theme.accent_qcolor(130 if theme.mode() in ('glass', 'black_glass') else 82)
        side.setColorAt(0, QColor(theme.BORDER))
        side.setColorAt(.5, a)
        side.setColorAt(1, QColor(theme.BORDER))
        p.setPen(QPen(QBrush(side), 1.1))
        p.drawLine(self.width()-1, 0, self.width()-1, self.height())
        p.end()


class GlassSurface(QFrame):
    """Glass card: soft refraction, reduced dark overlay and lit interior bevel."""
    def __init__(self, parent=None, *, hero=False, compact=False):
        super().__init__(parent)
        self._hero = hero
        self._compact = compact
        self._hover = False
        self.setObjectName('heroCard' if hero else 'chip' if compact else 'card')
        self.setAutoFillBackground(False)

    def enterEvent(self, event):
        self._hover = True
        if theme.mode() != "minimal":
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        if theme.mode() != "minimal":
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        if theme.mode() != "minimal":
            p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2.5, 2.5, -2.5, -2.5)
        if r.width() >= 8 and r.height() >= 8:
            radius = 12 if self._compact else 21 if self._hero else 17
            paint_glass_body(p, self, r, radius,
                             strong=self._hero, compact=self._compact,
                             active=self._hover)
        p.end()
