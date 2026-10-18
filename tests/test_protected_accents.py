"""Protected Vitalux preset colors survive updates and user actions."""
import ast
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication, QWidget
from vitalux import settings, theme
from vitalux.control import PreferencesPage


class Host(QWidget):
    _tray = True
    render_backend_active = "software"

    def apply_appearance(self):
        theme.set_accent(settings.get("accent", "#4f8cff"))

    def set_interval(self, value):
        self.interval = value


def test_color_protection():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="vitalux-accent-protection-") as tmp:
        old = settings.PATH
        settings.PATH = str(Path(tmp) / "settings.json")
        try:
            settings.set("accent", "#ef4444")
            settings.set("custom_accents", [
                {"name": "Falsches Rot", "color": "#ef4444"},
                {"name": "Falsches Blau", "color": "#4f8cff"},
                {"name": "Mein Petrol", "color": "#123456"},
            ])
            host = Host()
            for cycle in range(2):
                page = PreferencesPage(host)
                page.resize(1000, 900)
                page.show()
                app.processEvents()
                assert settings.get("custom_accents") == [
                    {"name": "Mein Petrol", "color": "#123456"}]
                assert page.custom_accents == [{"name": "Mein Petrol", "color": "#123456"}]
                for name, value in PreferencesPage.PRESET_ACCENTS:
                    index = page.accent_combo.findData(value)
                    assert index >= 0, (name, value, cycle)
                    page.accent_combo.setCurrentIndex(index)
                    app.processEvents()
                    assert not page.edit_custom_accent_button.isVisible(), name
                    assert not page.remove_custom_accent_button.isVisible(), name
                    page.remove_custom_accent()
                    page.edit_custom_accent()
                    assert page.accent_combo.findData(value) == index, name
                page.accent_combo.setCurrentIndex(
                    page.accent_combo.findData("#123456"))
                app.processEvents()
                assert page.edit_custom_accent_button.isVisible()
                assert page.remove_custom_accent_button.isVisible()
                page.close()
            host.close()
            assert settings.get("custom_accents") == [
                {"name": "Mein Petrol", "color": "#123456"}]
        finally:
            settings.PATH = old


def test_no_first_close_tray_toast():
    path = Path(__file__).resolve().parents[1] / "vitalux/window.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    methods = [method for cls in ast.walk(tree)
               if isinstance(cls, ast.ClassDef)
               for method in cls.body
               if isinstance(method, ast.FunctionDef) and method.name == "closeEvent"]
    assert len(methods) == 1
    code = ast.get_source_segment(path.read_text(encoding="utf-8"), methods[0])
    assert "showMessage(" not in code
    assert "_hide_to_tray()" in code
    assert "_tray_announce" not in path.read_text(encoding="utf-8")


if __name__ == "__main__":
    test_color_protection()
    test_no_first_close_tray_toast()
    print("Protected presets, legacy cleanup, restart and quiet tray: PASS")
