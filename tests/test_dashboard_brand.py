"""Qt regression checks: distro-logo editor state and live brand recoloring."""
import hashlib
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from vitalux import i18n, settings, theme
from vitalux.brand import PulseCore, themed_icon_pixmap, wordmark_pixmap
from vitalux.pages import OverviewPage


def fingerprint(pixmap):
    assert not pixmap.isNull()
    data = QBuffer()
    data.open(QIODevice.ReadWrite)
    assert pixmap.save(data, "PNG")
    return hashlib.sha256(bytes(data.data())).hexdigest()


def assert_editor(app):
    i18n.set_lang("de")
    settings.set("dashboard_distro_logo_visible", True)
    settings.set("dashboard_hidden", [])
    settings.set("dashboard_order", [])
    logo = QPixmap(96, 96)
    logo.fill(QColor("#52d3ff"))
    distro = {"name": "TestLinux", "short": "Test", "version": "2026.10"}
    page = OverviewPage(distro, logo)
    page.resize(1280, 920)
    page.show()
    app.processEvents()

    assert page.distro_logo_host.isVisible()
    assert page.board.distro_logo_visible
    assert not page.distro_logo_remove.isVisible()
    assert page.board.available_hidden() == []

    page.toggle_editor()
    app.processEvents()
    assert page.board.editing
    assert page.distro_logo_remove.isVisible()
    assert page.distro_logo_remove.property("distroLogoRemove")

    page.distro_logo_remove.click()
    app.processEvents()
    assert not page.board.distro_logo_visible
    assert not page.distro_logo_host.isVisible()
    assert page.hero_card.isVisible(), "Hiding the logo must not hide the hero card"
    assert page.board.tiles["hero"].isVisible()
    assert page.board.available_hidden() == [("distro_logo", "Distributionslogo")]

    page.board.undo()
    app.processEvents()
    assert page.board.distro_logo_visible
    assert page.distro_logo_host.isVisible()

    # Clicking X and "Verwerfen" must restore the previous saved state.
    page.board.hide_distro_logo()
    page.discard_edit()
    app.processEvents()
    assert not page.board.editing
    assert page.board.distro_logo_visible
    assert settings.get("dashboard_distro_logo_visible") is True

    # Persistently hide the logo, then reconstruct a page.
    page.toggle_editor()
    page.distro_logo_remove.click()
    page.save_editor()
    assert settings.get("dashboard_distro_logo_visible") is False
    assert page.hero_card.isVisible()

    page2 = OverviewPage(distro, logo)
    page2.resize(1280, 920)
    page2.show()
    app.processEvents()
    assert not page2.board.distro_logo_visible
    assert not page2.distro_logo_host.isVisible()
    page2.toggle_editor()
    assert ("distro_logo", "Distributionslogo") in page2.board.available_hidden()

    # Same restore method used by "Kacheln hinzufügen" menu.
    page2.board.show_tile("distro_logo")
    app.processEvents()
    assert page2.distro_logo_host.isVisible()
    page2.save_editor()
    assert settings.get("dashboard_distro_logo_visible") is True

    # Reset must bring a hidden distro logo back, without losing chips.
    page2.toggle_editor()
    page2.board.hide_distro_logo()
    page2.reset_editor()
    assert page2.board.distro_logo_visible
    assert settings.get("dashboard_distro_logo_visible") is True

    i18n.set_lang("en")
    page2.retranslate()
    assert page2.distro_logo_remove.toolTip() == "Hide distribution logo"
    page2.toggle_editor()
    page2.board.hide_distro_logo()
    assert ("distro_logo", "Distribution logo") in page2.board.available_hidden()
    page2.discard_edit()
    page2.close()
    page.close()
    print("Distro logo: hide X, layout save/discard/undo/reset, add-menu restore, DE/EN PASSED",flush=True)


def assert_brand(app):
    # Only the eight presets have individually designed icon + lettering vectors.
    presets = {
        "blue": "#4f8cff",
        "cyan": "#52d3ff",
        "violet": "#a78bfa",
        "green": "#73ba25",
        "orange": "#f59e0b",
        "yellow": "#facc15",
        "red": "#ef4444",
        "pink": "#f472b6",
    }
    icons = set()
    dark_words = set()
    light_words = set()
    for name, color in presets.items():
        settings.set("accent", color)
        theme.set_accent(color)
        for scheme in ("dark", "light", "glass", "black_glass", "minimal"):
            theme.set_mode(scheme)
            icon = themed_icon_pixmap(152)
            word = wordmark_pixmap(205, 44)
            assert icon.hasAlphaChannel(), (name, scheme)
            assert word.hasAlphaChannel(), (name, scheme)
            if scheme == "dark":
                icons.add(fingerprint(icon))
                dark_words.add(fingerprint(word))
            elif scheme == "light":
                light_words.add(fingerprint(word))
            pulse = PulseCore(size=152)
            pulse.show()
            app.processEvents()
            assert not pulse.grab().isNull(), (name, scheme, "pulse did not paint")
            if scheme == "minimal":
                assert not pulse._timer.isActive(), "Minimal theme still animating"
            pulse.close()
    assert len(icons) == len(presets), "Preset icon palettes must be different"
    assert len(dark_words) == len(presets), "Preset wordmarks must be different"
    assert len(light_words) == len(presets), "Light variants must be individually designed"

    # 'Distribution' and custom accents must leave the original untouched.
    from vitalux.brand import _pixmap
    for selected in ("auto", "#aabbcc"):
        settings.set("accent", selected)
        for scheme in ("dark", "light", "glass", "black_glass", "minimal"):
            theme.set_mode(scheme)
            icon = themed_icon_pixmap(152)
            assert fingerprint(icon) == fingerprint(_pixmap("vitalux-pulse.svg", 152, 152))
            source = "vitalux-wordmark-light.svg" if scheme == "light" else "vitalux-wordmark.svg"
            assert fingerprint(wordmark_pixmap(205, 44)) == fingerprint(
                _pixmap(source, 205, 44, ratio=2.0)), (selected, scheme)
    settings.set("accent", "auto")
    theme.set_mode("glass")
    print("Six newly authored SVG palettes + original fallback for auto/custom: PASS", flush=True)


if __name__ == "__main__":
    a = QApplication.instance() or QApplication([])
    assert_editor(a)
    assert_brand(a)
