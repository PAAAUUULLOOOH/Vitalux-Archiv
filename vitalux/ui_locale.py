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

class QCheckBox(_QCheckBox):
    def __init__(self, text='', *args, **kwargs):
        self._original = original_text(text)
        super().__init__(localized(text), *args, **kwargs)
    def setText(self, text):
        self._original = original_text(text)
        super().setText(localized(text))
    def retranslate(self):
        _QCheckBox.setText(self, localized(self._original))

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
