"""Headless tests for subtle update indicators and the repeating check timer."""
import os
import sys
from types import SimpleNamespace
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication
from vitalux import theme
from vitalux.brand import PulseCore
from vitalux.widgets import NavButton
from vitalux.window import MainWindow
from vitalux.update_manager import UpdateManager

app = QApplication.instance() or QApplication([])
app.setStyleSheet(theme.stylesheet())

manager = UpdateManager()
assert manager._timer.isActive(), 'Background update checks are not running'
assert manager._timer.interval() == 6 * 3600 * 1000
manager._timer.stop()
manager.shutdown()

nav = NavButton('↻    Updates')
nav.resize(235, 47)
nav.show()
logo = PulseCore(132)
logo.show()
app.processEvents()

class FakeManager:
    available = True
    latest = '0.9.3.63'

status = SimpleNamespace(
    update_btn=nav, pulse_core=logo, manager=FakeManager(),
    _tray=object(), _tray_update_action=QAction(),
    _notified_update_version='0.9.3.63', _update_notice_queued=False)
MainWindow._sync_glow(status)
app.processEvents()
assert nav.glow and nav._update_version == 'v0.9.3.63'
assert logo._update_available
assert status._tray_update_action.isVisible()
assert '0.9.3.63' in status._tray_update_action.text()
assert nav.minimumHeight() >= 47
frame = nav.grab()
assert not frame.isNull()

status.manager.available = False
MainWindow._sync_glow(status)
assert not nav.glow and nav._update_version == ''
assert not logo._update_available
assert not status._tray_update_action.isVisible()
nav.close()
logo.close()
print('Update animations, tray label and six-hour polling: PASS')
