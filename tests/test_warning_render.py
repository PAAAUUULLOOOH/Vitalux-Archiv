"""Headless Qt regression: warnings must paint all digits in every theme."""
import os
import sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from vitalux import theme
from vitalux.control import AlertThresholdField

app = QApplication.instance() or QApplication([])
field = AlertThresholdField(40, 110, '°C', 90)
field.show()
for scheme in ('dark', 'light', 'glass', 'black_glass', 'minimal'):
    theme.set_mode(scheme)
    app.setStyleSheet(theme.stylesheet())
    field.setValue(90)
    app.processEvents()
    before = field.number.grab().toImage()
    field.setValue(110)
    app.processEvents()
    after = field.number.grab().toImage()
    assert not before.isNull() and not after.isNull()
    assert before != after, ('Clipped warning digits', scheme)
    assert field.number.alignment() & Qt.AlignLeft
    assert field.number.fontMetrics().horizontalAdvance('110') <= field.number.width()
    assert field.unit_label.text() == '°C'
field.close()
print('Visible left-aligned warning digits in all themes: PASS')
