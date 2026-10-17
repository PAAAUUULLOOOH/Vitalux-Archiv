<p align="center">
  <img src="assets/vitalux-wordmark.svg" alt="Vitalux" width="420">
</p>

<h3 align="center">Dein Linux-System. Alle wichtigen Informationen. Eine Anwendung.</h3>

<p align="center">
  <strong>Vitalux</strong> ist eine native Linux-Desktop-Anwendung für Hardware-Überwachung, Systeminformationen, Sensorwerte und Laufwerks-Benchmarks – übersichtlich in einem Dashboard zusammengefasst.
</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest"><img alt="Latest Release" src="https://img.shields.io/github/v/release/PAAAUUULLOOOH/Vitalux?label=Version"></a>
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/actions/workflows/release.yml"><img alt="AppImage Build" src="https://github.com/PAAAUUULLOOOH/Vitalux/actions/workflows/release.yml/badge.svg"></a>
  <img alt="Linux x86-64" src="https://img.shields.io/badge/Linux-x86__64-1793d1?logo=linux&logoColor=white">
  <img alt="Distribution" src="https://img.shields.io/badge/Distribution-AppImage-55aa77">
  <img alt="Projektstatus" src="https://img.shields.io/badge/Status-Entwicklung-orange">
</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest"><strong>⬇ Neueste Version herunterladen</strong></a>
  &nbsp;·&nbsp;
  <a href="#installation">Installation</a>
  &nbsp;·&nbsp;
  <a href="#funktionen">Funktionen</a>
  &nbsp;·&nbsp;
  <a href="#updates">Updates</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/issues">Fehler melden</a>
</p>

---

> [!NOTE]
> **Vitalux befindet sich in der Entwicklung.** Der AppImage-Build wird über GitHub Actions erstellt. Nicht jede Linux-Distribution und jede Hardwarefunktion wurde bereits praktisch getestet. Hinweise auf Probleme sind willkommen.

## Überblick

Vitalux vereint Live-Systemdaten und Hardwareinformationen in einer eigenständigen **Qt/PySide6-Anwendung**. Es handelt sich **nicht** um eine Webseite oder eine Browseroberfläche.

| Bereich | Was Vitalux anzeigt bzw. ermöglicht |
| --- | --- |
| **Übersicht** | Kompaktes Live-Dashboard für die wichtigsten Systemwerte und die aktuelle Auslastung |
| **Prozessor** | CPU-Auslastung, Informationen, Taktraten und verfügbare Sensordaten |
| **Grafik** | GPU-Informationen, Treiber-/Grafiklaufzeitdaten und unterstützte Messwerte |
| **Arbeitsspeicher** | RAM-Nutzung und Speicherinformationen |
| **Netzwerk** | Netzwerkschnittstellen und Übertragungswerte |
| **Laufwerke** | Datenträgerinformationen, Auslastung, verfügbare Gesundheitswerte sowie integrierter Benchmark |
| **Sensoren** | Temperatur- und weitere Sensorwerte, soweit vom System bereitgestellt |
| **System** | Angaben zu Linux-Distribution, Kernel und Systemumgebung |
| **Einstellungen** | Darstellung, Akzentfarbe und weitere Programmoptionen |
| **Updates** | GitHub-Release-Prüfung und Updatefunktion |
| **Info** | Informationen über Vitalux |

Die angezeigten Daten hängen von Hardware, Treibern, Zugriffsrechten und den verfügbaren Linux-Schnittstellen ab. Nicht jede GPU, jeder Sensor oder jedes Laufwerk stellt alle Messwerte bereit.

### Darstellung

- Mehrere Farbschemata: **Dark, Light, Glass, Black Glass und Minimal**
- Anpassbare Akzentfarben
- Native grafische Oberfläche mit Dashboard, Kacheln und Seitenleiste
- Für Linux-Desktopumgebungen mit **Wayland** oder **X11** ausgelegt

### Laufwerks-Benchmark

Der integrierte Benchmark nutzt die echte **`fio`-Engine mit `libaio`**. Unterstützt werden unter anderem:

- Sequenzielle und zufällige Lese-/Schreibtests
- Die Profile **Standard, Peak und Real World**
- Verschiedene Testgrößen, Wiederholungen, Laufzeiten und Pausen
- Einstellbare Blockgröße, Queue Depth und Thread-Anzahl
- Direkt-I/O, Testdatenoptionen und Messwertanzeige in **MB/s, IOPS und µs**

Die Testparameter sind an etablierte `fio`-basierte Benchmarks angelehnt. **Identische Messwerte mit anderen Programmen sind nicht garantiert**, da beispielsweise Cache-Zustand, Dateisystem, Temperatur und laufende Hintergrundprozesse die Ergebnisse beeinflussen.

> [!CAUTION]
> Laufwerks-Benchmarks erzeugen echte Schreibzugriffe und benötigen freien Speicherplatz. Wähle das richtige Laufwerk und führe sie nicht unbedacht auf nahezu vollen oder stark belasteten Datenträgern aus.

## Download

➡️ **[Vitalux – aktuelle GitHub-Veröffentlichung](https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest)**

Öffne auf der Release-Seite den Abschnitt **Assets**:

| Datei | Verwendung |
| --- | --- |
| **`Vitalux-vX.Y.Z-x86_64.AppImage`** | **Empfohlen:** Anwendung direkt starten oder ins Anwendungsmenü integrieren |
| `Vitalux-vX.Y.Z-x86_64.AppImage.sha256` | SHA-256-Prüfsumme des AppImages |
| `Vitalux-vX.Y.Z-linux-x86_64.zip` | Portable Entwicklungs-/Testversion zum Entpacken |

Für die normale Nutzung empfehlen wir das **AppImage**. Python, Qt und die Benchmark-Engine werden in der bereitgestellten Anwendung gebündelt; eine gesonderte Installation dieser Komponenten ist normalerweise nicht notwendig.

## Installation

### Variante A – AppImage per Doppelklick integrieren (empfohlen)

1. Lade das aktuelle **`.AppImage`** unter [Releases](https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest) herunter.
2. Öffne im Dateimanager (z. B. **Dolphin**) die **Eigenschaften → Berechtigungen** und aktiviere die Ausführung der Datei.
3. Öffne die AppImage-Datei per **Doppelklick**.
4. Beim ersten Start kannst du **„Jetzt installieren“** oder **„Nur einmal starten“** wählen.
5. Nach erfolgreicher Installation findest du **Vitalux mit eigenem Symbol im Anwendungsmenü** (z. B. unter KDE Plasma oder COSMIC).

Das AppImage wird dabei **für den aktuellen Benutzer** integriert. Es ist **keine systemweite RPM-/DEB-Installation** und erfordert hierfür keine Administratorrechte.

**Standardpfade nach der Benutzerinstallation:**

| Zweck | Pfad |
| --- | --- |
| Programm | `~/.local/opt/vitalux/Vitalux.AppImage` |
| Anwendungsmenü | `~/.local/share/applications/vitalux.desktop` |
| Startbefehl | `~/.local/bin/vitalux` |
| Programmsymbol | `~/.local/share/icons/hicolor/scalable/apps/vitalux.svg` |

Die XDG-Pfade richten sich gegebenenfalls nach deiner Desktop-Konfiguration.

### Variante B – Manuell über das Terminal installieren

Falls der Dialog nicht erscheint, kannst du die Integration selbst auslösen. Öffne ein Terminal **im Downloadordner** und passe den Dateinamen bei einer anderen Version an:

~~~bash
chmod +x Vitalux-v0.9.3.46-x86_64.AppImage
./Vitalux-v0.9.3.46-x86_64.AppImage --install
~~~

Anschließend kannst du Vitalux aus dem Anwendungsmenü oder über den Befehl `~/.local/bin/vitalux` starten.

**Ohne Installation verwenden:**

~~~bash
./Vitalux-v0.9.3.46-x86_64.AppImage --portable
~~~

> [!TIP]
> Das AppImage ist bereits eine ausführbare Anwendung. Die optionale „Installation“ kopiert es an einen festen Ort und legt einen Menüeintrag an. Sie ist nicht zwingend erforderlich, um Vitalux zu benutzen.

### Vollständiges ZIP-Paket (Entwicklungs- und Testversion)

ZIP entpacken und im extrahierten Vitalux-Ordner `run.sh` ausführen. Die Datei `Portable-pruefen.sh` unterstützt bei der Überprüfung der Laufzeitumgebung. Für die alltägliche Verwendung und Menüintegration ist das AppImage vorgesehen.

## Updates

Vitalux verwendet **GitHub Releases** als zentrale Updatequelle.

- Beim Start und anschließend ungefähr **alle sechs Stunden** wird nach einer neuen Version gesucht.
- Ist eine neue Version verfügbar, macht der **Updates-Reiter** darauf aufmerksam.
- Im Reiter werden die neue Version und – sofern veröffentlicht – die Änderungen angezeigt.
- Das Update wird erst nach deiner Auswahl von **„Jetzt aktualisieren“** heruntergeladen.
- Der Updater überprüft den heruntergeladenen Inhalt per **SHA-256** und sieht einen automatischen Neustart nach der Aktualisierung vor.
- Bei AppImage-Updates wird die bisherige Datei zur Absicherung als `.previous` aufbewahrt.

> [!IMPORTANT]
> Der vollständige Update-Ablauf (Herunterladen → Ersetzen → Neustart → gegebenenfalls Wiederherstellung) ist noch nicht auf allen Zielsystemen end-to-end bestätigt. Vor wichtigen Updates empfiehlt es sich, die bisherige AppImage-Datei aufzubewahren.

**Neue Versionen erscheinen hier:** [GitHub Releases](https://github.com/PAAAUUULLOOOH/Vitalux/releases).

## Deinstallation

Bei einer Integration über das AppImage kannst du die Anwendung mit dem ursprünglichen Download oder der installierten Datei entfernen:

~~~bash
~/.local/opt/vitalux/Vitalux.AppImage --uninstall
~~~

Dadurch werden das integrierte AppImage, sein Startmenüeintrag, das Symbol und der Startbefehl entfernt. **Persönliche Einstellungen bleiben erhalten.** Sie können bei Bedarf separat im Benutzerprofil gelöscht werden.

Wenn Vitalux nur portabel gestartet wurde, genügt es, die heruntergeladene AppImage-Datei zu löschen.

## Systemanforderungen und Kompatibilität

| Voraussetzung | Hinweis |
| --- | --- |
| Betriebssystem | GNU/Linux |
| Architektur | **x86-64 (AMD64)**; kein ARM-Build |
| C-Laufzeit | **glibc 2.38 oder neuer** als derzeitiges Kompatibilitätsziel |
| Desktop | Grafische Sitzung mit **Wayland oder X11** |
| Weitere Systemkomponenten | Einzelne Funktionen benötigen passende Kernel-/Treiber-Schnittstellen, Berechtigungen oder Dienste (z. B. UDisks2 für Laufwerksdaten) |
| AppImage-Laufzeit | Je nach Distribution ist passende **FUSE-Unterstützung** erforderlich |
| Internet | Nicht für die lokale Systemanzeige erforderlich; **für GitHub-Updateprüfungen und Downloads** schon |

Vitalux ist unter anderem für **openSUSE Tumbleweed, CachyOS/Arch, Fedora und Pop!_OS mit COSMIC** vorgesehen. Diese Nennung ist **keine Garantie für vollständige Kompatibilität**: Grafiktreiber, libc-Versionen, Sensorzugriff und AppImage-Laufzeit können je nach Installation variieren.

## Probleme beheben

<details>
<summary><strong>Beim Doppelklick startet nichts</strong></summary>

Überprüfe, ob die Datei ausführbar ist. Unter KDE Plasma kannst du das in Dolphin über **Eigenschaften → Berechtigungen** einstellen. Alternativ:

~~~bash
chmod +x Vitalux-v0.9.3.46-x86_64.AppImage
~~~

Starte die Datei zur Fehlersuche aus einem Terminal im selben Verzeichnis, damit Fehlermeldungen sichtbar bleiben.
</details>

<details>
<summary><strong>Vitalux startet, aber ist nicht im Startmenü</strong></summary>

Die Datei wurde wahrscheinlich nur portabel geöffnet. Starte die AppImage-Datei mit **`--install`**. Der Desktop-Eintrag liegt nach einer erfolgreichen Integration unter `~/.local/share/applications/vitalux.desktop`.
</details>

<details>
<summary><strong>Der Installationsdialog erscheint nicht oder die Installation schlägt fehl</strong></summary>

Nutze die manuelle Installation wie oben beschrieben. Das Installationsprotokoll kann unter `~/.local/state/vitalux/installation.log` liegen (bei abweichender XDG-Konfiguration im entsprechenden State-Verzeichnis).
</details>

<details>
<summary><strong>Benchmark- oder Sensorwerte fehlen</strong></summary>

Nicht jede Hardware stellt alle Messwerte bereit. Prüfe das gewählte Laufwerk, verfügbare Berechtigungen und gegebenenfalls `Portable-pruefen.sh` bei der ZIP-Version. Für Benchmarks sollte ausreichend freier Speicherplatz vorhanden sein.
</details>

Weitere Fehler und Vorschläge: **[GitHub Issues](https://github.com/PAAAUUULLOOOH/Vitalux/issues)**. Bitte möglichst die Vitalux-Version, Linux-Distribution, Desktopumgebung (Wayland/X11), eine kurze Reproduktionsanleitung und die vollständige Fehlermeldung angeben. Keine privaten Zugangsdaten oder persönlichen Dateien veröffentlichen.

## Integrität der Downloads prüfen

Neben dem AppImage befindet sich im Release eine SHA-256-Datei. Wenn beide Dateien im selben Ordner liegen, kannst du die Prüfsumme kontrollieren:

~~~bash
sha256sum -c Vitalux-v0.9.3.46-x86_64.AppImage.sha256
~~~

Bei einer erfolgreichen Prüfung wird `OK` angezeigt. Passe den Dateinamen an die heruntergeladene Version an.

## Entwicklung und Veröffentlichungen

GitHub Actions übernimmt die Erstellung des AppImages:

1. Eine neue **ZIP-Vollversion** wird mit einem passenden Versions-Tag als GitHub-Release-Asset bereitgestellt.
2. Der Workflow [Vitalux AppImage Release](https://github.com/PAAAUUULLOOOH/Vitalux/actions/workflows/release.yml) erstellt daraus das AppImage.
3. Das AppImage und die passende SHA-256-Datei werden unter **Assets** desselben Releases veröffentlicht.

Die Build- und Integrationsskripte liegen unter [`packaging/`](packaging/). Der aktuelle Repository-Inhalt dient vorrangig der **Veröffentlichung und Paketierung**; nicht der gesamte Anwendungscode ist hier bereits separat eingecheckt.

Die Versionierung verwendet das Format `vX.Y.Z` beziehungsweise während der Entwicklung `vX.Y.Z.N`.

## Verwendete Technologien und Hinweise zu Lizenzen

Vitalux setzt unter anderem auf **Python 3**, **Qt 6 / PySide6**, **psutil**, **fio** und **libaio**. Hinweise zu gebündelten Drittkomponenten und ihren Lizenzen liegen im jeweiligen Release-Paket unter `licenses/`.

Für den Vitalux-Projektcode ist hier aktuell keine eigenständige allgemeine Lizenzdatei ausgewiesen. Die öffentliche Verfügbarkeit des Repositories bedeutet daher nicht automatisch, dass beliebige Weiterverwendung oder Weiterverteilung des Projektcodes gestattet ist.

---

<p align="center">
  <strong>Vitalux · Native Systeminformationen für Linux</strong><br>
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases">Releases</a> ·
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/issues">Issues & Feedback</a> ·
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/actions">Builds</a>
</p>
