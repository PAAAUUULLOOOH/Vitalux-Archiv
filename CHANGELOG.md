# Vitalux – Changelog

Änderungen werden hier für jede neue Version dokumentiert. Im Reiter **Updates**
siehst du die Neuerungen schon vor dem Aktualisieren und danach weiterhin den
Verlauf der installierten Versionen. Die jeweils aktuelle Version wird beim
Veröffentlichen automatisch als GitHub-Release-Beschreibung übernommen.

## [v0.9.3.78] - 2026-10-18
- **GPU-Tuning direkt im Grafik-Reiter:** Native, farbschemaabhängige Vitalux-Bedienoberfläche auf Basis des originalen lokalen **LACT-Hintergrunddienstes (lactd)** – die bisherigen Live-Sensordaten bleiben erhalten.
- GPU wählen und unterstützte Takt-, Spannungs-, Leistungs- und Lüfterparameter bearbeiten. Erweiterte LACT-Konfigurationsfelder bleiben erhalten und sind zusätzlich über den JSON-Expertenbereich zugänglich. Änderungen benötigen eine ausdrückliche Bestätigung; unbestätigte Werte rollt LACT automatisch zurück.
- Profile erstellen, aktivieren und löschen; automatische Umschaltung und Prozess-/GameMode-Regeln werden über die LACT-Schnittstelle verwaltet. Ohne installierten und freigegebenen lactd-Dienst bleibt Vitalux als Systemmonitor nutzbar.
- README, integrierte DE/EN-Anleitung, Übersetzungen, Lizenzhinweise und isolierte LACT-/Qt-Regressionstests ergänzt. Unterstützte Regler hängen von GPU, Treiber und LACT ab; GPU-Tuning ist nicht ohne weitere Hardwaretests garantiert.

## [v0.9.3.77] - 2026-10-18
- Im Info-Reiter steht wieder die vollständige Danksagung mit fettgedrucktem „Danke an:“ und anklickbarem GitHub-Profillink auf TimBooH. Die Danksagung folgt DE/EN und der Akzentfarbe.
- Automatisches Dashboard-Tiling: Nur größere Leerflächen nach dem Verschieben oder Ausblenden von Kacheln werden vorsichtig ausgefüllt. Der bisherige Abstand von 14 px zwischen Kacheln bleibt gleich. Keine Änderung gespeicherter Reihenfolgen, Undo oder Drag-and-drop-Bedienung.
- Betroffenen Code gestrafft, kompakte README und integrierte zweisprachige Anleitung aktualisiert; Regressionstests ergänzt.

## [v0.9.3.76] - 2026-10-18
- Flüssigeres Mausrad-Scrollen mit zeitbasierter Bewegung und dynamischer Anpassung an die aktuell eingestellte Bildwiederholrate des verwendeten Monitors (auch nach Monitorwechsel oder Hz-Änderung). Touchpads scrollen weiterhin ohne künstliche Verzögerung.
- Schonende Aktualisierung nur während aktiver Scrollbewegungen; reduzierte Animationen und ausgeschaltete Bewegungseffekte werden respektiert. Keine Änderung der KDE-Monitoreinstellung oder FPS-Garantie.
- Die Danksagung für TimBooH im Info-Reiter ist kürzer, größer und verwendet dieselbe Akzentfarbe wie „Made by PAAAUUULLOOOH“.
- README und Scroll-Regressionstests aktualisiert.

## [v0.9.3.75] - 2026-10-18
- Neuer **Qt Quick · GPU-Test (experimentell)** als dritte Option direkt unter **Einstellungen → Grafik-Rendering**, neben CPU und OpenGL. Wechsel erfolgt wie gehabt über **Jetzt neu starten**.
- Qt Quick nutzt den GPU-Scene-Graph mit Qt RHI/OpenGL für die Hintergrundtextur, während vorhandene CPU-gerenderte Qt-Widgets, Charts und Glas-Karten erhalten bleiben. Eine Beschleunigung der gesamten Oberfläche wird nicht versprochen.
- Benötigte Qt-Quick-/QML-Bindings und Module werden für die portable ZIP und AppImage gebündelt. Bei fehlenden Grafikkomponenten fällt Vitalux auf CPU zurück. Die bisherigen CPU-/OpenGL-Modi und der GPU-Startschutz bleiben unverändert.
- Unter **Info**, direkt unter „Made by PAAAUUULLOOOH“ und in kleinerer Schrift ergänzt: „Danke an TimBooH für die Unterstützung bei der Integration eigener Hintergrundbilder und der Grafikausgabe (OpenGL/CPU-Rendering).“
- README, deutsche/englische Anleitung und Rendering-Tests aktualisiert.

## [v0.9.3.74] - 2026-10-18
- Scrollende Karten verwenden keine aufwendigen Qt-Offsetschatten mehr, um wiederholtes Rendern großer Zwischenflächen zu vermeiden. Glasmaterial und Umrandungen bleiben erhalten; unabhängig von der Wahl CPU/OpenGL.
- Eigene Hintergrundbilder werden beim Dekodieren passend zur Zielgröße verkleinert und wiederverwendet. Das verringert CPU- und Speicheraufwand besonders bei großen Fotos und häufiger Größenänderung; Ausrichtungen Füllen, Einpassen, Strecken, Zentrieren und Kacheln bleiben verfügbar.
- Unter **Akzentfarbe** stehen weiterhin alle festen und selbst angelegten Farben. Ein einziger zusätzlicher Dropdown-Eintrag **Hintergrundfarbe automatisch** ersetzt beide Akzent-Reiter sowie die nummerierten Farboptionen. Alte nummerierte Auswahlwerte werden automatisch auf diesen Modus umgestellt.
- Layout der Akzent- und Hintergrundbildaktionen für schmalere Fenster und KDE-Skalierung angepasst.
- Beim Wechsel von CPU zu OpenGL oder umgekehrt erscheint **Jetzt neu starten**. Vitalux stoppt seine Threads kontrolliert und startet über den bestehenden Launcher neu, ohne im Tray als alte Instanz weiterzulaufen. Bei laufendem Benchmark wird der Neustart abgelehnt.
- Automatische Tests sowie deutsche/englische Anleitung aktualisiert. Die vorigen Releases bleiben für einen Rückschritt verfügbar.

## [v0.9.3.73] - 2026-10-17
- Experimentelle, **optionale OpenGL/GPU-Darstellung** für den nativen Hintergrund und die finale Qt-Fensterkomposition eingeführt. Klassische Qt-Widgets, Sensoren und Diagramme bleiben zunächst CPU-gerendert; eine Leistungssteigerung ist nicht garantiert.
- Unter **Einstellungen → Grafik-Rendering** kann zwischen „CPU · Standard (stabil)“ und „OpenGL · GPU-Test (experimentell)“ gewechselt werden. Die Änderung greift aus technischen Gründen erst nach einem Neustart und erhält alle übrigen Einstellungen.
- Vor dem OpenGL-Start prüft Vitalux, ob ein GL-Kontext erzeugt werden kann. Bei fehlendem OpenGL bleibt die CPU-Darstellung aktiv. Ein Absturz während der GPU-Startphase führt beim nächsten Programmstart automatisch zum CPU-Modus; mit `VITALUX_RENDERER=software` lässt sich dieser jederzeit erzwingen.
- Der GPU-Test kann separat mit identischem Hintergrund und gleichen Messintervallen verglichen werden; frühere Releases werden nicht überschrieben. Zweisprachige Anleitung, README und Regressionstests aktualisiert.

## [v0.9.3.72] - 2026-10-17
- Einstellungen → Farbakzente erhält zwei Reiter: „Manuelle Farbakzente“ (alle bisherigen Farben und Bearbeiten/Löschen unverändert) und „Passend zum Hintergrund“ mit fünf aus dem angezeigten Hintergrund ermittelten Farben.
- Neuer Modus „Automatisch anpassen“: Beim Wechsel eines integrierten Hintergrunds oder eines eigenen Bildes wird die Akzentfarbe neu ermittelt und auf Bedienelemente, Diagramme, Fenster- und Tray-Darstellung angewendet. Manuell ausgewählte Bildfarben folgen ebenfalls dem jeweils aktiven Hintergrund.
- Farben werden lokal, einmalig und verkleinert aus den Hintergrund-Pixeln bestimmt; die Auswahl bleibt stabil und vermeidet Rückkopplungen mit „Adaptiv · Akzentfarbe“. Keine zusätzlichen Python-Abhängigkeiten.
- Farb-Reiter und Vorschau berücksichtigen Dark, Light, Glass, Black Glass und Minimalistisch. README und zweisprachige Anleitung aktualisiert. Die 630 Kombinationen fester Standardoptionen bleiben erhalten.

## [v0.9.3.71] - 2026-10-17
- Systemleisten-Hover repariert: KDE zeigt wieder CPU-, GPU- und RAM-Auslastung sowie verfügbare CPU-/GPU-Temperaturen aus den laufenden Messdaten an.
- Kompakte Live-Vorschau im Tray-Kontextmenü ergänzt, mit aktualisierten Prozentbalken und Temperaturen. Unter Wayland wird der native KDE-Tooltip für den Hover verwendet.
- Eigene PNG-, JPG-, WebP- und BMP-Hintergründe importieren, auswählen und löschen. Die Originaldateien bleiben unverändert.
- Bildplatzierung: Bildschirmfüllend, Einpassen, Strecken, Zentriert oder Kacheln, mit Vorschau.
- Deutsch/Englisch, Anleitung und Tests erweitert. Die 630 integrierten Farbkombinationen bleiben erhalten.

## [v0.9.3.70] - 2026-10-17
- Protokolle vereinheitlicht: `vitalux.log`, `errors.log`, `installation.log` und `restart.log` erhalten lokale ISO-Zeitstempel einschließlich Zeitzone und Kennzeichnungen der Vitalux-Version. Native Crashframes werden mit einem zeitgestempelten Startmarker und Absturzabschluss eingerahmt.
- Alte animierte Hintergrundeffekte „Nordlicht“, „Nachtwellen“ und „Violetter Nebel“ sowie deren Farbpaletten und Renderlogik vollständig entfernt. Nur „Funkeln“ bleibt animiert.
- Statische Hintergründe „Perlmutt“ und „Eisblau“ samt Farbpaletten entfernt. Frühere Einstellungen dieser Designs fallen auf den Standardhintergrund des aktiven Farbschemas zurück.
- README und integrierte deutsch/englische Anleitung aktualisiert und verfügbare Kombinationen dokumentiert: 5 Farbschemas × 14 Hintergrundauswahlen × 9 Akzentoptionen = **630 Auswahlkombinationen**, davon 560 mit festen Akzentfarben; zusätzliche eigene Farben möglich.
- Regressionstests für Hintergrundauswahl, Logzeitstempel, Versionen und Wiederherstellung aktualisiert.

## [v0.9.3.69] - 2026-10-17
- Absturzdiagnose verbessert: `vitalux.log` versieht ab jetzt jede Programm-, Python- und Qt-Konsolenmeldung mit lokalem ISO-8601-Zeitstempel samt Zeitzone. Auch Programmstart (einschließlich Version) und Exit-Code werden protokolliert; der wirkliche Prozess-Exit-Code bleibt trotz Log-Pipeline erhalten.
- `errors.log` markiert jeden Programmstart vor Aktivierung des nativen Python-Absturzhandlers mit Zeitstempel und Vitalux-Version. So lassen sich ältere Fehler klar von neuen Abstürzen unterscheiden.
- Automatische Regressionstests für zeitgestempelte `malloc()`-Fehlermeldungen, Fehlercode 134, Wiederherstellungsstatus und `errors.log` ergänzt.
- Der vom Nutzer hochgeladene `NameError: json is not defined` stammt aus der alten Version 0.9.3.23. Die aktuelle Version enthält den erforderlichen Import bereits; für den nativen Speicherabsturz liegt weiterhin keine eindeutige Ursache vor.

## [v0.9.3.68] - 2026-10-17
- Hintergrund „Regenbogen Pastell“ sowie die animierten Hintergründe „Regenbogen“, „Fade Bunt“ und „Hell“ inklusive nicht mehr verwendeter Farbpaletten und Animationseffekte aus dem Programm entfernt.
- Der animierte Hintergrund „Funkeln“ bleibt unverändert erhalten.
- Drei neue, bewusst weniger grelle, automatisch animierte Hintergründe ergänzt: „Nordlicht“ (Petrol/Türkis/Violett), „Nachtwellen“ (Tiefblau/gedämpftes Petrol) und „Violetter Nebel“ (Blauviolett). Die Helligkeit orientiert sich am Standard-Glass-Hintergrund.
- Auswahl und Übersetzungen bereinigt; bisher gespeicherte, entfernte Hintergrundauswahlen fallen auf den Standardhintergrund des aktiven Farbschemas zurück.
- Tests für erlaubte Hintergrundauswahl, automatische Animationen, dunkle Farbwerte und Regressionen angepasst. README und integrierte Anleitung aktualisiert.

## [v0.9.3.67] - 2026-10-17
- Die globale Option „Hintergrund sanft animieren“ samt gespeicherter Einstellung und Zeichenlogik entfernt. Statische Designs bleiben nun stets statisch.
- Vier eigens animierte Hintergründe ergänzt: Regenbogen, Fade Bunt, Funkeln und Hell. Sie animieren direkt bei Auswahl; hellere Farbtöne bleiben unabhängig vom Farbschema erhalten. Adaptiv · Akzentfarbe ist wieder verfügbar.
- Regler für Farbintensität und Hintergrundweichheit mitsamt ihrer GUI, Berechnung, Speicherung und dem separaten Slider-Modul entfernt. Jedes Wallpaper verwendet fest abgestimmte Farben und Weichheit.
- Seitenleiste wieder dauerhaft links angeordnet. Freies Andocken rechts, Ziehgriff und spiegelnde Bedienelemente sowie nicht mehr benötigte Dateien entfernt.
- Zu den Standard-Akzentfarben Gelb und Rot passende Vitalux-Symbole und Wortmarken hinzugefügt. Farbwechsel von Fenster- und Tray-Symbol sowie benutzerinstalliertem KDE-Menü-Symbol verbessert.
- Update-Symbol erhält ein kräftiger sichtbares pulsierendes Leuchten im Tray. Pop-up-Schaltflächen (Ja/Nein usw.) richten sich unabhängig von Qt-Systemübersetzungen nach der gewählten Vitalux-Sprache.
- README, integrierte Anleitung und deutsch/englische Änderungshistorie aktualisiert; automatisierte Tests angepasst.

## [v0.9.3.66] - 2026-10-17
- Die Seitenleiste lässt sich über einen eigenen Punkte-Griff links oder rechts andocken. Anklicken wechselt die Seite, Ziehen und Loslassen positioniert sie nach Fensterhälfte. Die Position wird gespeichert; Ein-/Ausklapppfeil, Trennkante und Dashboard-Layoutpfeil passen sich automatisch an.
- Bei „Layout bearbeiten“ wird die Hervorhebung des Pfeils beim Schließen vollständig zurückgesetzt. Die seitliche Bearbeitungsleiste öffnet in der passenden Richtung.
- Die Glas-Seitenleiste und die Kacheln erhielten harmonisierte Helligkeit und Transparenz, während die gewohnte Originaloptik erhalten bleibt.
- Hintergrundanimationen mit stärker wahrnehmbaren, auf das jeweilige Farbschema abgestimmten Lichtverläufen versehen. Auch Minimalistisch unterstützt bei ausdrücklicher Aktivierung einen ressourcenschonenden monochromen Lichtschein; standardmäßig bleibt die Animation ausgeschaltet.
- Neue Standardwerte: Glass, Vitalux Blau und dazugehöriger Glass-Hintergrund. Vorhandene Einstellungen bleiben erhalten.
- Die sechs vordefinierten Akzentfarben wechseln nun das Vitalux-App-, Fenster- und Tray-Symbol. Eine vorhandene Benutzerinstallation aktualisiert auch ihre Menü-Icondatei; das glühende Updatesymbol übernimmt dieselbe Farbe.
- README, integrierte Anleitung und deutsch/englische Änderungsübersichten aktualisiert. Ergänzende grafische Regressionstests hinzugefügt.

## [v0.9.3.65] - 2026-10-17
- Das Vitalux-Symbol im KDE-Systemtray glüht und pulsiert nun bei einem verfügbaren Update. Nach dem Aktualisieren erscheint automatisch wieder das normale Symbol. Das Vitalux-Logo in der App erhält einen besser sichtbaren, farblich abgestimmten Leuchtring; Updates-Reiter und einmalige Tray-Meldung bleiben erhalten.
- Die ursprüngliche frosted Seitenleiste mit Glasmaterial und beleuchteter Trennkante wurde wiederhergestellt. Für abweichende Hintergrundpaletten passt sich ihre Transparenz behutsam an; das originale Erscheinungsbild der Farbschemas bleibt erhalten.
- Die bisherigen Zusatzhintergründe entfernt und durch neun abgestimmte Varianten ersetzt: Hell (Perlmutt, Morgenlicht, Eisblau), Regenbogen (Pastell, Prisma) und Dunkel (Tiefsee, Mitternacht, Samt, Graphit). Die fünf ursprünglichen Farbschema-Hintergründe bleiben bestehen.
- Die neuen Hintergründe übernehmen einen dezenten Anteil der Akzentfarbe und unterstützen Farbintensität, Hintergrundweichheit und optionale sanfte Animationen. Frühere nicht mehr vorhandene Hintergrundauswahlen fallen auf den Standard des Farbschemas zurück.
- Die kompakte GitHub-README und die integrierte deutsch/englische Anleitung aktualisiert. Regressionstests für Presets und animierte Tray-Symbole ergänzt.

## [v0.9.3.64] - 2026-10-17
- Hintergrund, Seitenleiste und Glas-Kacheln verwenden dieselbe fertig abgestimmte Darstellung. Die dunkle zusätzliche Seitenleisten-Überlagerung entfällt; insbesondere Light bleibt einheitlich.
- Farbharmonien und optionale gleitende Hintergrundanimationen für Aurora Glass, Nebula Purple, Obsidian Black, Arctic Frost und Adaptiv überarbeitet.
- Farbintensität ist nun auch bei allen Standardhintergründen wirksam (Dark, Light, Glass, Black Glass und Minimalistisch). Minimalistisch bleibt dabei einfarbig.
- Farbintensitäts- und Hintergrundweichheitsregler vollständig als elegante Qt-Controls mit sichtbaren Akzentverläufen und eigenen Griffen umgesetzt.
- Beim Öffnen von „Laufwerke“ startet die SMART-Prüfung wieder automatisch, während die Laufwerksauswahl sofort sichtbar ist. Erneutes Prüfen bleibt möglich.
- Regressionstests sowie README und integrierte Anleitung entsprechend aktualisiert.

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
