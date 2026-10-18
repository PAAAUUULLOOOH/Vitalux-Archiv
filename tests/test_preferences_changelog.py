"""Qt tests for unified checks, compact thresholds, custom accents, changelog."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QColorDialog, QInputDialog, QWidget, QFrame
from vitalux.ui_locale import QMessageBox

from vitalux import __version__, changelog, i18n, settings, theme
from vitalux.control import PreferencesPage, AlertThresholdField
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
            # Older releases could mistakenly persist an immutable preset as
            # a user accent, making Red deletable and removable from the menu.
            settings.set("custom_accents", [
                {"name": "Rot (alt)", "color": "#ef4444"},
                {"name": "Vitalux Blau (alt)", "color": "#4f8cff"},
            ])
            window = FakeWindow()
            page = PreferencesPage(window)
            page.resize(1100, 900)
            page.show()
            app.processEvents()

            warning_x = set()
            warning_gaps = []
            for name, spin in page.alert_boxes.items():
                assert spin.width() == 84, (name, spin.width())
                assert isinstance(spin, AlertThresholdField), name
                assert spin.value() > 0
                assert spin.number.text() == str(spin.value()), name
                assert spin.number.isVisible(), name
                assert spin.number.width() >= 26, (name, spin.number.width())
                assert spin.unit_label.text() == ('°C' if 'temp' in name else '%')
                assert spin.unit_label.isVisible(), name
                assert not spin.number.grab().isNull(), name
                label_widget = page.alert_labels[name]
                x = spin.mapTo(page, QPoint(0, 0)).x()
                warning_x.add(x)
                gap = x - (label_widget.mapTo(page, QPoint(0, 0)).x() + label_widget.width())
                warning_gaps.append(gap)
            assert len(warning_x) == 1, f"Unaligned warning fields: {warning_x}"
            assert min(warning_gaps) >= 8, warning_gaps
            assert max(warning_gaps) <= 42, warning_gaps

            # Regression: all numbers remain editable and are not a clipped
            # QSpinBox editor; persisted preferences follow valid edits only.
            threshold = page.alert_boxes["cpu_temp"]
            threshold.number.setText("97")
            assert threshold.value() == 97
            assert settings.get("cpu_temp") == 97
            threshold.number.setText("9")
            threshold.commit()
            assert threshold.value() == 97
            assert threshold.number.text() == "97"
            threshold.stepBy(1)
            assert threshold.value() == 98
            threshold.setValue(90)
            assert threshold.number.text() == "90"

            # Backdrop controls persist independently of the color scheme and
            # preserve the readable dropdown styles.
            assert page.background_combo.count() == 15  # 14 presets + imported image option
            assert page.background_combo.findData('custom_image') >= 0
            assert page.background_combo.findData('aurora') == -1
            assert page.background_combo.findData('obsidian') == -1
            assert page.background_combo.findData('nebula') == -1
            assert page.background_combo.findData('arctic') == -1
            assert page.background_combo.findData('adaptive') >= 0
            assert page.background_combo.findData('animated_sparkle') >= 0
            for name in ('pastel_rainbow', 'animated_rainbow',
                         'animated_fade', 'animated_light',
                         'animated_aurora', 'animated_waves',
                         'animated_mist', 'pearl', 'ice'):
                assert page.background_combo.findData(name) == -1
            assert page.accent_combo.findData('#facc15') >= 0
            assert page.accent_combo.findData('#ef4444') >= 0
            assert settings.get("custom_accents") == [], "Old preset duplicates must be repaired"
            for name, color in PreferencesPage.PRESET_ACCENTS:
                assert page.accent_combo.findData(color) >= 0, name
                page.accent_combo.setCurrentIndex(page.accent_combo.findData(color))
                app.processEvents()
                assert not page.edit_custom_accent_button.isVisible(), name
                assert not page.remove_custom_accent_button.isVisible(), name
                page.remove_custom_accent()  # Even a direct call must be safe.
                page.edit_custom_accent()
                assert page.accent_combo.findData(color) >= 0, name
            assert settings.get("custom_accents") == []
            # Reopening after update must restore all built-in color entries.
            restored = PreferencesPage(window)
            for name, color in PreferencesPage.PRESET_ACCENTS:
                assert restored.accent_combo.findData(color) >= 0, name
            restored.close()
            assert not hasattr(page, 'background_animate')
            assert page.background_combo.findData('theme_default') >= 0
            assert [page.background_combo.itemText(page.background_combo.findData(key))
                    for key in ('dark', 'light', 'glass', 'black_glass', 'minimal')] == [
                    'Dark', 'Light', 'Glass', 'Black Glass', 'Minimalistisch']
            assert not hasattr(page, 'background_sliders')
            assert not hasattr(page, 'background_values')
            for name in ('animated_sparkle', 'adaptive'):
                assert page.background_combo.findData(name) >= 0
            page.background_combo.setCurrentIndex(
                page.background_combo.findData('animated_sparkle'))
            assert settings.get('background_style') == 'animated_sparkle'

            # Previous themed drop-down styling is restored: a separate darker
            # control area on the right, with a readable closed label.
            smart = SmartPane()
            smart.show()
            app.processEvents()
            for scheme in ("dark", "light", "glass", "black_glass", "minimal"):
                theme.set_mode(scheme)
                page.setStyleSheet(theme.stylesheet())
                css = theme.stylesheet()
                assert "QComboBox::drop-down" in css
                assert "width: 25px; border: none; border-left: 1px solid" in css
                for dropdown in (page.mode, page.accent_combo, page.interval,
                                 page.motion_combo, smart.selector):
                    assert dropdown.view().frameShape() == QFrame.NoFrame
                    assert dropdown.view().autoFillBackground()
                    assert dropdown.maxVisibleItems() == 10
                    assert dropdown.sizeHint().width() >= 88
                    assert not dropdown.grab().isNull()
                    dropdown.showPopup()
                    app.processEvents()
                    popup = dropdown.view().window()
                    surface = theme.blend(theme.accent(), theme.CARD, .05)
                    assert f"background: {surface};" in popup.styleSheet(), scheme
                    assert popup.palette().color(QPalette.Base).name() == surface, scheme
                    assert f"color: {theme.TEXT};" in popup.styleSheet(), scheme
                    assert dropdown.view().viewport().palette().color(QPalette.Base).name() == surface
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
    german = changelog.version_notes(__version__, lang="de")
    english = changelog.version_notes(__version__, lang="en")
    assert german and english and german != english

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
    assert page.changelog_details.text() and "Zeitstempel" not in page.changelog_details.text()
    assert page.changelog_select.currentData() == __version__
    i18n.set_lang("de")
    page.retranslate()
    assert "Etwas Neues" in page.notes.text()
    assert page.changelog_details.text() and page.changelog_details.text() != ''
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
    assert page.changelog_details.text() == changelog.displayed_changes(page.changelog_list[page.changelog_select.currentIndex()][1])
    i18n.set_lang("de")
    page.close()
    manager.shutdown()
    print("Offline changelog history and pre-/post-update visibility: PASS")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    check_preferences(app)
    check_changelog(app)
