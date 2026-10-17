"""Headless regressions for the nine-slide help tour and DE/EN coverage.

Called using Vitalux's bundled interpreter inside the staged release package.
"""
from pathlib import Path
import ast
import faulthandler
faulthandler.enable()
import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from vitalux import i18n, theme
from vitalux.guide import GuideDialog, SLIDES
from vitalux.i18n import EN, EN_MORE, tr
from vitalux.pages_extra import InfoPage
from vitalux.ui_locale import retranslate_widgets

TRANSLATIONS = {**EN, **EN_MORE}


def check_translations():
    # Guide text is stored in a data structure, so check every slide explicitly.
    for slide in SLIDES:
        for key in slide[:-1]:
            assert key in TRANSLATIONS, f"Untranslated guide entry: {key!r}"
            assert TRANSLATIONS[key].strip(), f"Empty translation: {key!r}"
    for key in (
        "Anleitung öffnen", "Anleitung schließen",
        "Möchtest du eine kurze Einführung in Vitalux sehen?",
        "Die Anleitung erklärt die Oberfläche mit Pfeilen und Beispielen. Du kannst sie später jederzeit unter Info öffnen.",
        "Schritt {current} von {total}",
        "Später", "Nicht mehr anzeigen", "Beispielansicht – keine echten Messwerte",
    ):
        assert key in TRANSLATIONS, f"Missing popup translation: {key}"
        assert set(re.findall(r"\{\w+\}", key)) == set(
            re.findall(r"\{\w+\}", TRANSLATIONS[key])), f"Broken format fields: {key}"

    # Every literal passed to the primary user-visible widget helpers is translated.
    # English-only identifiers and dynamic strings are excluded from this static audit.
    methods = {
        "tr", "label", "Card", "KeyValue", "QPushButton",
        "QCheckBox", "QLabel", "QListWidgetItem",
        "setText", "setToolTip", "setWindowTitle", "setPlaceholderText",
        "addItem", "setItemText",
    }
    missing = []
    source = Path(__file__).resolve().parents[1] / "vitalux"
    for file in sorted(source.glob("*.py")):
        if file.name in {"i18n.py", "translations_extra.py"}:
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if isinstance(node.func, ast.Name):
                function = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function = node.func.attr
            else:
                continue
            if function not in methods:
                continue
            arg = node.args[0]
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                continue
            key = arg.value
            if not re.search(r"[äöüÄÖÜß]", key):
                continue
            if key not in TRANSLATIONS and key.upper() not in TRANSLATIONS:
                missing.append(f"{file.name}:{node.lineno}: {key[:90]!r}")
    assert not missing, "Untranslated UI labels:\n" + "\n".join(missing)
    print("Translation audit: passed (German/English + guide data)")


def check_gui():
    print("CHECK GUI: entering", flush=True)
    app = QApplication.instance() or QApplication([])
    print("CHECK GUI: QApplication initialized", flush=True)
    theme.set_mode("glass")
    theme.set_accent("#52d3ff")
    app.setStyleSheet(theme.stylesheet())

    print("CHECK GUI: creating InfoPage first", flush=True)
    i18n.set_lang("de")
    page = InfoPage({"name": "TestLinux"})
    print("CHECK GUI: InfoPage created", flush=True)
    assert page.guide_button.text() == "Anleitung öffnen"
    page.close()

    for locale in ("de", "en"):
        print("CHECK GUI: locale", locale, flush=True)
        i18n.set_lang(locale)
        print("CHECK GUI: before dialog", flush=True)
        guide = GuideDialog()
        print("CHECK GUI: after dialog", flush=True)
        guide.show()
        print("CHECK GUI: after show", flush=True)
        app.processEvents()
        assert guide.windowTitle() == tr("Vitalux-Anleitung")
        assert len(SLIDES) == 9
        for idx, (title, intro, *_rest) in enumerate(SLIDES):
            print("CHECK GUI: slide", locale, idx, flush=True)
            guide.show_step(idx)
            app.processEvents()
            assert guide.heading.text() == tr(title), (locale, idx, "heading")
            assert guide.summary.text() == tr(intro), (locale, idx, "summary")
            assert str(idx+1) in guide.counter.text()
            assert guide.illustration.step == idx
            for line in guide.bullets:
                assert line.text(), (locale, idx, "empty bullet")
                if locale == "en":
                    assert not re.search(r"[äöüÄÖÜß]", line.text()), line.text()
        print("CHECK GUI: before illustration grab", flush=True)
        assert not guide.illustration.grab().isNull(), "No guide illustration painted"
        guide.show_step(0)
        assert not guide.back_btn.isEnabled()
        guide.show_step(8)
        assert guide.next_btn.text() == tr("Fertig")
        guide.close()
        guide.deleteLater()
        app.processEvents()

    # Switching languages in the live Info page must update the guide button.
    print("CHECK GUI: before InfoPage", flush=True)
    i18n.set_lang("de")
    page = InfoPage({"name": "TestLinux"})
    assert page.guide_button.text() == "Anleitung öffnen"
    i18n.set_lang("en")
    retranslate_widgets(page)
    assert page.guide_button.text() == "Open guide"
    assert "Thanks to:" in page.support_credit.text()
    i18n.set_lang("de")
    retranslate_widgets(page)
    assert page.guide_button.text() == "Anleitung öffnen"
    assert "Danke an:" in page.support_credit.text()
    page.close()

    print("Native guide UI: passed (9 slides, arrows, screenshots, DE/EN)")


if __name__ == "__main__":
    print("CHECK GUI: before translations", flush=True)
    check_translations()
    print("CHECK GUI: after translations", flush=True)
    check_gui()
