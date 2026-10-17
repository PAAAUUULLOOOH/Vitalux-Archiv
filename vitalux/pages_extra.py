from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout

from . import APP_NAME, __version__, changelog, settings, theme
from .i18n import tr
from .pages import Page
from .ui_locale import QLabel, QPushButton, QComboBox
from .widgets import Bar, Card, KeyValue, label

CREDIT_URL = "https://github.com/TimBooH"
CREDIT_TEXT = "Danke an: TimBooH für die Unterstützung bei der Integration eigener Hintergrundbilder und der Grafikausgabe (OpenGL/CPU-Rendering)."

STATUS_TEXT = {
    "idle": "Die Updateprüfung startet automatisch.",
    "checking": "Prüfe GitHub auf eine neue Vitalux-Version …",
    "uptodate": "Vitalux ist auf dem neuesten Stand.",
    "available": "Eine neue Vitalux-Version ist verfügbar!",
    "installing": "Update wird heruntergeladen und geprüft …",
    "installed": "Update wird installiert. Vitalux startet anschließend neu …",
}

class UpdatePage(Page):
    """Only the official Vitalux GitHub release channel; no user-supplied links."""

    def __init__(self, manager):
        super().__init__("Updates", "Vitalux automatisch über GitHub aktualisieren")
        self.m = manager

        overview = Card("Vitalux – Versionsstatus")
        self.current = KeyValue("Installierte Version")
        self.current.set(__version__)
        overview.body.addWidget(self.current)
        self.status = label("", "strong", wrap=True)
        self.status.setTextFormat(Qt.PlainText)
        overview.body.addWidget(self.status)

        self.check_button = QPushButton(tr("Erneut nach Updates suchen"))
        self.check_button.setObjectName("ghostBtn")
        self.check_button.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout()
        row.addWidget(self.check_button)
        row.addStretch(1)
        overview.body.addLayout(row)
        self.content.addWidget(overview)

        # Entire update area is hidden when there is no new release.
        self.update_card = Card("Update verfügbar")
        self.latest = KeyValue("Neue Version")
        self.update_card.body.addWidget(self.latest)
        self.notes_header = label("Änderungen in dieser Version", "strong")
        self.notes = label("", "muted", wrap=True)
        self.notes.setTextFormat(Qt.PlainText)  # GitHub release body is untrusted input.
        self.notes.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.update_card.body.addWidget(self.notes_header)
        self.update_card.body.addWidget(self.notes)

        self.progress_bar = Bar()
        self.progress_bar.flat = True
        self.update_card.body.addWidget(self.progress_bar)
        self.install_button = QPushButton(tr("Jetzt aktualisieren"))
        self.install_button.setObjectName("primaryBtn")
        self.install_button.setCursor(Qt.PointingHandCursor)
        self.update_card.body.addWidget(self.install_button)
        self.content.addWidget(self.update_card)

        # This file is packaged with Vitalux, so current/past release changes
        # remain accessible even offline and after a successful upgrade.
        self.changelog_card = Card("Changelog")
        self.changelog_list = changelog.entries()
        self.changelog_select = QComboBox()
        for version, _changes in self.changelog_list:
            self.changelog_select.addItem(f"v{version}", version)
        self.changelog_select.setEnabled(bool(self.changelog_list))
        self.changelog_card.body.addWidget(self.changelog_select)
        self.changelog_details = label("", "muted", wrap=True)
        self.changelog_details.setTextFormat(Qt.PlainText)
        self.changelog_details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.changelog_card.body.addWidget(self.changelog_details)
        self.changelog_select.currentIndexChanged.connect(self._show_changelog_version)
        self._show_changelog_version()
        self.content.addWidget(self.changelog_card)

        self.check_button.clicked.connect(self.m.check)
        self.install_button.clicked.connect(self.m.install)
        self.m.changed.connect(self.sync)
        self.m.progress.connect(self.progress_bar.set_value)
        self.sync()

    def _show_changelog_version(self, *_):
        index = self.changelog_select.currentIndex()
        if 0 <= index < len(self.changelog_list):
            self.changelog_details.setText(
                changelog.displayed_changes(self.changelog_list[index][1]))
        else:
            self.changelog_details.setText(
                tr("Für diese installierte Version ist kein Changelog verfügbar."))

    def retranslate(self):
        # Called by the existing in-place language switcher. Preserve the
        # selected release while replacing its body with localized content.
        selected = self.changelog_select.currentData()
        self.changelog_list = changelog.entries()
        self.changelog_select.blockSignals(True)
        self.changelog_select.clear()
        for version, _changes in self.changelog_list:
            self.changelog_select.addItem(f"v{version}", version)
        target = self.changelog_select.findData(selected)
        self.changelog_select.setCurrentIndex(max(0, target))
        self.changelog_select.blockSignals(False)
        self._show_changelog_version()
        self.sync()

    def sync(self):
        m = self.m
        self.status.setText(tr(m.error if m.status == "error" else STATUS_TEXT.get(m.status, "")))
        self.check_button.setEnabled(m.status not in ("checking", "installing", "installed"))
        visible = m.status in ("available", "installing", "installed")
        self.update_card.setVisible(visible)
        self.latest.set(m.latest or "–")
        self.install_button.setVisible(m.status == "available")
        self.install_button.setEnabled(m.status == "available")
        self.progress_bar.setVisible(m.status == "installing")
        notes_available = bool(changelog.localized_release_notes(m.notes)) and m.status in ("available", "installing", "installed")
        self.notes_header.setVisible(notes_available)
        self.notes.setVisible(notes_available)
        translated = changelog.localized_release_notes(m.notes)
        # No HTML interpretation: downloaded GitHub text is untrusted input.
        self.notes.setText(translated.replace("### ", "").replace("## ", "")
                           .replace("- ", "• ")[:6000])


class SupportCredit(QLabel):
    """Translated acknowledgement linking only to the fixed GitHub profile."""

    def __init__(self):
        super().__init__()
        self.setObjectName("supportCredit")
        self.setAlignment(Qt.AlignHCenter)
        self.setWordWrap(True)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByMouse)
        self.setOpenExternalLinks(True)
        self.retranslate()

    def retranslate(self):
        # Translated content is escaped; only this fixed URL becomes HTML.
        heading, separator, remainder = tr(CREDIT_TEXT).partition(":")
        before, name, after = remainder.partition("TimBooH")
        if not separator or not name:
            raise ValueError("Invalid TimBooH credit translation")
        self.setText(
            f"<b>{escape(heading)}:</b>{escape(before)}"
            f'<a href="{CREDIT_URL}" style="color: {theme.accent()}; '
            f'text-decoration: underline;">TimBooH</a>{escape(after)}'
        )
        self.setAccessibleName(tr(CREDIT_TEXT))


class InfoPage(Page):
    def __init__(self, distro):
        super().__init__("Info", "Über diese App")
        c = Card(hero=True)
        c.body.addSpacing(10)
        c.body.addWidget(label("Made by PAAAUUULLOOOH", "madeBy", Qt.AlignHCenter, wrap=True))
        self.support_credit = SupportCredit()
        c.body.addWidget(self.support_credit)
        c.body.addWidget(label(f"{APP_NAME} {__version__}", "muted", Qt.AlignHCenter))
        c.body.addSpacing(10)
        self.content.addWidget(c)
        help_card = Card("Anleitung und Hilfe")
        help_card.body.addWidget(label(
            "Entdecke Vitalux in einer bebilderten Schritt-für-Schritt-Anleitung mit Pfeilen und Beispielen.",
            "muted", wrap=True))
        self.guide_button = QPushButton("Anleitung öffnen")
        self.guide_button.setObjectName("primaryBtn")
        self.guide_button.setCursor(Qt.PointingHandCursor)
        self.guide_button.clicked.connect(self.open_guide)
        help_card.body.addWidget(self.guide_button)
        self.content.addWidget(help_card)
        d = Card("Details")
        for k, v in (("Version", __version__), ("Erkannte Distribution", distro["name"]),
                     ("Einstellungsdatei", settings.PATH)):
            kv = KeyValue(k)
            kv.set(v)
            d.body.addWidget(kv)
        self.content.addWidget(d)

    def open_guide(self):
        from .guide import GuideDialog
        # Visiting the guide counts as opt-in; do not prompt again on next launch.
        settings.set("guide_intro_choice", "completed")
        dlg = GuideDialog(self.window())
        dlg.exec()
