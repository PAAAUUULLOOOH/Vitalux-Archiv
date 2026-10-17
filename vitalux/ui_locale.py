"""Qt widgets that respect Vitalux's runtime DE/EN localization.

The project uses dynamically constructed Python widgets rather than .ui files.
Central wrappers ensure buttons, combo entries, dialogs and dynamically updated
labels all pass through the same translation function.
"""
from PySide6.QtWidgets import (QLabel as _QLabel, QPushButton as _QPushButton,
    QCheckBox as _QCheckBox, QComboBox as _QComboBox, QDialog as _QDialog,
    QListWidgetItem as _QListWidgetItem, QMessageBox as _QMessageBox,
    QFileDialog as _QFileDialog)
from .i18n import tr
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def localized(x):
    return tr(x) if isinstance(x, str) else x

class QLabel(_QLabel):
    def __init__(self, text='', *args, **kwargs):
        self._original = original_text(text)
        self._tip_original = None
        super().__init__(localized(text), *args, **kwargs)
    def setText(self, text):
        self._original = original_text(text)
        super().setText(localized(text))
    def setToolTip(self, text):
        self._tip_original = original_text(text)
        super().setToolTip(localized(text))
    def retranslate(self):
        _QLabel.setText(self, localized(self._original))
        if self._tip_original is not None:
            _QLabel.setToolTip(self, localized(self._tip_original))

class QPushButton(_QPushButton):
    def __init__(self, text='', *args, **kwargs):
        self._original = original_text(text)
        self._tip_original = None
        super().__init__(localized(text), *args, **kwargs)
    def setText(self, text):
        self._original = original_text(text)
        super().setText(localized(text))
    def setToolTip(self, text):
        self._tip_original = original_text(text)
        super().setToolTip(localized(text))
    def retranslate(self):
        _QPushButton.setText(self, localized(self._original))
        if self._tip_original is not None:
            _QPushButton.setToolTip(self, localized(self._tip_original))

def paint_check_indicator(painter, bounds, checked, hovered=False, focused=False):
    """One consistent outlined-square + real checkmark for every checkbox."""
    from . import theme
    area = QRectF(bounds)
    stroke = QColor(theme.accent() if checked else theme.MUTED if hovered else theme.BORDER)
    background = QColor(theme.CARD)
    background.setAlpha(38 if theme.mode() in ('glass', 'black_glass') else
                        24 if theme.mode() == 'dark' else 110)
    painter.setPen(QPen(stroke, 1.45 if checked else 1.2))
    painter.setBrush(background)
    painter.drawRoundedRect(area, 3.3, 3.3)
    if checked:
        x, y, side = area.x(), area.y(), area.width()
        tick = QPainterPath()
        tick.moveTo(x + side * .22, y + side * .52)
        tick.lineTo(x + side * .42, y + side * .72)
        tick.lineTo(x + side * .81, y + side * .28)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(theme.accent()), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(tick)
    if focused:
        painter.setPen(QPen(QColor(theme.accent()), 1, Qt.DotLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(area.adjusted(-1.5, -1.5, 1.5, 1.5), 4, 4)


class QCheckBox(_QCheckBox):
    """Shared checkbox appearance in charts, networking, settings and benchmarks."""
    def __init__(self, text='', *args, **kwargs):
        self._original = original_text(text)
        super().__init__(localized(text), *args, **kwargs)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

    def setText(self, text):
        self._original = original_text(text)
        super().setText(localized(text))

    def retranslate(self):
        _QCheckBox.setText(self, localized(self._original))

    def paintEvent(self, event):
        from . import theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(.45)
        size = 15.
        y = (self.height() - size) / 2
        paint_check_indicator(painter, QRectF(2, y, size, size),
                              self.isChecked(), self.underMouse(), self.hasFocus())
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(QRectF(25, 0, max(0, self.width()-27), self.height()),
                         Qt.AlignLeft | Qt.AlignVCenter, self.text())
        painter.end()

class QComboBox(_QComboBox):
    def __init__(self,*args,**kwargs):
        self._source_items = []
        super().__init__(*args,**kwargs)
    def addItem(self, *args, **kwargs):
        source = original_text(args[0]) if args and isinstance(args[0],str) else None
        if source is not None:
            args = (localized(source), *args[1:])
        result = super().addItem(*args, **kwargs)
        self._source_items.append(source)
        return result
    def addItems(self, items):
        for item in items:self.addItem(item)
    def removeItem(self, index):
        if 0 <= index < len(self._source_items):
            self._source_items.pop(index)
        return super().removeItem(index)
    def setItemText(self, index, text):
        source = original_text(text)
        if index < len(self._source_items):self._source_items[index] = source
        return super().setItemText(index, localized(source))
    def setPlaceholderText(self, text):
        return super().setPlaceholderText(localized(text))
    def retranslate(self):
        for i,source in enumerate(self._source_items):
            if i < self.count() and source is not None:
                _QComboBox.setItemText(self,i,localized(source))

class QDialog(_QDialog):
    def setWindowTitle(self, text):
        return super().setWindowTitle(localized(text))

class QListWidgetItem(_QListWidgetItem):
    def __init__(self, text='', *args, **kwargs):
        super().__init__(localized(text), *args, **kwargs)

class QMessageBox(_QMessageBox):
    @staticmethod
    def warning(parent, title, text, *args, **kwargs):
        return _QMessageBox.warning(parent, localized(title), localized(text), *args, **kwargs)
    @staticmethod
    def information(parent, title, text, *args, **kwargs):
        return _QMessageBox.information(parent, localized(title), localized(text), *args, **kwargs)
    @staticmethod
    def question(parent, title, text, *args, **kwargs):
        return _QMessageBox.question(parent, localized(title), localized(text), *args, **kwargs)
    @staticmethod
    def critical(parent, title, text, *args, **kwargs):
        return _QMessageBox.critical(parent, localized(title), localized(text), *args, **kwargs)

class QFileDialog(_QFileDialog):
    @staticmethod
    def getSaveFileName(parent=None, caption='', *args, **kwargs):
        return _QFileDialog.getSaveFileName(parent, localized(caption), *args, **kwargs)
    @staticmethod
    def getExistingDirectory(parent=None, caption='', *args, **kwargs):
        return _QFileDialog.getExistingDirectory(parent, localized(caption), *args, **kwargs)

# v0.9.3.10: retranslate existing widgets in place. We deliberately do not
# reconstruct pages, which would reset scrollbars and destroy running workers.
def original_text(text):
    if not isinstance(text, str):
        return text
    from .i18n import EN, EN_MORE
    reverse = {english: german for mapping in (EN, EN_MORE) for german, english in mapping.items()}
    reverse.update({english.upper(): german.upper() for mapping in (EN, EN_MORE)
                    for german, english in mapping.items()})
    return reverse.get(text, text)


def retranslate_widgets(root):
    from PySide6.QtWidgets import QWidget
    for widget in [root, *root.findChildren(QWidget)]:
        handler = getattr(widget, 'retranslate', None)
        if callable(handler):
            handler()
