"""Erststartdialog fuer eine freiwillige AppImage-Desktopintegration."""
import sys

def main():
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication([])
        if len(sys.argv) > 2 and sys.argv[1] == "--error":
            QMessageBox.critical(None, "Vitalux – Installation", sys.argv[2])
            return 0
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Vitalux – Erster Start")
        msg.setText("Vitalux als Desktop-Anwendung installieren?")
        msg.setInformativeText(
            "Vitalux wird ohne Administratorrechte in deinem Benutzerordner abgelegt "
            "und ins Anwendungsmenü eingetragen. Alternativ kannst du es ohne "
            "Installation starten."
        )
        install = msg.addButton("Jetzt installieren", QMessageBox.ButtonRole.AcceptRole)
        portable = msg.addButton("Nur einmal starten", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(install)
        msg.exec()
        if msg.clickedButton() is install:
            return 0
        if msg.clickedButton() is portable:
            return 1
        return 2
    except Exception as exc:
        print(f"Vitalux: Erststartdialog fehlgeschlagen: {exc}", file=sys.stderr)
        return 80

if __name__ == "__main__":
    raise SystemExit(main())
