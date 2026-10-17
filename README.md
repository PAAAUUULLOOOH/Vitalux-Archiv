# Vitalux

Linux-Systemmonitor mit Hardwareinformationen, Sensoren und Laufwerksbenchmarks.

## Veröffentlichungsformate

- **AppImage:** Hauptversion für Linux x86-64, mit Benutzerinstallation und GitHub-Updates.
- **Portable ZIP:** Entwicklungs- und Testversion mit gebündeltem Python, Qt und `fio`.

## Erstes AppImage veröffentlichen

1. Gehe zu **Releases → Draft a new release**.
2. Erstelle den Tag **`v0.9.3.46`**.
3. Lade **vor dem Veröffentlichen** das vollständige Archiv **`Vitalux-v0.9.3.46-linux-x86_64-Portabel.zip`** hoch.
4. Veröffentliche den Release. Der GitHub-Actions-Workflow erstellt danach **`Vitalux-v0.9.3.46-x86_64.AppImage`** und die passende SHA-256-Datei.
5. Sieh unter **Actions → Vitalux AppImage Release** nach, ob der Build erfolgreich ist.

Falls die ZIP erst nach dem Release hochgeladen wurde, starte den Workflow manuell unter **Actions → Vitalux AppImage Release → Run workflow** mit dem vorhandenen Release-Tag.

## Installation

Das AppImage ist selbstständig startfähig. Nach dem ersten Doppelklick (Datei zuvor ausführbar machen) fragt Vitalux, ob es als Desktop-App ins Benutzerverzeichnis integriert oder nur einmal portabel gestartet werden soll.

Alternativ kann die AppImage-Datei mit `--install`, `--portable` oder `--uninstall` aufgerufen werden. Die Installation erzeugt `~/.local/share/applications/vitalux.desktop`; die alte Datei `Vitalux-starten.desktop` wird nicht benötigt.

Der integrierte Updater überprüft GitHub Releases und kann eine neue Version herunterladen, prüfen, ersetzen und Vitalux neu starten. Vor der allgemeinen Veröffentlichung sind ein echter GitHub-Build und ein Update-Test unter KDE/Wayland sowie COSMIC erforderlich.

Hinweis: AppImage ist für Linux x86-64. Kompatibilität mit jeder Linux-Distribution wird nicht garantiert.
