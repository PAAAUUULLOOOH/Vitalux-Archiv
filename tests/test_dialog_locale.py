"""Dialogs follow Vitalux's selected language, not Qt's host locale."""
import os
import sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from vitalux.i18n import set_lang
from vitalux.ui_locale import QMessageBox

app = QApplication.instance() or QApplication([])
prompt = ('Alle Anzeige-, Überwachungs- und Warnungseinstellungen auf '
          'die Standardwerte zurücksetzen? Dashboard-Anordnung und Sprache bleiben erhalten.')

for code, positive, negative in (('de', 'Ja', 'Nein'),
                                  ('en', 'Yes', 'No')):
    set_lang(code)
    seen = {}
    def inspect_and_cancel():
        dialog = app.activeModalWidget()
        assert dialog is not None, 'The confirmation popup is not modal'
        yes = dialog.button(QMessageBox.Yes)
        no = dialog.button(QMessageBox.No)
        seen['buttons'] = (yes.text(), no.text())
        seen['message'] = dialog.text()
        no.click()

    QTimer.singleShot(0, inspect_and_cancel)
    # Fail closed rather than block a release indefinitely on a headless Qt
    # platform if native modal focus/translation behavior changes.
    def watchdog():
        dialog = app.activeModalWidget()
        if dialog is not None:
            dialog.reject()
    QTimer.singleShot(2000, watchdog)
    result = QMessageBox.question(None, 'Vitalux', prompt,
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    assert result == QMessageBox.No, (code, result)
    assert seen['buttons'] == (positive, negative), (code, seen)
    assert seen['message'].startswith('Reset appearance' if code == 'en'
                                       else 'Alle Anzeige'), (code, seen)

set_lang('de')
print('German and English confirmation popups and Yes/No controls: PASS')
