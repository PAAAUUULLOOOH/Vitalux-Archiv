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
    icon_digests = set()
    text_digests = set()
    for mode in ("dark", "light", "glass", "black_glass", "minimal"):
        theme.set_mode(mode)
        for accent in ("#4f8cff", "#f5588d"):
            theme.set_accent(accent)
            icon = themed_icon_pixmap(152)
            text = wordmark_pixmap(205, 44)
            icon_digests.add(fingerprint(icon))
            text_digests.add(fingerprint(text))
            assert icon.hasAlphaChannel()
            assert text.hasAlphaChannel()
            pulse = PulseCore(size=152)
            pulse.show()
            app.processEvents()
            assert not pulse.grab().isNull(), f"No painted logo in {mode}"
            if mode == "minimal":
                assert not pulse._timer.isActive(), "Minimal theme should remain animation-free"
            pulse.close()
    assert len(icon_digests) == 10, "Top-left icon did not respond to every theme + accent"
    assert len(text_digests) == 10, "Top-left wordmark did not respond to every theme + accent"
    print("Original Vitalux symbol + lettering: all 5 themes and accent colors PASSED",flush=True)


if __name__ == "__main__":
    a = QApplication.instance() or QApplication([])
    assert_editor(a)
    assert_brand(a)
