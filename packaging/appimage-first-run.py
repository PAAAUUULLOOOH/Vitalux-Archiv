import sys
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication([])
    dialog = QMessageBox()
    dialog.setWindowTitle("Vitalux – Erster Start")
    dialog.setText("Vitalux im Anwendungsmenü installieren?")
    dialog.setInformativeText("Benutzerinstallation ohne Administratorrechte oder zusätzliche Systempakete.")
    install = dialog.addButton("Jetzt installieren", QMessageBox.ButtonRole.AcceptRole)
    dialog.addButton("Nur einmal starten", QMessageBox.ButtonRole.RejectRole)
    dialog.setDefaultButton(install)
    dialog.exec()
    sys.exit(0 if dialog.clickedButton() is install else 1)
except Exception as exc:
    print(f"Vitalux: Dialog nicht verfügbar: {exc}", file=sys.stderr)
    sys.exit(1)
