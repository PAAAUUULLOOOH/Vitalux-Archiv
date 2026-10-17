<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/vitalux-readme-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/vitalux-readme-light.svg">
    <img src="assets/vitalux-readme-light.svg" alt="Vitalux" width="270">
  </picture>
</p>

<h3 align="center">Dein Linux-System. Alle wichtigen Informationen. Eine Anwendung.</h3>

<p align="center">Nativer Linux-Systemmonitor mit Live-Dashboard, Sensoren, Laufwerksdiagnose und Benchmarks.</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest"><img alt="Aktuelle Version" src="https://img.shields.io/github/v/release/PAAAUUULLOOOH/Vitalux?label=Version"></a>
  <img alt="Linux x86-64" src="https://img.shields.io/badge/Linux-x86__64-1793d1?logo=linux&logoColor=white">
  <img alt="Sprachen" src="https://img.shields.io/badge/DE%20%7C%20EN-5375bf">
  <img alt="Entwicklung" src="https://img.shields.io/badge/Status-Entwicklung-orange">
</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest"><strong>Aktuelle Version herunterladen</strong></a>
  &nbsp;·&nbsp; <a href="#funktionen">Funktionen</a>
  &nbsp;·&nbsp; <a href="#installation">Installation</a>
  &nbsp;·&nbsp; <a href="#updates">Updates</a>
  &nbsp;·&nbsp; <a href="#hilfe">Hilfe</a>
</p>

> [!NOTE]
> Vitalux ist in Entwicklung. Sensoren und verfügbare Hardwaredaten hängen von Linux, Treibern und Zugriffsrechten ab.

<p align="center">
  <img src="assets/vitalux-dashboard-preview.png" alt="Vitalux-Dashboard im Glass-Design" width="1080">
</p>
<p align="center"><sub>Beispielansicht eines Linux-Testsystems; angezeigte Werte können abweichen.</sub></p>

## Funktionen

| Bereich | Inhalt |
| --- | --- |
| **Übersicht** | Live-Dashboard mit frei anordenbaren Kacheln, Diagrammen und Systemlaufzeit |
| **CPU, GPU, RAM** | Auslastung, Taktraten, Speicher und verfügbare Sensorwerte |
| **Netzwerk & System** | Schnittstellen, Übertragungsraten, Distribution, Kernel und Treiber |
| **Laufwerke** | Partitionen, SMART-Analyse und fio-Lese-/Schreibbenchmarks |
| **Einstellungen** | Farbschemas, eigene Akzentfarben, Hintergründe, Animationen und Warnwerte |
| **Updates & Info** | Bestätigte Aktualisierungen, lokaler Changelog und integrierte Anleitung |

### Design & Hintergründe

- **Farbschemas:** Standardmäßig **Glass mit Vitalux Blau**. Auch Dark, Light, Black Glass und Minimalistisch stehen zur Verfügung. Bereits gespeicherte Einstellungen bleiben unverändert.
- **Hintergründe:** **Automatisch (Farbschema)** sowie die Originale Dark, Light, Glass, Black Glass und Minimalistisch. Dazu neun neue Stile: **Hell** (Perlmutt, Morgenlicht, Eisblau), **Regenbogen** (Pastell, Prisma) und **Dunkel** (Tiefsee, Mitternacht, Samt, Graphit). Vorherige Zusatzhintergründe wurden entfernt; gespeicherte frühere Auswahlen fallen automatisch auf das aktuelle Farbschema zurück.
- **Anpassung:** Farbintensität und Hintergrundweichheit (0–100 %) mit eigenen Qt-Reglern; auf Wunsch deutlichere, farblich abgestimmte Animationen für **alle Hintergründe** – auch für Minimalistisch als monochromer Lichtschein. Animationen sind standardmäßig **aus**.
- **Akzentfarben & Symbole:** Vitalux Blau, Cyan, Violett, Grün, Orange und Rosa ändern auch das App-, Fenster- und Tray-Symbol. Bei einer Benutzerinstallation wird das Symbol im KDE-Anwendungsmenü ebenfalls aktualisiert (der Icon-Cache kann kurz verzögert sein). Eigene Farben bleiben bearbeitbar.
- **Bedienung:** Die Seitenleiste lässt sich am **Punkte-Griff oben** per Ziehen links oder rechts andocken, alternativ durch Anklicken des Griffs. Position und zugehörige Pfeile werden gespeichert beziehungsweise gespiegelt. Der Pfeil für die Dashboard-Layoutbearbeitung verliert nach dem Schließen seine Markierung. Hover-Texthinweise bleiben deaktiviert.

**Abgestimmtes Design:** Die Seitenleiste ist farblich an die Kacheln angepasst und kann links oder rechts sitzen. Der Zusammenklapppfeil und der Dashboard-Layoutpfeil orientieren sich an der Position. Das Glühen bei Updates bleibt auf das ausgewählte Symbol und dessen Akzentfarbe abgestimmt.

Die Hintergrundeffekte sind **lokal gerenderte Qt-Farbverläufe**. Es werden weder ein Browser noch externe Hintergrunddateien benötigt.

### Monitoring, Warnungen & Benchmarks

In **Einstellungen → Hardware-Warnungen** aktivierst du Grenzwerte für CPU-/GPU-Temperatur, RAM und Systemlaufwerk. Zahlen und Einheiten sind in kompakten, linksbündig ausgerichteten Feldern sichtbar. Warnungen werden erst nach ausreichender Rückkehr unter den Grenzwert erneut ausgelöst; bei mehreren Grafikkarten zählt die höchste verfügbare GPU-Temperatur.

Beim Öffnen von **Laufwerke** werden die SMART-Daten automatisch im Hintergrund geprüft. Die Datenträgerauswahl ist sofort sichtbar; der Button erlaubt jederzeit eine erneute Prüfung. Benchmarks mit `fio` messen MB/s, IOPS und Latenz mit konfigurierbaren Profilen.

> [!CAUTION]
> Laufwerks-Benchmarks schreiben temporäre Daten und belasten den Datenträger. Prüfe Ziel, freien Speicher und Datensicherung vor dem Start.

### Sprachen & Anleitung

Zwischen **Deutsch und Englisch** wechselst du unten in der Seitenleiste mit **DE / EN**, ohne Neustart. Unter **Info → Anleitung öffnen** erläutert eine integrierte neunteilige Führung Navigation, Hardwaredaten, Benchmarks, Hintergrundgestaltung sowie Update-Hinweise im Tray. Sie ist auch nach dem ersten Start verfügbar.

## Download

Alle Dateien liegen unter **[GitHub Releases](https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest)**.

| Datei | Zweck |
| --- | --- |
| `Vitalux-vVERSION-x86_64.AppImage` | **Empfohlen:** direkt starten oder für den Benutzer installieren |
| `Vitalux-vVERSION-linux-x86_64.zip` | Vollversion zum Entpacken |
| `Vitalux-vVERSION-Update-von-vVORVERSION.zip` | Manuelles Differenzupdate für die angegebene Vorgängerversion; **nicht** fürs AppImage |
| `Vitalux-vVERSION-SHA256SUMS.txt` | SHA-256-Prüfsummen |

## Installation

**AppImage (empfohlen)**

1. AppImage aus dem aktuellen Release herunterladen.
2. In KDE Dolphin unter **Eigenschaften → Berechtigungen** ausführbar machen.
3. Per Doppelklick starten und **„Jetzt installieren“** oder **„Nur einmal starten“** wählen.

Bei der Benutzerinstallation wird das AppImage nach `~/.local/opt/vitalux/Vitalux.AppImage` kopiert und ein Anwendungsmenüeintrag angelegt. Normalerweise sind keine Administratorrechte nötig. Der Start ohne Installation ist ebenfalls möglich.

Optional per Terminal im Downloadordner (dort sollte sich nur das gewünschte Vitalux-AppImage befinden):

```bash
chmod +x ./Vitalux-v*-x86_64.AppImage
./Vitalux-v*-x86_64.AppImage --install
# Ohne Installation: ./Vitalux-v*-x86_64.AppImage --portable
```

**ZIP:** Komplett entpacken und `run.sh` aus dem entpackten Ordner starten. Falls nötig: `chmod +x run.sh && ./run.sh`. Das enthaltene `Portable-pruefen.sh` unterstützt die Fehlerdiagnose.

<details>
<summary><strong>Installationspfade</strong></summary>

| Bestandteil | Standardpfad |
| --- | --- |
| AppImage | `~/.local/opt/vitalux/Vitalux.AppImage` |
| Desktopdatei | `~/.local/share/applications/vitalux.desktop` |
| Startbefehl | `~/.local/bin/vitalux` |
| Symbol | `~/.local/share/icons/hicolor/scalable/apps/vitalux.svg` |
| Einstellungen | `~/.config/vitalux/settings.json` |

XDG-Konfigurationen können die Pfade beeinflussen.
</details>

## Updates

Vitalux prüft **beim Start und ungefähr alle sechs Stunden** GitHub Releases. Bei einem Update **glühen und pulsieren das Vitalux-Logo in der App und das Tray-Symbol**, außerdem wird der Updates-Reiter hervorgehoben. Eine Benachrichtigung erscheint **einmal pro Version**, sofern die Systemleiste dies unterstützt; das Tray-Menü bietet einen direkten Zugang zu Updates. **Installiert wird ausschließlich nach deiner Bestätigung**. Dort stehen auch die Neuerungen vorab und der **offline verfügbare, deutsch/englisch umschaltbare Changelog**. Downloads werden per SHA-256 geprüft; bei AppImage-Updates bleibt eine vorherige Version als Sicherung erhalten.

GitHub Actions veröffentlicht je Version **AppImage, Vollversion, passendes Differenzupdate und Prüfsummen**. Die vollständige Aktualisierung samt Neustart kann sich je nach Distribution unterscheiden.

## Hilfe

<details>
<summary><strong>AppImage startet nicht oder erscheint nicht im Menü</strong></summary>

Prüfe die Ausführungsberechtigung in Dolphin. Zum Testen kannst du `./Vitalux-v*-x86_64.AppImage` im Terminal starten; so bleiben Fehlermeldungen sichtbar. Für eine nachträgliche Menüintegration verwende `--install`. Manche Distributionen benötigen FUSE-Unterstützung.
</details>

<details>
<summary><strong>Installation oder Update schlägt fehl</strong></summary>

Installationsprotokoll: `~/.local/state/vitalux/installation.log`. Bei GitHub-Fehlern Internetverbindung, DNS, Systemzeit und CA-Zertifikate prüfen; die Updateprüfung im Reiter **Updates** wiederholen.
</details>

<details>
<summary><strong>Sensor-, SMART- oder Benchmarkwerte fehlen</strong></summary>

Nicht alle Sensoren und Laufwerke liefern jede Kennzahl. Prüfe Treiber, Controller, Zugriffsrechte, das ausgewählte Benchmark-Laufwerk und freien Speicher. Bei der ZIP-Version hilft `Portable-pruefen.sh`.
</details>

<details>
<summary><strong>Download mit SHA-256 prüfen</strong></summary>

Lade die passende `SHA256SUMS.txt` aus demselben Release und prüfe im Downloadordner:

```bash
sha256sum --ignore-missing -c Vitalux-v*-SHA256SUMS.txt
```
</details>

## Deinstallation

Nach einer Benutzerinstallation:

```bash
~/.local/opt/vitalux/Vitalux.AppImage --uninstall
```

Anwendung und Menüeintrag werden entfernt; **persönliche Einstellungen bleiben erhalten**. Ein lediglich heruntergeladenes AppImage kann einfach gelöscht werden.

## Systemanforderungen

GNU/Linux **x86-64**, Wayland oder X11, glibc **2.38+** als derzeitiges Kompatibilitätsziel; AppImage benötigt je nach Distribution FUSE. Hardwareüberwachung funktioniert offline; Internet ist für Release-Prüfungen nötig. Zielsysteme sind unter anderem openSUSE Tumbleweed, Fedora, Arch/CachyOS und weitere aktuelle Linux-Distributionen.

## Feedback & Lizenzen

Fehler und Vorschläge über **[GitHub Issues](https://github.com/PAAAUUULLOOOH/Vitalux/issues)** melden – möglichst mit App-Version, Distribution und Desktop. Keine privaten Systemdaten veröffentlichen.

Vitalux verwendet unter anderem **Python, Qt/PySide6, psutil, fio und libaio**; Hinweise zu Drittkomponenten stehen im Paket unter `licenses/`. Für den Vitalux-Projektcode liegt derzeit keine allgemeine Lizenzdatei vor; öffentliche Einsicht ist keine automatische Nutzungserlaubnis.

---

<p align="center"><strong>Vitalux · Dein Linux-System im Blick.</strong></p>
