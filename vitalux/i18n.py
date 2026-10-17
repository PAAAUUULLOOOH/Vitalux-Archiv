"""Übersetzung. Die deutschen Texte sind zugleich die Schlüssel; Englisch wird per Tabelle nachgeschlagen."""

_lang = "de"


def set_lang(code):
    global _lang
    _lang = code if code in ("de", "en") else "de"


def lang():
    return _lang


def tr(text):
    if _lang != "en" or not text or not isinstance(text, str):
        return text
    result = EN.get(text)
    if result is not None:
        return result
    result = EN_MORE.get(text)
    if result is not None:
        return result
    # Card headers are rendered uppercase. Translate their original keys
    # without changing layout or rebuilding the page.
    if text.isupper():
        for source in (EN, EN_MORE):
            for german, english in source.items():
                if german.upper() == text:
                    return english.upper()
    # Dynamic benchmark phases contain a test name, pass number and/or delay.
    # Keep the numeric values intact while translating the visible keywords.
    import re
    result = re.sub(r"\bDurchlauf\b", "Pass", text)
    result = re.sub(r"\bBereite Testdatei vor\b", "Preparing test file", result)
    result = re.sub(r"\bIntervall\b", "Interval", result)
    result = re.sub(r"\bMessbericht in die Zwischenablage kopiert\b", "Report copied to clipboard", result)
    result = re.sub(r"\bBericht gespeichert\b", "Report saved", result)
    result = re.sub(r"\bBericht konnte nicht gespeichert werden\b", "Could not save report", result)
    result = re.sub(r"\bExport fehlgeschlagen\b", "Export failed", result)
    result = re.sub(r"\bkeine IP\b", "no IP address", result)
    result = re.sub(r"\bU/min\b", "RPM", result)
    result = re.sub(r"\bKeine GPU erkannt\b", "No GPU detected", result)
    result = re.sub(r"\bMbit/s\b", "Mbit/s", result)
    return result


EN = {
    # Navigation / Seiten
    "Übersicht": "Overview", "Prozessor": "Processor", "Grafik": "Graphics",
    "Arbeitsspeicher": "Memory", "Laufwerke": "Drives", "System": "System", "Netzwerk-Verlauf": "Network history",
    "Updates": "Updates", "Info": "About", "Sensoren": "Sensors", "Einstellungen": "Settings",
    "Live-Status deines Systems": "Live status of your system",
    "Systemauslastung": "System load",
    "System-Laufwerk": "System drive", "Auslastung": "Utilization",
    "Arbeitsspeicher-Verlauf": "Memory history", "Netzwerk": "Network", "Netzwerk-Verlauf": "Network history",
    "Aktive Schnittstelle": "Active interface", "Daten gesamt": "Total data",
    "Link-Geschwindigkeit": "Link speed", "Netzwerkschnittstellen": "Network interfaces",
    "Aktuelle Übertragungsraten": "Current transfer rates", "Download": "Download", "Upload": "Upload",
    "Keine GPU-Daten verfügbar": "No GPU data available", "Laufzeit": "Uptime",
    "Auslastung, Takt und Temperatur": "Load, clock speed and temperature",
    "Kerne / Threads": "Cores / threads", "Kerne": "cores", "Takt": "Clock speed",
    "Temperatur": "Temperature", "Last (1 / 5 / 15 Min)": "Load average (1 / 5 / 15 min)",
    "Gesamtauslastung": "Total load", "Verlauf": "History",
    "GPU-Auslastung, Videospeicher und Sensoren": "GPU load, video memory and sensors",
    "Videospeicher": "Video memory", "Leistung": "Power", "Lüfter": "Fan",
    "GPU-Takt": "GPU clock", "Speicher-Takt": "Memory clock",
    "nicht verfügbar": "not available", "Treiber": "Driver",
    "Keine GPU-Daten gefunden. Unterstützt werden NVIDIA (nvidia-smi), AMD (amdgpu) und Intel (Name, ohne Auslastung).":
        "No GPU data found. Supported: NVIDIA (nvidia-smi), AMD (amdgpu) and Intel (name only, no load).",
    "RAM und Swap": "RAM and swap", "Gesamt": "Total", "In Benutzung": "In use",
    "Verfügbar": "Available", "Puffer": "Buffers", "nicht aktiv": "not active",
    "Datenträger, Belegung und Durchsatz": "Drives, usage and throughput",
    "Physische Datenträger": "Physical drives", "Partitionen": "Partitions",
    "Durchsatz": "Throughput", "Lesen": "Read", "Schreiben": "Write",
    "Betriebssystem, Hardware und Software": "Operating system, hardware and software",
    "Betriebssystem": "Operating system", "Distribution": "Distribution", "Distributionsversion": "Distribution version", "KDE Plasma": "KDE Plasma", "KDE Frameworks": "KDE Frameworks", "Desktop": "Desktop", "Cache": "Cache",
    "Architektur": "Architecture", "Rechnername": "Hostname", "Benutzer": "User",
    "Sitzung": "Session", "Hersteller": "Manufacturer", "Modell": "Model",
    "Details": "Details",
    "T": "d", "Std": "h", "Min": "min",
    # Updates
    "Neue Versionen holen und installieren": "Get and install new versions",
    "Version": "Version", "Aktuelle Version": "Current version", "Neueste Version": "Latest version",
    "Nach Updates suchen": "Check for updates", "Update installieren": "Install update",
    "Was ist neu": "What's new", "Update-Quelle (GitHub)": "Update source (GitHub)",
    "Speichern": "Save",
    "Trage hier dein GitHub-Repository ein, z. B. dein-name/vitalux. Es muss öffentlich sein.":
        "Enter your GitHub repository here, e.g. your-name/vitalux. It must be public.",
    "So veröffentlichst du ein Update": "How to publish an update",
    "Führe im Projektordner ./release.sh 0.4 \"Änderungen\" aus. Das erzeugt ein ZIP. "
    "Lade es auf GitHub unter Releases > Create a new release hoch (Tag z. B. v0.4) und klicke Publish. "
    "Die App erkennt das Update danach automatisch und der Reiter leuchtet.":
        "Run ./release.sh 0.4 \"changes\" in the project folder. This creates a ZIP. "
        "Upload it on GitHub under Releases > Create a new release (tag e.g. v0.4) and click Publish. "
        "The app then detects the update automatically and this tab starts to glow.",
    "Noch keine Update-Quelle eingerichtet. Trage unten dein GitHub-Repository ein (z. B. dein-name/vitalux).":
        "No update source set up yet. Enter your GitHub repository below (e.g. your-name/vitalux).",
    "Suche nach Updates ...": "Checking for updates ...",
    "Du bist auf dem neuesten Stand.": "You are up to date.",
    "Neue Version verfügbar!": "New version available!",
    "Installiere Update ...": "Installing update ...",
    "Update installiert, starte neu ...": "Update installed, restarting ...",
    "Ungültiger Repository-Name. Format: benutzer/repository": "Invalid repository name. Format: user/repository",
    "Kein Release gefunden. Ist das Repository öffentlich und der Name richtig?":
        "No release found. Is the repository public and the name correct?",
    "Keine Verbindung zu GitHub.": "Could not connect to GitHub.",
    "Das Release enthält keine ZIP-Datei.": "The release contains no ZIP file.",
    "Unerwartete Antwort von GitHub.": "Unexpected response from GitHub.",
    "Das Update-Paket hat eine unbekannte Struktur.": "The update package has an unknown structure.",
    "Installation fehlgeschlagen:": "Installation failed:",
    # Info
    "Über diese App": "About this app", "Erkannte Distribution": "Detected distribution",
    "Einstellungsdatei": "Settings file",
}

from .translations_extra import EN_MORE
