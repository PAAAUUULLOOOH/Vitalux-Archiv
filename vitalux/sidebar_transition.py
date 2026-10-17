"""Single-layer, frame-cached sidebar compositor.

Real Qt layouts settle at the two endpoints. During movement only the cached
images are painted. Card frames are clipped rather than scaling widget
screenshots: fonts, graphs and glass borders cannot be squeezed into thin
strips during the transition.
"""
from PySide6.QtCore import Qt, QRect, QEvent, Signal
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtWidgets import QWidget
from . import theme


def _slice(pixmap: QPixmap, x: int, width: int) -> QPixmap:
    """Copy in physical pixels, preserving HiDPI logical dimensions."""
    dpr = pixmap.devicePixelRatio()
    xpx = round(x * dpr)
    wpx = round((x + width) * dpr) - xpx
    piece = pixmap.copy(xpx, 0, wpx, pixmap.height())
    piece.setDevicePixelRatio(dpr)
    return piece


def _transition_cache(pixmap: QPixmap) -> QPixmap:
    """Keep cached animation sprites at *logical* resolution on HiDPI.

    The real Qt widgets are shown unchanged immediately after the movement.
    On a 150%-scaled screen this reduces per-frame pixel copying by >50%,
    and avoids multisample scaling work in every paintEvent.
    """
    if pixmap is None or pixmap.isNull() or pixmap.devicePixelRatio() <= 1.0:
        return pixmap
    dpr = pixmap.devicePixelRatio()
    width = max(1, round(pixmap.width() / dpr))
    height = max(1, round(pixmap.height() / dpr))
    result = pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    result.setDevicePixelRatio(1.0)
    return result


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _lerp(start, end, fraction):
    return start + (end - start) * fraction


class SidebarFreeze(QWidget):
    """Opaque first-frame guard while Qt changes the real layout underneath.

    When Qt processes deferred resize/paint events to settle the *destination*
    state, the user must keep seeing the original state.  Previously the
    transition overlay was created only after processEvents(), making the
    intermediate expanded/compact layout visible for one or more frames.
    """

    def __init__(self, parent, frame):
        super().__init__(parent)
        self._frame = frame
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setGeometry(parent.rect())
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._frame)
        painter.end()


class SidebarTransition(QWidget):
    """Caches endpoints; only inexpensive QPainter composition occurs per tick."""
    resized = Signal()

    def __init__(self, parent, before, after, old_width, new_width,
                 old_arrow=None, new_arrow=None, old_tiles=None, new_tiles=None,
                 old_viewport=None, new_viewport=None,
                 before_side=None, after_side=None):
        super().__init__(parent)
        self.old_width = int(old_width)
        self.new_width = int(new_width)
        self.progress = 0.0
        self._before_sidebar = _transition_cache(_slice(before, 0, self.old_width))
        self._after_sidebar = _transition_cache(_slice(after, 0, self.new_width))
        width = parent.width()
        self._before_content = _transition_cache(_slice(before, self.old_width, width - self.old_width))
        self._after_content = _transition_cache(_slice(after, self.new_width, width - self.new_width))
        # Cache each image once in native logical coordinates. Nav sprites and
        # moving tiles are drawn without real-time scaling or blur filters.
        def normalise_sidebar(layers):
            if not layers:
                return layers
            return dict(layers,
                        background=_transition_cache(layers['background']),
                        nav={key: (rect, _transition_cache(sprite)) if sprite else None
                             for key, data in layers['nav'].items()
                             for rect, sprite in ([data] if data else [(None, None)])},
                        **{key: (value[0], _transition_cache(value[1])) if value else None
                           for key in ('brand', 'language', 'version')
                           for value in (layers[key],)})

        self._sidebar_start = normalise_sidebar(before_side)
        self._sidebar_end = normalise_sidebar(after_side)
        self._before_arrow = _transition_cache(old_arrow)
        self._after_arrow = _transition_cache(new_arrow)
        self._old_tiles = {key: (rect, _transition_cache(sprite))
                           for key, (rect, sprite) in (old_tiles or {}).items()}
        self._new_tiles = {key: (rect, _transition_cache(sprite))
                           for key, (rect, sprite) in (new_tiles or {}).items()}
        self._old_viewport = old_viewport
        self._new_viewport = new_viewport
        self._background = QColor(theme.BG)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setGeometry(parent.rect())
        parent.installEventFilter(self)
        self.show()
        self.raise_()

    def current_width(self):
        return round(_lerp(self.old_width, self.new_width, self.progress))

    def set_progress(self, progress):
        self.progress = max(0.0, min(1.0, float(progress)))
        self.update()

    def eventFilter(self, watched, event):
        if watched is self.parentWidget() and event.type() == QEvent.Resize:
            self.resized.emit()
        return super().eventFilter(watched, event)

    def _paint_content(self, painter, seam, fraction):
        """Compose cached content at native pixel size; never squash the UI."""
        available = max(0, self.width() - seam)
        if not available:
            return
        # Both background pixmaps contain NO live dashboard tiles; those are
        # animated separately. Never switch instantly to the destination
        # background on the first frame (which looked like a flash on click).
        # Native pixmap painting avoids any stretch/deformation of text.
        painter.drawPixmap(seam, 0, self._before_content)
        if fraction > 0:
            painter.save()
            painter.setOpacity(fraction)
            painter.drawPixmap(seam, 0, self._after_content)
            painter.restore()

    @staticmethod
    def _paint_unscaled_tile(painter, frame, sprite, opacity):
        """Reveal a native-size card image inside its moving frame.

        Never draw QPixmap into a stretched target QRect: the old renderer
        visibly compressed card contents and text when the window reflowed.
        """
        if opacity <= 0 or sprite.isNull():
            return
        painter.save()
        painter.setOpacity(opacity)
        painter.setClipRect(frame, Qt.IntersectClip)
        painter.drawPixmap(frame.topLeft(), sprite)
        painter.restore()

    def _paint_tiles(self, painter, seam, fraction):
        if not self._old_tiles and not self._new_tiles:
            return
        initial_clip, final_clip = self._old_viewport, self._new_viewport
        painter.save()
        if initial_clip and final_clip:
            clip = QRect(round(_lerp(initial_clip.x(), final_clip.x(), fraction)),
                         round(_lerp(initial_clip.y(), final_clip.y(), fraction)),
                         round(_lerp(initial_clip.width(), final_clip.width(), fraction)),
                         round(_lerp(initial_clip.height(), final_clip.height(), fraction)))
            painter.setClipRect(clip, Qt.IntersectClip)
        for key in (self._old_tiles.keys() | self._new_tiles.keys()):
            old = self._old_tiles.get(key)
            new = self._new_tiles.get(key)
            if old is None and new is None:
                continue
            first, last = old or new, new or old
            a, b = first[0], last[0]
            start_x = a.x() - (self.old_width if old else self.new_width)
            end_x = b.x() - (self.new_width if new else self.old_width)
            frame = QRect(round(seam + _lerp(start_x, end_x, fraction)),
                          round(_lerp(a.y(), b.y(), fraction)),
                          max(1, round(_lerp(a.width(), b.width(), fraction))),
                          max(1, round(_lerp(a.height(), b.height(), fraction))))
            # Paint the destination material first: expanding tiles never
            # have an empty right edge. The original material covers it at
            # the start, then fades over a short middle interval.
            if old is not None and new is not None:
                # Most frames require ONE pixmap, not two alpha-blended
                # high-resolution surfaces. Blend only around midpoint.
                if fraction < .42:
                    self._paint_unscaled_tile(painter, frame, old[1], 1.0)
                elif fraction >= .58:
                    self._paint_unscaled_tile(painter, frame, new[1], 1.0)
                else:
                    mix = (fraction - .42) / .16
                    self._paint_unscaled_tile(painter, frame, old[1], 1.0)
                    self._paint_unscaled_tile(painter, frame, new[1], mix)
            elif new is not None:
                self._paint_unscaled_tile(painter, frame, new[1], fraction)
            else:
                self._paint_unscaled_tile(painter, frame, old[1], 1.0-fraction)
        painter.restore()

    def _paint_sidebar_layers(self, painter, seam, fraction):
        """Animate navigation sprites instead of ghosting two whole sidebars.

        A single expanded-button sprite is clipped to an interpolated width.
        Its text naturally reveals or disappears, while the icon moves with
        its row. Neither captions nor glyphs are painted twice in one frame.
        """
        start, end = self._sidebar_start, self._sidebar_end
        if not start or not end:
            # Safe fallback for a capture made before the window becomes visible.
            compact = self._before_sidebar if self.old_width < self.new_width else self._after_sidebar
            expanded = self._after_sidebar if self.old_width < self.new_width else self._before_sidebar
            painter.drawPixmap(0, 0, compact if seam <= 82 else expanded)
            return
        # Both are the same sidebar material. Draw one wide cached backdrop
        # rather than alpha-blend two full-height pixmaps on *every* frame.
        expanding = self.new_width > self.old_width
        background = end['background'] if expanding else start['background']
        painter.drawPixmap(0, 0, background)

        expanded_fraction = fraction if expanding else 1.0 - fraction
        # The brand has no compact equivalent. Fade its ONE cached sprite in
        # once the rail has enough width; it never competes with duplicate text.
        branding = end if expanding else start
        opacity = _ease(max(0.0, min(1.0, (expanded_fraction - 0.16) / 0.44)))
        if opacity > 0:
            painter.save()
            painter.setOpacity(opacity)
            for key in ('brand','language','version'):
                part = branding[key]
                if part is not None:
                    rect, sprite = part
                    painter.drawPixmap(rect.topLeft(), sprite)
            painter.restore()

        a, b = start['viewport'], end['viewport']
        clip = QRect(round(_lerp(a.x(), b.x(), fraction)),
                     round(_lerp(a.y(), b.y(), fraction)),
                     max(1, round(_lerp(a.width(), b.width(), fraction))),
                     max(1, round(_lerp(a.height(), b.height(), fraction))))
        painter.save()
        painter.setClipRect(clip, Qt.IntersectClip)
        # Every nav row slides vertically as the brand grows/shrinks. Use the
        # *expanded* source image in both directions and reveal the label with
        # the interpolating button width; no full-frame cross-fade of letters.
        for i in start['nav'].keys() | end['nav'].keys():
            old, new = start['nav'].get(i), end['nav'].get(i)
            if old is None or new is None:
                continue
            wide = new if expanding else old
            old_rect, new_rect = old[0], new[0]
            x = round(_lerp(old_rect.x(), new_rect.x(), fraction))
            y = round(_lerp(old_rect.y(), new_rect.y(), fraction))
            width = max(1, round(_lerp(old_rect.width(), new_rect.width(), fraction)))
            height = max(1, round(_lerp(old_rect.height(), new_rect.height(), fraction)))
            painter.save()
            painter.setClipRect(QRect(x,y,width,height), Qt.IntersectClip)
            painter.drawPixmap(x, y, wide[1])
            painter.restore()
        painter.restore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        seam = max(0, min(self.width(), self.current_width()))
        w, h = self.width(), self.height()
        t = self.progress
        p.fillRect(self.rect(), self._background)
        p.save()
        p.setClipRect(QRect(seam, 0, w - seam, h))
        self._paint_content(p, seam, t)
        self._paint_tiles(p, seam, t)
        p.restore()

        p.save()
        p.setClipRect(QRect(0, 0, seam, h))
        self._paint_sidebar_layers(p, seam, t)
        p.restore()

        arrow_x = seam - 31
        arrow_y = 13
        if self._before_arrow is not None and not self._before_arrow.isNull():
            p.setOpacity(1.0 - _ease(t))
            p.drawPixmap(arrow_x, arrow_y, self._before_arrow)
        if self._after_arrow is not None and not self._after_arrow.isNull():
            p.setOpacity(_ease(t))
            p.drawPixmap(arrow_x, arrow_y, self._after_arrow)
        p.end()

    def closeEvent(self, event):
        self.parentWidget().removeEventFilter(self)
        super().closeEvent(event)
