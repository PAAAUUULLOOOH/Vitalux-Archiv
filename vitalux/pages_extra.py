from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from .ui_locale import QPushButton

from . import APP_NAME, __version__
from .i18n import tr
from .pages import Page
from .widgets import Bar, Card, KeyValue, label

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

        self.check_button.clicked.connect(self.m.check)
        self.install_button.clicked.connect(self.m.install)
        self.m.changed.connect(self.sync)
        self.m.progress.connect(self.progress_bar.set_value)
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
        self.notes_header.setVisible(bool(m.notes) and m.status == "available")
        self.notes.setVisible(bool(m.notes) and m.status == "available")
        self.notes.setText((m.notes or "")[:6000])


class InfoPage(Page):
    def __init__(self, distro):
        super().__init__("Info", "Über diese App")
        c = Card(hero=True)
        c.body.addSpacing(10)
        c.body.addWidget(label("Made by PAAAUUULLOOOH", "madeBy", Qt.AlignHCenter, wrap=True))
        c.body.addWidget(label(f"{APP_NAME} {__version__}", "muted", Qt.AlignHCenter))
        c.body.addSpacing(10)
        self.content.addWidget(c)
        d = Card("Details")
        from . import settings
        for k, v in (("Version", __version__), ("Erkannte Distribution", distro["name"]),
                     ("Einstellungsdatei", settings.PATH)):
            kv = KeyValue(k)
            kv.set(v)
            d.body.addWidget(kv)
        self.content.addWidget(d)
