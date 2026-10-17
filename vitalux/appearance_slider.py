"""A carefully rendered native Qt slider for Vitalux's appearance controls.

The platform style no longer determines the handle or groove appearance.
Keyboard and wheel accessibility remain those of QSlider.
"""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QSlider

from . import theme


class AppearanceSlider(QSlider):
    """High-contrast satin track with a glowing, tactile accent thumb."""

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setObjectName('backgroundSlider')
        self.setMinimumHeight(42)
        self.setFixedHeight(42)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self._hover = False
        self._dragging = False

    def _geometry(self):
        outer = 13.0
        width = max(1.0, self.width() - outer * 2)
        span = max(1, self.maximum() - self.minimum())
        fraction = max(0., min(1., (self.sliderPosition() - self.minimum()) / span))
        return outer, width, outer + width * fraction, self.height() * .5

    def _set_from_point(self, x):
        left, width, _center, _middle = self._geometry()
        fraction = max(0., min(1., (x - left) / width))
        self.setSliderPosition(round(self.minimum() + fraction * (self.maximum() - self.minimum())))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus()
            self._dragging = True
            self.setSliderDown(True)
            self._set_from_point(event.position().x())
            self.update()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._set_from_point(event.position().x())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == Qt.LeftButton:
            self._set_from_point(event.position().x())
            self._dragging = False
            self.setSliderDown(False)
            self.update()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        left, width, center, cy = self._geometry()
        base = QColor(theme.CARD)
        accent = QColor(theme.accent())
        secondary = QColor(theme.secondary_accent())
        ink = QColor(theme.TEXT)
        track = QRectF(left, cy - 3.5, width, 7.0)

        # Quiet full-length inset rail, distinctly visible in both Light/Dark.
        shadow = QColor('#09101b' if theme.mode() != 'light' else '#7690ab')
        shadow.setAlpha(70 if theme.mode() != 'light' else 55)
        painter.setPen(Qt.NoPen)
        painter.setBrush(shadow)
        painter.drawRoundedRect(track.adjusted(-1, -1, 1, 1), 4.5, 4.5)
        empty = QColor(theme.INPUT_BG if hasattr(theme, 'INPUT_BG') else theme.CARD)
        painter.setBrush(empty)
        painter.drawRoundedRect(track, 3.5, 3.5)

        # The filled section is a real gradient, not a native Plasma groove.
        if center > left + 2:
            fill = QRectF(left, cy - 3.5, center - left, 7.0)
            gradient = QLinearGradient(left, cy, left + width, cy)
            gradient.setColorAt(0, secondary)
            gradient.setColorAt(.65, accent)
            gradient.setColorAt(1, QColor(accent).lighter(120))
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(fill, 3.5, 3.5)

        # Fine end markers make the scale's extent visually clear.
        marker = QColor(ink)
        marker.setAlpha(77 if theme.mode() != 'light' else 92)
        painter.setPen(QPen(marker, 1.0))
        painter.drawLine(QPointF(left, cy+9), QPointF(left, cy+12))
        painter.drawLine(QPointF(left+width, cy+9), QPointF(left+width, cy+12))

        if self.isEnabled():
            # Small radial halo, luminous white cap and an inner accent core.
            focused = self.hasFocus() or self._hover or self._dragging
            aura = QRadialGradient(QPointF(center, cy), 19 if focused else 16)
            glow = QColor(accent)
            glow.setAlpha(95 if focused else 52)
            end = QColor(accent); end.setAlpha(0)
            aura.setColorAt(0, glow)
            aura.setColorAt(1, end)
            painter.setBrush(QBrush(aura))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(center, cy), 19 if focused else 16, 19 if focused else 16)

            ring = QColor(theme.BORDER)
            ring.setAlpha(235)
            painter.setPen(QPen(ring, 1.2))
            painter.setBrush(QColor(theme.CARD))
            painter.drawEllipse(QPointF(center, cy), 10.5, 10.5)
            cap = QLinearGradient(center, cy - 9, center, cy + 9)
            cap.setColorAt(0, QColor(accent).lighter(137))
            cap.setColorAt(1, accent)
            painter.setBrush(QBrush(cap))
            painter.setPen(QPen(QColor(theme.BORDER), 1))
            painter.drawEllipse(QPointF(center, cy), 8.4, 8.4)
            highlight = QColor('#ffffff')
            highlight.setAlpha(130)
            painter.setPen(Qt.NoPen)
            painter.setBrush(highlight)
            painter.drawEllipse(QPointF(center - 2.2, cy - 2.7), 2.6, 2.6)
        painter.end()
