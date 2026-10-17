<p align="center">
  <img src="assets/vitalux-wordmark.svg" alt="Vitalux – Linux-Systemmonitor" width="420">
</p>

<h3 align="center">Dein Linux-System. Alle wichtigen Informationen. Eine Anwendung.</h3>

<p align="center">
  <strong>Vitalux</strong> ist eine eigenständige Linux-Desktop-Anwendung, die Hardware, Systemauslastung, Sensorwerte und Laufwerksleistung in einer modernen, übersichtlichen Oberfläche zusammenführt.
</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest"><img alt="Aktuelle Version" src="https://img.shields.io/github/v/release/PAAAUUULLOOOH/Vitalux?label=Aktuelle%20Version"></a>
  <img alt="Linux x86-64" src="https://img.shields.io/badge/Linux-x86__64-1793d1?logo=linux&logoColor=white">
  <img alt="Sprachen Deutsch und Englisch" src="https://img.shields.io/badge/Sprachen-Deutsch%20%7C%20English-5375bf">
  <img alt="Status Entwicklung" src="https://img.shields.io/badge/Status-In%20Entwicklung-orange">
</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest"><strong>⬇ Vitalux herunterladen</strong></a>
  &nbsp;·&nbsp;
  <a href="#funktionen">Funktionen</a>
  &nbsp;·&nbsp;
  <a href="#installation">Installation</a>
  &nbsp;·&nbsp;
  <a href="#sprachen">Sprachen</a>
  &nbsp;·&nbsp;
  <a href="#integrierte-anleitung">Anleitung</a>
  &nbsp;·&nbsp;
  <a href="#updates">Updates</a>
</p>

---

> [!NOTE]
> **Vitalux befindet sich in der Entwicklung.** Die verfügbaren System- und Sensorwerte hängen von der Hardware, den Linux-Treibern und den Berechtigungen ab. Einige Funktionen können je nach Distribution unterschiedlich verfügbar sein.

## Vitalux im Überblick

Mit Vitalux behältst du dein System im Blick, ohne zwischen mehreren Programmen wechseln zu müssen. Die Oberfläche ist eine **native Linux-Anwendung** – keine Webseite und kein Browserfenster.

### Funktionen

| Bereich | Beschreibung |
| --- | --- |
| **Übersicht** | Zentrales Dashboard mit wichtigen Live-Werten, Systeminformationen und Diagrammen zur aktuellen Auslastung. |
| **Prozessor** | CPU-Auslastung, Taktraten, Kerne und Threads sowie verfügbare Temperatur- und Leistungswerte. |
| **Grafik** | Informationen zur Grafikkarte, zum Grafiktreiber, zur GPU-Auslastung und zum Videospeicher, soweit verfügbar. |
| **Arbeitsspeicher** | Belegter und verfügbarer RAM, Swap-Speicher und Verlauf der Speichernutzung. |
| **Netzwerk** | Netzwerkschnittstellen, Verbindungsinformationen sowie aktuelle Download- und Uploadraten. |
| **Laufwerke** | Datenträger, Partitionen, Speicherauslastung, Laufwerksinformationen und integrierter Benchmark. |
| **Sensoren** | Verfügbare Temperaturen, Lüfterdrehzahlen, Spannungen und weitere Messwerte. |
| **System** | Details zur Linux-Distribution, zum Kernel, zur Hardware und zur Systemumgebung. |
| **Einstellungen** | Farbschemata, Akzentfarben, Animationen, Messintervalle und weitere Anpassungen. |
| **Updates** | Automatische Prüfung auf neue Vitalux-Versionen und Installation auf Wunsch. |
| **Info** | Informationen zur Anwendung und Zugriff auf die bebilderte Schritt-für-Schritt-Anleitung. |

### Persönlich anpassbares Dashboard

Passe Vitalux an deinen Geschmack an. Du kannst die Anordnung und Sichtbarkeit von Dashboard-Kacheln verändern, Akzentfarben wählen und das Erscheinungsbild wechseln.

**Verfügbare Farbschemata:** Dark, Light, Glass, Black Glass und Minimalistisch.

Glass und Black Glass kombinieren halbtransparente Elemente mit einem weichgezeichneten Hintergrund. Minimalistisch verzichtet auf aufwendige Glaseffekte und reduziert die grafische Darstellung.

### Laufwerks-Benchmark

Mit dem integrierten Benchmark kannst du die Leistung eines Laufwerks messen und verschiedene Testprofile verwenden. Vitalux zeigt unter anderem:

- **MB/s:** Wie viele Megabyte pro Sekunde gelesen oder geschrieben werden.
- **IOPS:** Wie viele Ein- und Ausgabevorgänge pro Sekunde stattfinden.
- **Latenz:** Wie lange einzelne Laufwerkszugriffe dauern.

Unterstützt werden unter anderem sequenzielle und zufällige Lese-/Schreibtests sowie anpassbare Testgrößen, Laufzeiten und Durchläufe. Die Ergebnisse können von Dateisystem, Laufwerkstemperatur, Cache und laufenden Programmen beeinflusst werden.

> [!CAUTION]
> **Wichtig bei Schreibtests:** Benchmarks erzeugen echte Schreibzugriffe und benötigen freien Speicherplatz. Sichere wichtige Daten, bevor du ein Laufwerk belastest, und wähle den gewünschten Datenträger sorgfältig aus.

## Sprachen

Vitalux kann vollständig über die Oberfläche zwischen **Deutsch und Englisch** umgeschaltet werden.

- **Deutsch (DE)** – deutschsprachige Menüs, Schaltflächen und Erklärungen.
- **English (EN)** – englischsprachige Benutzeroberfläche und Anleitung.

Die Sprachschaltflächen **DE** und **EN** findest du unten in der linken Seitenleiste. Die Sprache lässt sich jederzeit wechseln, ohne Vitalux neu zu starten.

## Integrierte Anleitung

Neu bei Vitalux ist eine **bebilderte, interaktive Schritt-für-Schritt-Anleitung**, mit der du die wichtigsten Funktionen der Anwendung kennenlernst.

Die Anleitung öffnet sich in einem eigenen Fenster direkt in Vitalux. Sie besteht aus **neun übersichtlichen Seiten** mit einer beispielhaften Programmoberfläche, **Pfeilen und farbigen Markierungen**. So erkennst du, wo sich Funktionen befinden und wofür sie gedacht sind.

Die Einführung erklärt beispielsweise das Dashboard, die linke Navigation, CPU und GPU, Netzwerk und Laufwerke, den Benchmark, Sensoren, Einstellungen und Updates. Auch Begriffe wie **MB/s, IOPS und Latenz** werden verständlich erläutert.

**So öffnest du die Anleitung:**

1. Öffne in der linken Seitenleiste den Bereich **Info**.
2. Klicke auf **„Anleitung öffnen“**.
3. Wechsle mit **„Weiter“** und **„Zurück“** zwischen den Erklärungen.

Beim ersten Start bietet Vitalux die Einführung optional an. Du kannst sie sofort ansehen, auf später verschieben oder die automatische Nachfrage deaktivieren. **Über Info bleibt die Anleitung jederzeit erreichbar.** Sie steht auf Deutsch und Englisch zur Verfügung.

## Download

**➡️ [Zur neuesten Vitalux-Version auf GitHub](https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest)**

Öffne dort den Bereich **Assets**. Die wichtigsten Dateien sind:

| Datei | Wofür sie gedacht ist |
| --- | --- |
| `Vitalux-vX.Y.Z-x86_64.AppImage` | **Empfohlen:** Fertige Desktop-Anwendung mit optionaler Integration ins Anwendungsmenü. |
| `Vitalux-vX.Y.Z-linux-x86_64.zip` | Vollständiges ZIP-Paket zum Entpacken und Starten. |
| `Vitalux-vX.Y.Z-SHA256SUMS.txt` | Prüfsummen zur Kontrolle der heruntergeladenen Dateien. |

Die Versionsnummer `X.Y.Z` ist ein Platzhalter; die tatsächlichen Dateinamen stehen bei der jeweiligen Veröffentlichung.

## Installation

### AppImage – empfohlen

Das AppImage ist die einfachste Möglichkeit, Vitalux zu verwenden. Es enthält die für die Anwendung benötigten Programmkomponenten und benötigt normalerweise keine separate Python- oder Qt-Installation.

1. Lade das aktuelle **AppImage** über [GitHub Releases](https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest) herunter.
2. Öffne die **Eigenschaften** der Datei im Dateimanager, beispielsweise Dolphin, und erlaube unter **Berechtigungen** die Ausführung.
3. Starte die Datei per **Doppelklick**.
4. Beim ersten Start kannst du wählen, ob Vitalux **installiert** oder **ohne Installation gestartet** werden soll.

**Bei der Installation** legt Vitalux einen Eintrag mit Programmsymbol im Anwendungsmenü an. Du kannst die Anwendung anschließend wie gewohnt aus dem Startmenü öffnen. Die Integration gilt für dein Benutzerkonto und benötigt normalerweise keine Administratorrechte.

**Ohne Installation** kannst du das AppImage direkt verwenden. Deine Wahl lässt sich später ändern, indem du die Anwendung entsprechend erneut startest.

### Alternative: ZIP-Paket

Lade die ZIP-Vollversion herunter, entpacke sie und starte im entpackten Vitalux-Ordner die Datei `run.sh`. Für die übliche Desktop-Nutzung empfehlen wir das AppImage.

## Updates

Vitalux prüft **bei jedem Programmstart** automatisch, ob eine neue Version auf dem offiziellen GitHub-Projekt verfügbar ist. Während das Programm geöffnet bleibt, folgen ungefähr alle sechs Stunden weitere Prüfungen.

Wenn ein Update verfügbar ist, **pulsiert der Updates-Reiter links in der Seitenleiste**. Im Reiter kannst du die neue Versionsnummer und die verfügbaren Versionshinweise ansehen.

Mit **„Jetzt aktualisieren“** startest du den Download und die Installation. Die heruntergeladene Datei wird anhand einer SHA-256-Prüfsumme geprüft. Das AppImage-Update ist auf einen automatischen Neustart ausgelegt.

**Wichtig:** Vitalux sucht selbst nach Updates, **installiert sie aber nicht ohne deine Bestätigung**.

> [!NOTE]
> Die vollständige Aktualisierung einschließlich Neustart ist noch nicht für jede Linux-Distribution praktisch bestätigt. Bewahre vor wichtigen Updates gegebenenfalls eine Kopie deines bisherigen AppImages auf.

## Systemanforderungen

| Voraussetzung | Hinweise |
| --- | --- |
| **Betriebssystem** | GNU/Linux |
| **Architektur** | x86-64 (AMD64) |
| **Desktop** | Grafische Sitzung unter Wayland oder X11 |
| **Systembibliotheken** | Derzeitiges Kompatibilitätsziel: glibc 2.38 oder neuer |
| **AppImage** | Abhängig von der Distribution kann FUSE-Unterstützung notwendig sein |
| **Internet** | Nur für das Abrufen und Installieren von Updates erforderlich |

Vitalux ist unter anderem für **openSUSE Tumbleweed, CachyOS/Arch, Fedora und Pop!_OS/COSMIC** vorgesehen. Die genaue Unterstützung hängt von Linux-Version, Grafiktreiber, Hardware und bereitgestellten Systemdiensten ab.

## Häufige Fragen und Problemlösungen

<details>
<summary><strong>Beim Doppelklick öffnet sich Vitalux nicht. Was kann ich tun?</strong></summary>

Prüfe, ob das AppImage ausführbar ist. In KDE Dolphin findest du die Einstellung unter **Eigenschaften → Berechtigungen**. Falls es weiterhin nicht startet, führe die Datei aus einem Terminal aus, um die Fehlermeldung zu sehen.

</details>

<details>
<summary><strong>Warum erscheint Vitalux nicht im Anwendungsmenü?</strong></summary>

Möglicherweise hast du beim ersten Start die Verwendung ohne Installation gewählt. Starte das AppImage erneut und wähle die Installation. Danach sollte der Eintrag im Anwendungsmenü verfügbar sein.

</details>

<details>
<summary><strong>Warum werden bestimmte Sensorwerte nicht angezeigt?</strong></summary>

Nicht jede Hardware stellt alle Messwerte bereit. Besonders Temperatur-, Lüfter-, Spannungs- und SMART-Werte hängen von Treibern, Systemdiensten und Berechtigungen ab. Vitalux zeigt keine erfundenen Ersatzwerte an.

</details>

<details>
<summary><strong>Wo finde ich die Anleitung?</strong></summary>

Öffne den Bereich **Info** und klicke auf **„Anleitung öffnen“**. Dort findest du neun bebilderte Erklärungsseiten mit Pfeilen und Markierungen. Du kannst die Anleitung sowohl auf Deutsch als auch auf Englisch verwenden.

</details>

<details>
<summary><strong>Wie deinstalliere ich Vitalux?</strong></summary>

Wenn Vitalux über das AppImage ins Anwendungsmenü integriert wurde, kannst du die installierte AppImage-Datei mit der Option `--uninstall` starten. Zum Beispiel im Terminal:

```bash
~/.local/opt/vitalux/Vitalux.AppImage --uninstall
```

Dabei werden die installierte Anwendung und ihre Menüintegration entfernt. Deine persönlichen Einstellungen bleiben erhalten. Falls du Vitalux lediglich ohne Installation gestartet hast, kannst du einfach die heruntergeladene Datei entfernen.

</details>

<details>
<summary><strong>Wie überprüfe ich den Download?</strong></summary>

Lade zusammen mit dem AppImage die Datei `Vitalux-vX.Y.Z-SHA256SUMS.txt` aus demselben Release herunter. Befinden sich die Dateien im gleichen Ordner, kannst du im Terminal mit `sha256sum -c Vitalux-vX.Y.Z-SHA256SUMS.txt` die Prüfsummen kontrollieren. Ersetze dabei `X.Y.Z` durch die tatsächliche Versionsnummer.

</details>

## Feedback und Fehler melden

Du hast einen Fehler entdeckt oder eine Idee für Vitalux? Über **[GitHub Issues](https://github.com/PAAAUUULLOOOH/Vitalux/issues)** kannst du Rückmeldungen und Verbesserungsvorschläge einreichen.

Hilfreich sind die verwendete Vitalux-Version, deine Linux-Distribution, die Desktopumgebung und eine kurze Beschreibung des Problems. Teile bitte keine Passwörter, Zugangsdaten oder andere private Informationen.

## Lizenzen

Vitalux verwendet unter anderem Python, Qt/PySide6, psutil und fio. Lizenzinformationen zu gebündelten Drittkomponenten befinden sich im jeweiligen Downloadpaket im Ordner `licenses/`.

Für den Vitalux-Projektcode ist derzeit keine eigene allgemeine Lizenzdatei hinterlegt. Die öffentliche Sichtbarkeit des Quellcodes bedeutet daher nicht automatisch, dass der Code beliebig weiterverwendet oder weiterverteilt werden darf.

---

<p align="center">
  <strong>Vitalux · Dein Linux-System im Blick.</strong>
</p>

<p align="center">
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/releases/latest">Download</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/PAAAUUULLOOOH/Vitalux/issues">Feedback & Fehler melden</a>
</p>
