"""Native glass materials for the Vitalux Qt6 interface.

Glass and Black Glass sample a cached, softly blurred in-app backdrop,
matching each card's actual position. The whole window stays opaque.
No KWin compositor transparency or blur-behind is required.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QFrame, QWidget
try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
except (ImportError, RuntimeError):
    QOpenGLWidget = None

from . import theme, settings, backdrops, user_background, renderer

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def rgba(r, g, b, a):
    return QColor(r, g, b, a)


def rounded(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


class _AmbientSceneCore:
    """Shared cached-background implementation for raster and OpenGL hosts."""
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
        self._wallpaper_timer = QTimer(self)
        self._wallpaper_timer.setInterval(250)
        self._wallpaper_timer.timeout.connect(self._advance_backdrop)
        self.sync_background()

    def sync_background(self):
        self._render_key = None
        self._asset_mode = None
        self._cache_size = None
        self._composed_key = None
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        active = style in backdrops.ANIMATED_PRESETS
        if active and not self._wallpaper_timer.isActive():
            self._wallpaper_timer.start()
        elif not active:
            self._wallpaper_timer.stop()
            self._phase = 0.0
        self.update()

    def _advance_backdrop(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + .13) % 6.28318530718
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
        if enabled and backdrops.resolve(settings.get('background_style', 'theme_default'),
                                         theme.mode()) == 'minimal':
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
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        if style == 'minimal' and theme.mode() == 'minimal':
            return
        if style == 'custom_image':
            chosen = settings.get('custom_background_selected', '')
            fit = settings.get('custom_background_fit', 'cover')
            path = user_background.image_path(chosen)
            stamp = path.stat().st_mtime_ns if path else None
            key = (style, chosen, fit, stamp, theme.BG, self.size())
            if key != self._render_key:
                self._sharp_cache = user_background.draw(self.size(), chosen, fit)
                self._soft_cache = self._sharp_cache
                self._render_key = key
                self._asset_mode = None
                self._cache_size = self.size()
            return
        if style not in ('glass', 'black_glass'):
            # Each preset is cached independently and sampled by glass panels.
            key = (theme.mode(), style, theme.accent(), self.size(),
                   round(self._phase, 3) if style in backdrops.ANIMATED_PRESETS else 0)
            if key != self._render_key:
                self._sharp_cache, self._soft_cache = backdrops.render(
                    self.size(), style, theme.accent(),
                    light=style in backdrops.LIGHT_PRESETS
                       or theme.mode() == 'light', phase=self._phase)
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
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        if style == 'minimal' and theme.mode() == 'minimal':
            self._composed_sharp = QPixmap()
            self._composed_soft = QPixmap()
            self._composed_key = None
            return
        self._ensure_cache()
        if self._sharp_cache.isNull():
            return
        moving = self._wallpaper_timer.isActive()
        key = (theme.mode(), style, theme.accent(), self.size(),
               round(self._phase, 4) if moving else 0,
               self._asset_mode, self._render_key)
        if key == self._composed_key and not self._composed_sharp.isNull():
            return
        canvas = self._sharp_cache.copy()
        painter = QPainter(canvas)
        painter.setPen(Qt.NoPen)
        full = QRectF(canvas.rect())
        # Never darken a light wallpaper or bleach a dark one solely because
        # the selected card/text theme differs. Each wallpaper keeps its
        # intended palette; the card and sidebar materials provide legibility.
        # Only the original Glass / Black Glass atmosphere retains its
        # purpose-designed shading.
        if style == theme.mode() and style in ('glass', 'black_glass'):
            wash = QLinearGradient(0, 0, canvas.width(), canvas.height())
            if style == 'black_glass':
                wash.setColorAt(0, rgba(0, 0, 0, 109))
                wash.setColorAt(1, rgba(0, 0, 0, 131))
            else:
                wash.setColorAt(0, rgba(4, 9, 19, 30))
                wash.setColorAt(1, rgba(5, 9, 25, 23))
            painter.fillRect(full, QBrush(wash))
        painter.end()

        self._composed_sharp = canvas
        # The sidebar shows the precise same canvas. Cards use a blur derived
        # from that *same final image*, not from an incompatible raw palette.
        divisor = 10
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

    def _paint_background(self):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.BG))
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        if style == 'minimal' and theme.mode() == 'minimal':
            p.fillRect(self.rect(), backdrops.minimal_color())
        else:
            self._ensure_composed()
            if not self._composed_sharp.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                p.drawPixmap(0, 0, self._composed_sharp)
        p.end()


class AmbientScene(_AmbientSceneCore, QWidget):
    """Established Qt raster renderer. Always available and the default."""
    def paintEvent(self, event):
        self._paint_background()


if QOpenGLWidget is not None:
    class AcceleratedAmbientScene(_AmbientSceneCore, QOpenGLWidget):
        """Experimental GL-backed background with OpenGL compositing.

        Standard Qt child widgets continue using software QPainter.
        """
        def paintEvent(self, event):
            QOpenGLWidget.paintEvent(self, event)

        def paintGL(self):
            self._paint_background()
else:
    AcceleratedAmbientScene = None


def create_ambient_scene():
    """Select one backend at startup; never hot-swap a GL surface."""
    if renderer.desired() == renderer.QTQUICK:
        if renderer.quick_available():
            try:
                from .quick_scene import QuickAmbientScene
                scene = QuickAmbientScene()
                scene.render_backend = renderer.QTQUICK
                return scene
            except (ImportError, RuntimeError, OSError) as exc:
                print('Vitalux: Qt Quick konnte nicht initialisiert werden:', exc)
        renderer.fallback()
    if renderer.desired() == renderer.OPENGL:
        if AcceleratedAmbientScene is not None and renderer.gpu_available():
            try:
                scene = AcceleratedAmbientScene()
                scene.render_backend = renderer.OPENGL
                return scene
            except (RuntimeError, OSError):
                pass
        renderer.fallback()
    scene = AmbientScene()
    scene.render_backend = renderer.SOFTWARE
    return scene


def scene_for(widget):
    current = widget.parentWidget()
    while current is not None:
        if isinstance(current, _AmbientSceneCore):
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
    # The source crop and destination are equal-sized in scene coordinates.
    # Avoid the expensive smooth resampling path during every scroll repaint.
    if abs(src.width()-target.width()) > .01 or abs(src.height()-target.height()) > .01:
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
        bg_style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                     theme.mode())
        bg = backdrops.material_tint(bg_style, theme.CARD, theme.accent(), .085)
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
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        if style not in backdrops.DEFAULT_THEMES:
            # New wallpapers reflect subtly in the cards, but the accent hue
            # does not overwrite the text contrast of Glass/Black Glass.
            material = backdrops.material_tint(style, theme.CARD, theme.accent(), .24)
            top = QColor(material)
            top.setAlpha(174 if strong else
                         149 if style in backdrops.LIGHT_PRESETS else 128)
            bottom = QColor(material).darker(125)
            bottom.setAlpha(166 if strong else 136)
            overlay.setColorAt(0, top)
            overlay.setColorAt(1, bottom)
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
            self._toggle_button.move(
                self.width() - self._toggle_button.width() - 5, 13)
            self._toggle_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_toggle()

    def paintEvent(self, event):
        """Restore the original Vitalux frosted sidebar and luminous seam.

        Matching Glass/Black Glass/Light/Dark schemes keep their original
        treatment. For new wallpapers, the frost adapts gently to the chosen
        palette so it remains related to the cards and the scene.
        """
        p = QPainter(self)
        style = backdrops.resolve(settings.get('background_style', 'theme_default'),
                                  theme.mode())
        matching = style == theme.mode()
        if theme.mode() == 'minimal' and style == 'minimal':
            # Original opaque sidebar with a stable monochrome material.
            base = backdrops.minimal_color()
            p.fillRect(self.rect(), QColor(theme.blend(theme.SIDEBAR, base.name(), .68)))
        else:
            p.setRenderHint(QPainter.Antialiasing)
            rect = QRectF(self.rect())
            if theme.mode() in ('glass', 'black_glass'):
                draw_frosted_backdrop(p, self, rect, 1.0)
                shade = QLinearGradient(0, 0, self.width(), 0)
                if theme.mode() == 'black_glass':
                    # Original two-sided black-glass frost.
                    left, right = (190, 160) if matching else (143, 119)
                    shade.setColorAt(0, rgba(2, 2, 3, left))
                    shade.setColorAt(1, rgba(13, 13, 16, right))
                else:
                    # Original blue-grey transparent glass material.
                    left, right = (159, 130) if matching else (
                        (51, 43) if style in backdrops.LIGHT_PRESETS
                        else (112, 96))
                    shade.setColorAt(0, rgba(7, 15, 30, left))
                    shade.setColorAt(1, rgba(15, 28, 47, right))
                p.fillRect(rect, QBrush(shade))
            else:
                material = QColor(theme.blend(theme.SIDEBAR, theme.CARD, .63))
                if style in backdrops.LIGHT_PRESETS and theme.mode() != 'light':
                    material.setAlpha(80)
                elif not matching:
                    material.setAlpha(210 if theme.mode() == 'light' else 188)
                p.fillRect(rect, material)
        side = QLinearGradient(0, 0, 0, max(1, self.height()))
        accent = theme.accent_qcolor(130 if theme.mode() in ('glass', 'black_glass') else 82)
        side.setColorAt(0, QColor(theme.BORDER))
        side.setColorAt(.5, accent)
        side.setColorAt(1, QColor(theme.BORDER))
        p.setPen(QPen(QBrush(side), 1.1))
        x = self.width()-1
        p.drawLine(x, 0, x, self.height())
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
