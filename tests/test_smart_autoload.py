"""SMART: drive tabs visible immediately, automatic first-visit scan."""
import os
import sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from vitalux.smart_ui import SmartPane
from vitalux.window import MainWindow

app = QApplication.instance() or QApplication([])
pane = SmartPane()
pane.set_devices([
    {'name': '/dev/sda', 'model': 'Example SSD'},
    {'name': '/dev/nvme0n1', 'model': 'Example NVMe'},
])
assert pane.selector.count() == 2
assert pane.selector.itemData(0) == '/dev/sda'
assert pane.selector.itemData(1) == '/dev/nvme0n1'
assert pane.selector.itemText(0).endswith('Example SSD')
assert pane.status.text() != ''

class Overview:
    class Board:
        editing = False
    board = Board()

class Disk:
    _smart_loaded = False
    _smart_worker = None
    def __init__(self):
        self.calls = 0
    def request_smart(self):
        self.calls += 1
        self._smart_loaded = True

class Stack:
    def __init__(self):
        self.index = 0
    def setCurrentIndex(self, i):
        self.index = i

class Window:
    def __init__(self):
        self.pages = [('Übersicht', Overview()), ('Laufwerke', Disk())]
        self.stack = Stack()
        self.refreshes = 0
    def _refresh_visible_page(self):
        self.refreshes += 1

view = Window()
MainWindow._switch_page(view, 1)
app.processEvents()
assert view.pages[1][1].calls == 1
MainWindow._switch_page(view, 1)
app.processEvents()
assert view.pages[1][1].calls == 1
assert view.refreshes == 2
pane.close()
print('SMART disk selector before scan and automatic first-visit check: PASS')
