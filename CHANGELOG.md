# Vitalux – Changelog

Änderungen werden hier für jede neue Version dokumentiert. Im Reiter **Updates**
siehst du die Neuerungen schon vor dem Aktualisieren und danach weiterhin den
Verlauf der installierten Versionen. Die jeweils aktuelle Version wird beim
Veröffentlichen automatisch als GitHub-Release-Beschreibung übernommen.

## [v0.9.3.63] - 2026-10-17
- Originale Hintergrund-Designs wiederhergestellt und einzeln nach ihrem Farbschema benannt: Dark, Light, Glass, Black Glass und Minimalistisch. Mit „Automatisch (Farbschema)“ wird der passende Standardhintergrund gewählt.
- Die Seitenleiste bei zusätzlichen Hintergrunddesigns farblich harmonisiert; die vertraute Glasoptik der Originaldesigns bleibt unverändert. Zusätzliche Farbverläufe und zurückhaltende Satinstrukturen verbessern Aurora Glass, Obsidian Black, Nebula Purple und Arctic Frost.
- Hintergrund-Slider eleganter gestaltet: feine Akzentfarbverläufe, dezente Griffe, einheitliche Prozentanzeigen und besser sichtbare Hover-Zustände.
- Neue Updates werden durch ein dezentes Pulsieren des Updates-Reiters und des Vitalux-Logos angezeigt. Im Reiter steht die neue Versionsnummer direkt sichtbar. Eine einmalige Benachrichtigung je Version erscheint im Tray; das Tray-Menü öffnet den Updates-Reiter.
- Automatische Updateprüfung beim Programmstart und regelmäßig etwa alle sechs Stunden beibehalten. Keine ungefragte Installation.
- README, deutsche/englische Übersetzungen, integrierte Anleitung und Regressionstests aktualisiert.

## [v0.9.3.62] - 2026-10-17
- Systemweite Hover-Textfenster innerhalb der Anwendung abgeschaltet; farbliche Hover-Effekte bleiben erhalten, auch in der Seitenleiste.
- Native Hintergrundstile Aurora Glass, Obsidian Black, Nebula Purple, Arctic Frost, Adaptiv und Klassisch hinzugefügt. Farbschema und Hintergrund lassen sich unabhängig auswählen; minimalistische Darstellung bleibt einfarbig.
- Hintergrund-Farbintensität, Weichheit und optional sanfte Animationen ergänzt. Adaptiv reagiert auf die gewählte Akzentfarbe; die Animation ist standardmäßig ausgeschaltet.
- Die Grafiken werden direkt durch Qt gerendert und als Glas-Hintergrund zwischengespeichert, ohne zusätzliche Downloads oder Browser.
- Einstellungsoberfläche, englische Übersetzungen, integrierte Anleitung und die kompakt überarbeitete GitHub-README aktualisiert.
- Zusätzliche grafische Regressionstests für Hintergründe, Farbwechsel, Minimal-Modus und Tooltip-Unterdrückung.

## [v0.9.3.61] - 2026-10-17
- Hardware-Warnwerte linksbündig ausgerichtet; Zahlen und Einheiten bleiben sichtbar, Mausrad verändert Werte nur bei fokussierter Eingabe.
- Dropdowns behalten die dunkle rechte Fläche ohne Pfeil, passen ihre geöffneten Listen an lange Texte an und zeigen vollständige Einträge bei Bedarf als Tooltip.
- Kleinere Fenster auf hochskalierten KDE-Desktops zugelassen; versteckte Seiten werden nicht mehr unnötig neu gezeichnet.
- SMART-Daten werden entsprechend der Beschriftung nur noch per Schaltfläche angefordert.
- Bei mehreren Grafikkarten wird für GPU-Temperaturwarnungen die höchste verfügbare Temperatur berücksichtigt; ungültige Sensordaten lösen keine Warnungen aus.
- Einstellungen werden zwischengespeichert und atomar geschrieben; Speicherfehler werden gemeldet.
- GitHub-Workflow und Update-Pakete verbessert: Tests laufen auch bei bereits vorhandenem Release, Differenzupdates basieren auf der unmittelbaren Vorgängerversion.
- Zusätzliche Regressionstests für Warnwerte, Einstellungen, GPU-Warnungen und Dropdowns.

## [v0.9.3.60] - 2026-10-17
- Hardware-Warnwerte vollständig korrigiert: Statt des unter KDE/Wayland abgeschnittenen QSpinBox-Innenfelds werden Zahl und Einheit jetzt getrennt und zuverlässig lesbar dargestellt.
- Werte bleiben direkt editierbar; Pfeiltasten, Mausrad, Grenzbereiche und Speichern der Einstellungen funktionieren weiterhin.
- Einheitliche Ausrichtung und kompakte Feldbreite beibehalten; automatisierte Tests um Werteingabe und Sichtbarkeit ergänzt.

## [v0.9.3.59] - 2026-10-17
- Die zuletzt problematischen Dropdown-Änderungen zurückgenommen und die frühere Darstellung mit dunklem rechten Auswahlbereich wiederhergestellt.
- Dropdown-Text und vollständige Versionsnummern im Changelog wieder lesbar.
- Hardware-Warnwerte zeigen wieder die Zahlen einschließlich Einheiten; Warnwert-Felder bleiben einheitlich ausgerichtet.
- Die grafischen Tests an die wiederhergestellten Bedienelemente angepasst.

## [v0.9.3.58] - 2026-10-17
- Warnwert-Felder stehen jetzt in einer festen, gemeinsamen Spalte statt textabhängig zu wandern; „Systemlaufwerk“ als kürzere Beschriftung.
- Schmalere Warnwert-Felder ohne Auf-/Ab-Pfeile; Eingabe per Tastatur, Pfeiltasten und Mausrad weiterhin möglich.
- Alle Dropdowns ohne Pfeile oder Pfeilbereich; kompaktere Breite auch bei langen Einträgen.
- Geschlossene Dropdowns werden unabhängig vom KDE-/Qt-Systemstil vollständig im aktiven Vitalux-Farbschema gezeichnet.
- Aufgeklappte Dropdown-Listen, ihre Ränder und Scrollbereiche erhalten explizit die jeweils passende Hintergrund- und Textfarbe.
- Tests und README aktualisiert.

## [v0.9.3.57] - 2026-10-17
- Schmalere Dropdown-Menüs mit eigener, farblich an das Schema angepasster Pfeilmarkierung.
- Aufgeklappte Listen in allen fünf Farbschemata mit passendem Hintergrund; keine schwarzen Qt-Menüleisten oben und unten.
- Warnwerte für CPU, GPU, RAM und Systemlaufwerk stehen einheitlich unmittelbar neben dem zugehörigen Text.
- Schaltflächen für eigene Akzentfarben neu angeordnet: „Bearbeiten“, „Löschen“, „Eigene Farbe …“.
- Einstellungen-Tests und README angepasst.

## [v0.9.3.56] - 2026-10-17
- Gespeicherte eigene Akzentfarben können über einen neuen Button „Bearbeiten“ in Name und Farbwert geändert werden, ohne einen zusätzlichen Eintrag anzulegen.
- Für eigene Farben erscheint ein separater Button „Löschen“; beide Aktionen sind nur bei einer ausgewählten eigenen Farbe sichtbar.
- Alle Dropdown-Menüs an Dark, Light, Glass, Black Glass und Minimalistisch angepasst, einschließlich SMART-Laufwerksauswahl; die Auswahlfelder wurden nur geringfügig schmaler gemacht.
- Temperatur- und Auslastungswarnwerte stehen wieder rechts hinter den Beschriftungen, weiterhin mit schmalen, zentrierten Zahlenfeldern.
- Im Update-Changelog wird immer nur die gerade ausgewählte Sprache angezeigt: Deutsch oder Englisch.
- Integrierte Anleitung und GitHub-README zu den neuen Bedienelementen aktualisiert.

## [v0.9.3.55] - 2026-10-17
- Dropdown-Menüs mit durchgängig gestalteten Hintergründen überarbeitet; störende schwarze Leisten oben und unten beseitigt.
- Schmale, mittig ausgerichtete Temperatur- und Auslastungswarnwerte links vor ihre Beschriftungen verschoben, ohne die Kachelgröße zu verändern.
- Vollständige englische Changelogs für installierte und kommende Updates ergänzt; der Sprachwechsel aktualisiert beide Anzeigen.
- Integrierte Anleitung und README zu Warnwerten, Farbauswahl, Dropdowns und Changelog gezielt aktualisiert.

## [v0.9.3.54] - 2026-10-17
- Einheitliche Checkboxen mit sichtbar gezeichnetem Häkchen in Diagrammen, Einstellungen und Benchmarks.
- Schmalere Warnwert-Felder mit mittig ausgerichteten Zahlen; die Größe der umgebenden Kacheln bleibt unverändert.
- Eigene Akzentfarben beim Erstellen benennen, dauerhaft speichern und über das X neben der Farbauswahl wieder löschen.
- Changelog direkt in Vitalux: Neuerungen vor dem Update und Versionsverlauf nach dem Update ansehen.
- GitHub-Veröffentlichungen übernehmen ihre Änderungsbeschreibung ab jetzt automatisch aus diesem Changelog.

## [v0.9.3.53] - 2026-10-17
- Automatische Wiederherstellung einer vorherigen AppImage-Version beim ersten Neustart nach einem Update zusätzlich abgesichert.
- Wiederherstellung auch für Neustarts aus älteren Vitalux-Versionen geprüft.

## [v0.9.3.52] - 2026-10-17
- Problematische Mauszugriffe des Layout-Editors unter Wayland entfernt und Diagnose von Abstürzen verbessert.
- Neu gestaltete SVG-Logos in den sechs vordefinierten Akzentfarben; bei Distributions- und eigenen Farben bleibt das Originallogo.
- Wiederherstellungsmechanismus für die unmittelbar vorherige Version sowie Tests für AppImage und ZIP ergänzt.

## [v0.9.3.51] - 2026-10-17
- Distributionslogo im Layout-Editor mit einem X einzeln ausblendbar und über „Kacheln hinzufügen“ wiederherstellbar.
- Layout-Aktionen wie Speichern, Verwerfen und Rückgängig für die Logo-Sichtbarkeit ergänzt.
- Erste dynamische Farbanpassung des Vitalux-Schriftzugs und -Logos eingeführt, in späteren Versionen durch eigene SVG-Farbvarianten ersetzt.
