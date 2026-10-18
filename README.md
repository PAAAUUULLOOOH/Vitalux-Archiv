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
| **CPU, GPU, RAM** | Auslastung, Taktraten, Speicher, Sensorwerte, PCIe, echte GPU-Taktraten und Live-Diagramme |
| **Netzwerk & System** | Schnittstellen, Übertragungsraten, Distribution, Kernel und Treiber |
| **Laufwerke** | Partitionen, SMART-Analyse und fio-Lese-/Schreibbenchmarks |
| **Einstellungen** | Farbschemas, eigene Akzentfarben, Hintergründe, Animationen und Warnwerte |
| **Updates & Info** | Bestätigte Aktualisierungen, lokaler Changelog und integrierte Anleitung |

Scrollen folgt der eingestellten Monitor-Bildwiederholrate (ohne FPS-Garantie); Touchpads bleiben direkt. **Automatisches Tiling** füllt nur größere Lücken nach dem Kachelverschieben oder Ausblenden; die Kachelabstände bleiben bei 14 px.

### Hardware-Überwachung (ohne Übertaktung)

**Grafik:** Auslastung, belegter Videospeicher, aktuelle GPU-/VRAM-Taktraten, Temperatur/Hotspot, Spannung, Leistung und Lüfterwerte in einer übersichtlichen Ansicht. Aufklappbare Details zeigen verfügbare PCIe-Linkdaten (aktuell/maximal), Mesa-Version und die Sensor-Datenquelle. Live-Diagramme bieten 60 Sekunden, 5 und 15 Minuten Verlauf. Nicht vorhandene Werte erscheinen als **Nicht verfügbar**, niemals als erfundene Nullwerte.

**CPU & Mainboard:** CPU-Temperaturverlauf, Mainboard-Hersteller/Modell/BIOS und – soweit von Linux eindeutig erkannt – ein eigener Temperaturverlauf für den Mainboard-Sensor. Kein Ersatz durch CPU- oder NVMe-Temperaturen.

**Analyse:** Min-/Max-Werte seit dem Start, manuell zurücksetzbar; sachlicher Hardwarestatus anhand der vorhandenen Warnwerte. Systemberichte lassen sich lokal als **TXT oder JSON** exportieren. Berichte können Hostnamen, System- und Netzwerkdaten enthalten; es erfolgt kein automatischer Upload.

Vitalux arbeitet vollständig lesend über vorhandene Linux-Schnittstellen. **GPU-Übertaktung und Lüftersteuerung wurden aus der Anwendung entfernt.** Es ist keine privilegierte GPU-Steuerungsengine und keine Administrator-Einrichtung mehr erforderlich. Ein gegebenenfalls aus älteren Testversionen bereits installierter Dienst wird nicht automatisch verändert oder deinstalliert.

### Design & Hintergründe

- **Farbschemas:** Glass mit Vitalux Blau (Standard), Dark, Light, Black Glass und Minimalistisch.
- **Hintergründe:** 14 integrierte Optionen plus selbst importierte PNG-, JPEG-, WebP- und BMP-Bilder mit Füllen, Einpassen, Strecken, Zentrieren und Kacheln. Nur **Funkeln** ist animiert.
- **Akzentfarben:** Acht geschützte, nicht löschbare Standardfarben, Distributionsfarbe, eigene bearbeitbare/löschbare Farben und **Hintergrundfarbe automatisch**.
- **Rendering:** CPU (Standard), OpenGL und Qt Quick (GPU-Tests) über **Einstellungen → Grafik-Rendering**; per **Jetzt neu starten** wechseln. GPU-Modi beschleunigen bisher nur den Hintergrund bzw. die Komposition, nicht alle Qt-Widgets und Diagramme.

**630 integrierte Kombinationen:** 5 Farbschemas × 14 Hintergründe × 9 Akzentoptionen (davon 8 feste Farben). Eigene Farben erweitern die Auswahl; manche Kombinationen können optisch identisch sein.

**GPU-Rückkehr:** Die Testmodi sind nicht garantiert schneller. Bei Grafikproblemen **CPU · Standard** wählen und neu starten oder `VITALUX_RENDERER=software ./run.sh` verwenden. Fehlgeschlagene GPU-Starts werden automatisch zurückgesetzt.

**Systemleiste:** Beim Hover werden CPU-, GPU- und RAM-Auslastung sowie verfügbare Temperaturen angezeigt. Im Kontextmenü lässt sich eine kompakte Live-Vorschau öffnen.

### Monitoring, Warnungen & Benchmarks

Unter **Einstellungen → Hardware-Warnungen** gelten konfigurierbare Grenzwerte für CPU/GPU, RAM und Systemlaufwerk; Folgealarme erscheinen erst nach zwischenzeitlicher Entwarnung.

Unter **Laufwerke** startet die SMART-Prüfung im Hintergrund; `fio` misst MB/s, IOPS und Latenz mit wählbaren Profilen.

> [!CAUTION]
> Laufwerks-Benchmarks schreiben temporäre Daten und belasten den Datenträger. Prüfe Ziel, freien Speicher und Datensicherung vor dem Start.

### Sprachen & Anleitung

**DE / EN** wechselt die Sprache ohne Neustart. Unter **Info → Anleitung öffnen** findest du eine neunteilige Einführung zu Navigation, Hardware, Benchmarks, Design und Updates.

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

**Versionierung:** Die letzte Ziffer zählt von 1 bis 99. Danach steigt die vorletzte Ziffer und die letzte beginnt wieder bei 1: **v0.9.3.99 → v0.9.4.1** (nicht v0.9.3.100). Dies wird beim Veröffentlichen automatisch geprüft.

## Hilfe

<details>
<summary><strong>AppImage startet nicht oder erscheint nicht im Menü</strong></summary>

Prüfe die Ausführungsberechtigung in Dolphin. Zum Testen kannst du `./Vitalux-v*-x86_64.AppImage` im Terminal starten; so bleiben Fehlermeldungen sichtbar. Für eine nachträgliche Menüintegration verwende `--install`. Manche Distributionen benötigen FUSE-Unterstützung.
</details>

<details>
<summary><strong>Installation oder Update schlägt fehl</strong></summary>

**Alle vier Vitalux-Protokolle** unter `~/.local/state/vitalux/` enthalten ab v0.9.3.70 Zeitstempel mit lokaler Zeitzone und Versionsangaben: `vitalux.log` (Programm/Qt), `errors.log` (Python-Fehler und native Crash-Traces mit Zeit-/Versions-Kennzeichnung am Start und beim Absturz), `installation.log` (Installationsvorgänge) und `restart.log` (Updates/Wiederherstellung). Die native Fehlerausgabe kann weiterhin unformatierte Stackframes enthalten, die von Zeit-/Versionsmarkierungen eingerahmt werden. Die Dateien werden nicht automatisch hochgeladen. Bei GitHub-Fehlern Internetverbindung, DNS, Systemzeit und CA-Zertifikate prüfen.
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

**Mitwirkende:** **Danke an:** [TimBooH](https://github.com/TimBooH) für die Unterstützung bei der Integration eigener Hintergrundbilder und der Grafikausgabe (OpenGL/CPU-Rendering). Der Name ist auch unter **Info** anklickbar.

## Feedback & Lizenzen

Fehler und Vorschläge über **[GitHub Issues](https://github.com/PAAAUUULLOOOH/Vitalux/issues)** melden – möglichst mit App-Version, Distribution und Desktop. Keine privaten Systemdaten veröffentlichen.

Vitalux verwendet unter anderem **Python, Qt/PySide6, psutil, fio und libaio**; Hinweise zu Drittkomponenten stehen im Paket unter `licenses/`. Für den Vitalux-Projektcode liegt derzeit keine allgemeine Lizenzdatei vor; öffentliche Einsicht ist keine automatische Nutzungserlaubnis.

---

<p align="center"><strong>Vitalux · Dein Linux-System im Blick.</strong></p>
