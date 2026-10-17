"""Native glass materials for the Vitalux Qt6 interface.

Glass and Black Glass sample a cached, softly blurred in-app backdrop,
matching each card's actual position. The whole window stays opaque.
No KWin compositor transparency or blur-behind is required.
"""
from __future__ import annotations

from pathlib import Path
from math import sin, cos
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QFrame, QWidget
from . import theme, settings, motion, backdrops

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
        self._render_key = None
        self._composed_key = None
        self._composed_sharp = QPixmap()
        self._composed_soft = QPixmap()
        self._phase = 0.0
        self._motion_timer = QTimer(self)
        self._motion_timer.setInterval(220)
        self._motion_timer.timeout.connect(self._advance_backdrop)
        self.sync_background()

    def sync_background(self):
        self._render_key = None
        self._asset_mode = None
        self._cache_size = None
        self._composed_key = None
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        active = (settings.get('background_animate', False)
                  and style != 'minimal' and theme.mode() != 'minimal'
                  and motion.enabled())
        if active:
            self._motion_timer.start()
        else:
            self._motion_timer.stop()
        self.update()

    def _advance_backdrop(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + .065) % 6.28318530718
        self._composed_key = None
        self._render_key = None
        self.update()
        # Keep live glass sampling aligned to the painted moving backdrop.
        for kind in (GlassSurface, GlassSidebar):
            for card in self.findChildren(kind):
                if card.isVisible():
                    card.update()

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
            self._render_key = None
            self._composed_key = None
        self.sync_background()

    def _ensure_cache(self):
        # The entire window stays opaque. The softened
        # atmosphere is an *internal* backdrop sampled under glass widgets.
        if theme.mode() == 'minimal':
            return
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        if style not in ('glass', 'black_glass'):
            # Each preset is cached independently and sampled by glass panels.
            key = (theme.mode(), style, theme.accent(),
                   backdrops.bounded(settings.get('background_intensity', 60), 60),
                   backdrops.bounded(settings.get('background_softness', 65), 65),
                   self.size(), round(self._phase, 3))
            if key != self._render_key:
                self._sharp_cache, self._soft_cache = backdrops.render(
                    self.size(), style, theme.accent(), key[3], key[4],
                    light=(theme.mode() == 'light'), phase=self._phase)
                self._render_key = key
                self._asset_mode = None
                self._cache_size = self.size()
            return

        # These are the exact original bundled Glass/Black Glass wallpapers.
        # Reset cache identity when switching from generated backgrounds.
        if self._render_key is not None:
            self._asset_mode = None
        self._render_key = None
        material = style
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

    def _ensure_composed(self):
        """One final background for the canvas, sidebar and frosted cards.

        In older builds, root tinted the *painted* image while sidebar/cards
        sampled the un-tinted original. Light wallpapers with Glass therefore
        gave three incompatible colors. Compose once and share that result.
        """
        if theme.mode() == 'minimal':
            self._composed_sharp = QPixmap()
            self._composed_soft = QPixmap()
            self._composed_key = None
            return
        self._ensure_cache()
        if self._sharp_cache.isNull():
            return
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        intensity = backdrops.bounded(settings.get('background_intensity', 60), 60)
        softness = backdrops.bounded(settings.get('background_softness', 65), 65)
        moving = self._motion_timer.isActive()
        key = (theme.mode(), style, theme.accent(), self.size(),
               intensity, softness, round(self._phase, 4) if moving else 0,
               self._asset_mode, self._render_key)
        if key == self._composed_key and not self._composed_sharp.isNull():
            return
        canvas = self._sharp_cache.copy()
        painter = QPainter(canvas)
        painter.setPen(Qt.NoPen)
        full = QRectF(canvas.rect())
        # Apply readability correction once, *before* sidebar or cards sample.
        if theme.mode() == 'light' and style not in ('light', 'arctic'):
            painter.fillRect(full, rgba(247, 250, 255, 200))
        elif theme.mode() != 'light' and style == 'light':
            painter.fillRect(full, rgba(5, 12, 26, 194))
        elif theme.mode() in ('glass', 'black_glass'):
            if style == theme.mode():
                tint = QLinearGradient(0, 0, canvas.width(), canvas.height())
                if style == 'black_glass':
                    tint.setColorAt(0, rgba(0, 0, 0, 125))
                    tint.setColorAt(1, rgba(0, 0, 0, 165))
                else:
                    tint.setColorAt(0, rgba(4, 9, 19, 48))
                    tint.setColorAt(1, rgba(5, 9, 25, 35))
                painter.fillRect(full, QBrush(tint))
            else:
                painter.fillRect(full, rgba(3, 9, 20, 18 if theme.mode() == 'glass' else 36))

        # Stock Glass/Black Glass use fixed artwork. Desaturate/tint their
        # source gently at low intensity; 100% reveals the original colors.
        # This correction belongs to the shared canvas so the sidebar and
        # frosted cards react identically when the user moves the slider.
        if style in ('glass', 'black_glass'):
            neutral = rgba(14, 22, 34, round((100 - intensity) * 1.55)) if style == 'glass' \
                else rgba(21, 22, 28, round((100 - intensity) * 1.55))
            painter.fillRect(full, neutral)

        # Slow, nuanced ambient breathing that suits each wallpaper's colors.
        # It works even with the original bundled Glass wallpapers.
        if moving:
            glow_colors = backdrops.motion_colors(style, theme.accent(), theme.mode() == 'light')
            strength = (max(.25, intensity / 100) * .24)
            width, height = canvas.width(), canvas.height()
            for i, color in enumerate(glow_colors):
                x = width * ((.23 if i == 0 else .78) +
                             .16 * sin(self._phase + i * 2.1))
                y = height * ((.30 if i == 0 else .68) +
                              .18 * cos(self._phase * .8 + i * 2.3))
                radius = max(width * .34, height * .72) * (1 + softness / 300)
                gradient = QRadialGradient(QPointF(x, y), radius)
                center = QColor(color)
                center.setAlphaF(min(.42, strength * (.95 if i == 0 else .60)))
                end = QColor(center); end.setAlpha(0)
                gradient.setColorAt(0, center)
                gradient.setColorAt(.55, QColor(center).lighter(104))
                gradient.setColorAt(1, end)
                painter.fillRect(full, QBrush(gradient))
        painter.end()

        self._composed_sharp = canvas
        # The sidebar shows the precise same canvas. Cards use a blur derived
        # from that *same final image*, not from an incompatible raw palette.
        divisor = 4 + round(softness * .10)
        tiny = canvas.scaled(max(14, canvas.width() // divisor),
                             max(14, canvas.height() // divisor),
                             Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self._composed_soft = tiny.scaled(canvas.size(),
                                         Qt.IgnoreAspectRatio,
                                         Qt.SmoothTransformation)
        self._composed_key = key

    def soft_backdrop(self):
        self._ensure_composed()
        return self._composed_soft

    def sharp_backdrop(self):
        self._ensure_composed()
        return self._composed_sharp

    def paintEvent(self, event):
        p = QPainter(self)
        if theme.mode() == "minimal":
            p.fillRect(self.rect(),
                       backdrops.minimal_color(settings.get('background_intensity', 60)))
        else:
            self._ensure_composed()
            p.fillRect(self.rect(), QColor(theme.BG))
            if not self._composed_sharp.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                p.drawPixmap(0, 0, self._composed_sharp)
        p.end()


def scene_for(widget):
    current = widget.parentWidget()
    while current is not None:
        if isinstance(current, AmbientScene):
            return current
        current = current.parentWidget()
    return None


def draw_frosted_backdrop(p, widget, target, opacity=1.0, *, softened=True):
    """Sample a cached blur from the *correct viewport position* on each repaint.

    Scroll offsets are handled by Qt's mapTo() on the widget, not by a local
    counter; this avoids cards showing identical/floating backgrounds.
    """
    scene = scene_for(widget)
    if scene is None:
        return
    image = scene.soft_backdrop() if softened else scene.sharp_backdrop()
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
        if theme.mode() == 'minimal':
            # Match the same monochrome intensity as the central scene.
            p.fillRect(self.rect(),
                       backdrops.minimal_color(settings.get('background_intensity', 60)))
        else:
            # Use the exact same composed canvas at the actual sidebar origin.
            # Never add a second opaque tint (the source of the dark strip).
            draw_frosted_backdrop(p, self, QRectF(self.rect()),
                                  softened=False)
        # Only the seam separates navigation from content.
        side = QLinearGradient(0, 0, 0, max(1, self.height()))
        accent = theme.accent_qcolor(82)
        side.setColorAt(0, QColor(theme.BORDER))
        side.setColorAt(.5, accent)
        side.setColorAt(1, QColor(theme.BORDER))
        p.setPen(QPen(QBrush(side), 1.0))
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
