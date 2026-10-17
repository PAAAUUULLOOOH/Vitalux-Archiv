"""Qt tests for unified checks, compact thresholds, custom accents, changelog."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QColorDialog, QInputDialog, QWidget

from vitalux import __version__, changelog, i18n, settings, theme
from vitalux.control import PreferencesPage
from vitalux.pages_extra import UpdatePage
from vitalux.update_manager import UpdateManager
from vitalux.widgets import ChartSeriesCheckBox


class FakeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._tray = object()
        self.last_sample = None

    def apply_appearance(self):
        theme.set_mode(settings.get("theme", "glass"))
        theme.set_accent(settings.get("accent", "#4f8cff"))

    def set_interval(self, interval):
        self.interval = interval


def check_preferences(app):
    with tempfile.TemporaryDirectory(prefix="vitalux-options-") as folder:
        prior = settings.PATH
        settings.PATH = str(Path(folder) / "settings.json")
        original_color = QColorDialog.getColor
        original_name = QInputDialog.getText
        try:
            settings.set("accent", "auto")
            window = FakeWindow()
            page = PreferencesPage(window)
            page.resize(1100, 900)
            page.show()
            app.processEvents()

            for name, spin in page.alert_boxes.items():
                assert spin.width() == 112, (name, spin.width())
                assert spin.alignment() & Qt.AlignHCenter, name
                assert spin.alignment() & Qt.AlignVCenter, name
                assert spin.value() > 0

            # Normal Qt checkbox semantics remain intact with our painted tick.
            standard = page.alert_toggle
            chart = ChartSeriesCheckBox("Netzwerkstatus", "#52d3ff")
            chart.show()
            app.processEvents()
            standard.setChecked(False)
            standard.click()
            assert standard.isChecked()
            chart.setChecked(False)
            chart.click()
            assert chart.isChecked()
            assert not standard.grab().isNull()
            assert not chart.grab().isNull()
            chart.close()

            assert not page.remove_custom_accent_button.isVisible()
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#123456"))
            QInputDialog.getText = staticmethod(lambda *a, **k: ("Mein Petrol", True))
            page.custom_accent(page.accent_combo)
            app.processEvents()
            assert page.accent_combo.currentText() == "Mein Petrol"
            assert page.accent_combo.currentData() == "#123456"
            assert page.remove_custom_accent_button.isVisible()
            assert settings.get("custom_accents") == [{"name": "Mein Petrol", "color": "#123456"}]
            assert settings.get("accent") == "#123456"

            # Picking the identical color again does not duplicate it.
            count = page.accent_combo.count()
            page.custom_accent(page.accent_combo)
            assert page.accent_combo.count() == count
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#654321"))
            QInputDialog.getText = staticmethod(lambda *a, **k: ("Ignored", False))
            page.custom_accent(page.accent_combo)
            assert page.accent_combo.count() == count

            page.remove_custom_accent()
            app.processEvents()
            assert page.accent_combo.findData("#123456") == -1
            assert settings.get("custom_accents") == []
            assert settings.get("accent") == "auto"
            assert not page.remove_custom_accent_button.isVisible()

            # Old installations with one unnamed color remain editable.
            settings.set("accent", "#bbaacc")
            page2 = PreferencesPage(window)
            page2.resize(1100, 900)
            page2.show()
            app.processEvents()
            assert page2.accent_combo.findData("#bbaacc") >= 0
            assert page2.remove_custom_accent_button.isVisible()
            assert page2.accent_combo.currentText() == "Eigene Farbe"
            page2.remove_custom_accent_button.click()
            assert settings.get("accent") == "auto"

            # Changing language preserves item data and stored names.
            i18n.set_lang("en")
            page2.accent_combo.retranslate()
            assert page2.accent_combo.findData("auto") == 0
            i18n.set_lang("de")
            page2.close()
            page.close()
        finally:
            QColorDialog.getColor = original_color
            QInputDialog.getText = original_name
            settings.PATH = prior
    print("Custom accent names, deletion, presets, legacy colors, checkboxes and warning fields: PASS")


def check_changelog(app):
    versions = changelog.entries()
    assert versions and versions[0][0] == __version__, (versions, __version__)
    assert len(changelog.version_notes(__version__)) >= 3
    assert "Häkchen" in " ".join(changelog.version_notes(__version__))

    manager = UpdateManager()
    page = UpdatePage(manager)
    page.resize(1100, 900)
    page.show()
    app.processEvents()
    assert page.changelog_select.currentData() == __version__
    assert "• " in page.changelog_details.text()
    assert not page.update_card.isVisible()
    manager.status = "available"
    manager.latest = "0.9.3.55"
    manager.notes = "## Neu in der nächsten Version\n- Etwas Neues"
    page.sync()
    app.processEvents()
    assert page.update_card.isVisible(), "New-release notes must be visible before updating"
    assert "Etwas Neues" in page.notes.text()
    manager.status = "uptodate"
    manager.notes = ""
    page.sync()
    app.processEvents()
    assert page.changelog_card.isVisible(), "History must stay visible after installing"
    assert page.changelog_select.count() > 1
    page.changelog_select.setCurrentIndex(1)
    assert page.changelog_details.text(), "Past release notes must remain accessible"
    page.close()
    manager.shutdown()
    print("Offline changelog history and pre-/post-update visibility: PASS")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    check_preferences(app)
    check_changelog(app)
