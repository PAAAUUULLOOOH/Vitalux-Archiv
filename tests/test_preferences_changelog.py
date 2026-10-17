"""Qt tests for unified checks, compact thresholds, custom accents, changelog."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QColorDialog, QInputDialog, QWidget, QFrame, QMessageBox, QAbstractSpinBox

from vitalux import __version__, changelog, i18n, settings, theme
from vitalux.control import PreferencesPage
from vitalux.pages_extra import UpdatePage
from vitalux.update_manager import UpdateManager
from vitalux.widgets import ChartSeriesCheckBox
from vitalux.smart_ui import SmartPane


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
        original_notice = QMessageBox.information
        try:
            settings.set("accent", "auto")
            window = FakeWindow()
            page = PreferencesPage(window)
            page.resize(1100, 900)
            page.show()
            app.processEvents()

            warning_x = set()
            warning_gaps = []
            for name, spin in page.alert_boxes.items():
                assert spin.width() == 84, (name, spin.width())
                assert spin.buttonSymbols() == QAbstractSpinBox.NoButtons, name
                assert spin.alignment() & Qt.AlignHCenter, name
                assert spin.alignment() & Qt.AlignVCenter, name
                assert spin.value() > 0
                label_widget = page.alert_labels[name]
                x = spin.mapTo(page, QPoint(0, 0)).x()
                warning_x.add(x)
                gap = x - (label_widget.mapTo(page, QPoint(0, 0)).x() + label_widget.width())
                warning_gaps.append(gap)
            assert len(warning_x) == 1, f"Unaligned warning fields: {warning_x}"
            assert min(warning_gaps) >= 8, warning_gaps
            assert max(warning_gaps) <= 42, warning_gaps

            # Every dropdown, including the SMART selector, uses the same Qt
            # popup background and palette in all five Vitalux themes.
            smart = SmartPane()
            smart.show()
            app.processEvents()
            for scheme in ("dark", "light", "glass", "black_glass", "minimal"):
                theme.set_mode(scheme)
                page.setStyleSheet(theme.stylesheet())
                for dropdown in (page.mode, page.accent_combo, page.interval,
                                 page.motion_combo, smart.selector):
                    assert dropdown.view().frameShape() == QFrame.NoFrame
                    assert dropdown.view().autoFillBackground()
                    assert dropdown.maxVisibleItems() == 10
                    assert 78 <= dropdown.sizeHint().width() <= 196
                    assert "width: 0px; border: none" in theme.stylesheet()
                    # The CLOSED field must use the chosen theme too, not a
                    # dark OS-supplied field that merely has a themed popup.
                    image = dropdown.grab().toImage()
                    sample = image.pixelColor(dropdown.width() - 12, dropdown.height() // 2).name()
                    assert sample == theme.combo_surface(), (scheme, sample, theme.combo_surface())
                    dropdown.showPopup()
                    app.processEvents()
                    popup = dropdown.view().window()
                    assert "background:" in popup.styleSheet(), scheme
                    expected = theme.combo_surface()
                    assert popup.palette().color(QPalette.Base).name() == expected, scheme
                    # Some Qt styles map Text to WindowText for popup
                    # containers. The explicit QSS controls visible glyphs.
                    assert f"color: {theme.TEXT};" in popup.styleSheet(), scheme
                    assert f"background-color: {expected}" in dropdown.view().styleSheet()
                    assert dropdown.view().viewport().palette().color(QPalette.Base).name() == expected
                    dropdown.hidePopup()
            smart.close()
            theme.set_mode("glass")
            page.setStyleSheet(theme.stylesheet())

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
            assert not page.edit_custom_accent_button.isVisible()
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#123456"))
            QInputDialog.getText = staticmethod(lambda *a, **k: ("Mein Petrol", True))
            page.custom_accent(page.accent_combo)
            app.processEvents()
            assert page.accent_combo.currentText() == "Mein Petrol"
            assert page.accent_combo.currentData() == "#123456"
            assert page.remove_custom_accent_button.isVisible()
            assert page.edit_custom_accent_button.isVisible()
            assert page.edit_custom_accent_button.text() == "Bearbeiten"
            assert page.remove_custom_accent_button.text() == "Löschen"
            assert page.edit_custom_accent_button.mapTo(page, QPoint(0, 0)).x() < page.remove_custom_accent_button.mapTo(page, QPoint(0, 0)).x()
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

            # Re-edit without creating a new row; the chosen color and its
            # name should be persisted and immediately applied.
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#334455"))
            QInputDialog.getText = staticmethod(lambda *a, **k: ("Mein Smaragd", True))
            page.edit_custom_accent_button.click()
            app.processEvents()
            assert page.accent_combo.count() == count
            assert page.accent_combo.currentText() == "Mein Smaragd"
            assert page.accent_combo.currentData() == "#334455"
            assert settings.get("custom_accents") == [{"name": "Mein Smaragd", "color": "#334455"}]
            assert settings.get("accent") == "#334455"
            assert page.remove_custom_accent_button.isVisible()
            assert page.edit_custom_accent_button.isVisible()

            # Editing the name alone must leave the color untouched.
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#334455"))
            QInputDialog.getText = staticmethod(lambda *a, **k: ("Moos", True))
            page.edit_custom_accent()
            assert settings.get("custom_accents") == [{"name": "Moos", "color": "#334455"}]
            assert page.accent_combo.currentText() == "Moos"
            # Cancel the color or name dialog: neither may alter the saved row.
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor())
            page.edit_custom_accent()
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#778899"))
            QInputDialog.getText = staticmethod(lambda *a, **k: ("Abgebrochen", False))
            page.edit_custom_accent()
            assert settings.get("custom_accents") == [{"name": "Moos", "color": "#334455"}]
            # Reject duplicate preset colors.
            QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#52d3ff"))
            QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
            page.edit_custom_accent()
            assert settings.get("custom_accents") == [{"name": "Moos", "color": "#334455"}]

            page.accent_combo.setCurrentIndex(0)
            app.processEvents()
            assert not page.edit_custom_accent_button.isVisible()
            assert not page.remove_custom_accent_button.isVisible()
            page.accent_combo.setCurrentIndex(page.accent_combo.findData("#334455"))
            app.processEvents()
            assert page.edit_custom_accent_button.isVisible()
            page.remove_custom_accent_button.click()
            app.processEvents()
            assert page.accent_combo.findData("#334455") == -1
            assert settings.get("custom_accents") == []
            assert settings.get("accent") == "auto"
            assert not page.remove_custom_accent_button.isVisible()
            assert not page.edit_custom_accent_button.isVisible()

            # Old installations with one unnamed color remain editable.
            settings.set("accent", "#bbaacc")
            page2 = PreferencesPage(window)
            page2.resize(1100, 900)
            page2.show()
            app.processEvents()
            assert page2.accent_combo.findData("#bbaacc") >= 0
            assert page2.remove_custom_accent_button.isVisible()
            assert page2.edit_custom_accent_button.isVisible()
            assert page2.accent_combo.currentText() == "Eigene Farbe"
            page2.remove_custom_accent_button.click()
            assert settings.get("accent") == "auto"

            # Changing language localizes both buttons and keeps item values.
            i18n.set_lang("en")
            page2.accent_combo.retranslate()
            page2.edit_custom_accent_button.retranslate()
            page2.remove_custom_accent_button.retranslate()
            assert page2.accent_combo.findData("auto") == 0
            assert page2.edit_custom_accent_button.text() == "Edit"
            assert page2.remove_custom_accent_button.text() == "Delete"
            i18n.set_lang("de")
            page2.close()
            page.close()
        finally:
            QColorDialog.getColor = original_color
            QInputDialog.getText = original_name
            QMessageBox.information = original_notice
            settings.PATH = prior
    print("Editable named accents, explicit Edit/Delete actions, adaptive dropdown palettes, warning labels and localized buttons: PASS")


def check_changelog(app):
    versions = changelog.entries()
    assert versions and versions[0][0] == __version__, (versions, __version__)
    assert len(changelog.version_notes(__version__)) >= 3
    assert "Dropdown" in " ".join(changelog.version_notes(__version__, lang="de"))
    assert "drop-down" in " ".join(changelog.version_notes(__version__, lang="en"))

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
    manager.notes = ("## Deutsch\n\n### Neu in nächster Version\n\n- Etwas Neues"
                     "\n\n## English\n\n### New in next version\n\n- A new feature")
    page.sync()
    app.processEvents()
    assert page.update_card.isVisible(), "New-release notes must be visible before updating"
    assert "Etwas Neues" in page.notes.text()
    i18n.set_lang("en")
    page.retranslate()
    app.processEvents()
    assert "A new feature" in page.notes.text()
    assert "Etwas Neues" not in page.notes.text()
    assert "drop-down" in page.changelog_details.text()
    assert page.changelog_select.currentData() == __version__
    i18n.set_lang("de")
    page.retranslate()
    assert "Etwas Neues" in page.notes.text()
    assert "Dropdown" in page.changelog_details.text()
    manager.status = "uptodate"
    manager.notes = ""
    page.sync()
    app.processEvents()
    assert page.changelog_card.isVisible(), "History must stay visible after installing"
    assert page.changelog_select.count() > 1
    page.changelog_select.setCurrentIndex(1)
    assert page.changelog_details.text(), "Past release notes must remain accessible"
    selected = page.changelog_select.currentData()
    i18n.set_lang("en")
    page.retranslate()
    assert page.changelog_select.currentData() == selected
    assert "drop-down" in page.changelog_details.text().lower()
    i18n.set_lang("de")
    page.close()
    manager.shutdown()
    print("Offline changelog history and pre-/post-update visibility: PASS")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    check_preferences(app)
    check_changelog(app)
