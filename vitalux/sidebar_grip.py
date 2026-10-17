"""Mouse-draggable and keyboard-usable sidebar side switch.

A dedicated grip avoids stealing clicks from the navigation buttons. Drag it
across the window centre and release to dock left/right; a short click toggles.
"""
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton
from . import theme


class SidebarGrip(QPushButton):
    dockRequested = Signal(bool)  # True = right
    def __init__(self, parent=None):
        super().__init__('', parent)
        self.setFixedSize(26, 30)
        self.setObjectName('sidebarGrip')
        self.setAccessibleName('Seitenleiste nach links oder rechts verschieben')
        self.setCursor(Qt.OpenHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self._press = None
        self._dragging = False
        self._right = False

    def set_right(self, value):
        self._right = bool(value)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._dragging = False
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is not None:
            if (event.globalPosition().toPoint() - self._press).manhattanLength() > 7:
                self._dragging = True
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press is not None:
            right = not self._right
            if self._dragging:
                window = self.window()
                x = window.mapFromGlobal(event.globalPosition().toPoint()).x()
                right = x > window.width() / 2
            self._press = None
            self._dragging = False
            self.setCursor(Qt.OpenHandCursor)
            self.clearFocus()
            self.dockRequested.emit(right)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QColor(theme.MUTED)
        if self.underMouse() or self._dragging or self.hasFocus():
            pen = QColor(theme.accent())
        p.setPen(QPen(pen, 2.0, Qt.SolidLine, Qt.RoundCap))
        cx, cy = self.width() / 2, self.height() / 2
        for x in (-4, 0, 4):
            for y in (-4, 0, 4):
                p.drawPoint(QPointF(cx + x, cy + y))
        p.end()
