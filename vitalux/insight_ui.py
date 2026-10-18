"""Native, theme-aware, read-only Vitalux Insights panel and focus window."""
from __future__ import annotations


from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QPainter, QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLineEdit, QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QFileDialog,
    QComboBox, QFrame,
)
from .ui_locale import QPushButton, QCheckBox, QMessageBox
from .widgets import Card, ChartPanel, label
from . import theme, settings, sensors
from .i18n import tr
from .insight_engine import FIELDS, telemetry, number


METRIC_TITLES = {
    "cpu_usage": ("CPU", "%"), "cpu_temp": ("CPU-Temperatur", "°C"),
    "gpu_usage": ("GPU", "%"), "gpu_temp": ("GPU-Temperatur", "°C"),
    "gpu_clock": ("GPU-Takt", "MHz"), "gpu_power": ("GPU-Leistung", "W"),
    "ram_usage": ("RAM", "%"), "vram_usage": ("VRAM", "%"),
}


def fmt(value, unit, digits=1):
    return f"{value:.{digits}f} {unit}" if number(value) else tr("nicht verfügbar")


class FocusWindow(QWidget):
    """Independent movable Qt window for a second monitor; no sampling thread."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Vitalux · Fokusmodus")
        self.setMinimumSize(430, 290)
        self.resize(660, 380)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(label("LIVE · FOKUSMODUS", "cardTitle"), 1)
        self.ontop = QCheckBox("Immer im Vordergrund")
        self.ontop.toggled.connect(self._on_top)
        header.addWidget(self.ontop)
        layout.addLayout(header)
        grid = QGridLayout()
        grid.setSpacing(12)
        self.entries = []
        for i, key in enumerate(("gpu_usage", "gpu_temp", "cpu_usage", "vram_usage")):
            card = QGroupBox()
            card.setObjectName("insightGroup")
            col = QVBoxLayout(card)
            choose = QComboBox()
            for metric, (title, _unit) in METRIC_TITLES.items():
                choose.addItem(tr(title), metric)
            choose.setCurrentIndex(choose.findData(key))
            reading = QLabel("–")
            reading.setAlignment(Qt.AlignCenter)
            reading.setObjectName("focusReading")
            reading.setStyleSheet(f"color: {theme.accent()}; font-size: 29px; font-weight: 800;")
            col.addWidget(choose)
            col.addWidget(reading, 1)
            grid.addWidget(card, i // 2, i % 2)
            self.entries.append((choose, reading))
        layout.addLayout(grid, 1)
        layout.addWidget(label("Nur vorhandene Sensordaten – keine Übertaktung oder Hardwaresteuerung.",
                               "muted", wrap=True))

    def retranslate(self):
        self.setWindowTitle(tr("Vitalux · Fokusmodus"))
        for choose, reading in self.entries:
            for idx in range(choose.count()):
                key = choose.itemData(idx)
                choose.setItemText(idx, tr(METRIC_TITLES[key][0]))
            reading.setStyleSheet(
                f"color: {theme.accent()}; font-size: 29px; font-weight: 800;")

    def _on_top(self, enabled):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, enabled)
        self.show()

    def update_sample(self, sample):
        values = telemetry(sample)
        for choose, reading in self.entries:
            key = choose.currentData()
            reading.setText(fmt(values.get(key), METRIC_TITLES[key][1]))


class _HardwareNode(QGraphicsRectItem):
    def __init__(self, name, key, x, y, width, height, callback):
        super().__init__(0, 0, width, height)
        self.key = key
        self.callback = callback
        self.setPos(x, y)
        self.setPen(QPen(QColor(theme.BORDER), 1))
        self.setBrush(QBrush(QColor(theme.CARD)))
        self.text = QGraphicsSimpleTextItem(name, self)
        self.text.setBrush(QBrush(QColor(theme.TEXT)))
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.text.setFont(font)
        self.text.setPos(10, 11)
        self.setToolTip(tr("Anklicken, um echte Hardwareinformationen zu sehen"))
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.callback(self.key)
        super().mousePressEvent(event)


class HardwareMap(QGraphicsView):
    """Interactive component diagram; conceptual grouping, not a PCIe wire map."""
    def __init__(self, callback):
        super().__init__()
        self.setMinimumHeight(265)
        self.setMaximumHeight(305)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent;")
        scene = QGraphicsScene(self)
        scene.setSceneRect(QRectF(0, 0, 690, 250))
        self.setScene(scene)
        pen = QPen(QColor(theme.accent()), 2)
        for x1, y1, x2, y2 in (
            (340, 82, 340, 108), (340, 160, 340, 181),
            (280, 135, 233, 58), (400, 135, 456, 58),
            (280, 137, 233, 211), (400, 137, 456, 211),
        ):
            scene.addLine(x1, y1, x2, y2, pen)
        locations = (
            ("mainboard", "MAINBOARD", 269, 108, 142, 54),
            ("cpu", "CPU", 280, 20, 120, 60),
            ("ram", "RAM", 460, 20, 120, 60),
            ("gpu", "GRAFIK", 460, 180, 120, 60),
            ("disk", "LAUFWERKE", 100, 180, 130, 60),
        )
        for key, name, x, y, w, h in locations:
            scene.addItem(_HardwareNode(name, key, x, y, w, h, callback))
        self.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)


class MonitoringLabPanel(Card):
    """Optional analytical tools beneath the existing Grafikkarte information."""
    def __init__(self, lab, open_focus):
        super().__init__("Vitalux Insights · Performance-Analyse")
        self.lab = lab
        self._open_focus = open_focus
        self.last_sample = None
        self._last_events = None
        self._last_findings = None
        self._static = sensors.system_static()

        self.intro = label(
            "Rein lesende Analyse · gemessene Fakten und mögliche Ursachen werden unterschieden.",
            "muted", wrap=True)
        self.body.addWidget(self.intro)
        self.focus = QPushButton("Fokusmodus für zweiten Monitor öffnen")
        self.focus.clicked.connect(self._open_focus)
        self.body.addWidget(self.focus)

        self.detector = QGroupBox("Performance Detective")
        dl = QVBoxLayout(self.detector)
        self.findings = QLabel(tr("Warte auf Messwerte …"))
        self.findings.setWordWrap(True)
        dl.addWidget(self.findings)
        self.body.addWidget(self.detector)

        self.trend_group = QGroupBox("Performance-Verlauf")
        trend_layout = QVBoxLayout(self.trend_group)
        self.trend_chart = ChartPanel(
            ["CPU", "GPU", "VRAM"],
            [theme.accent(), theme.secondary_accent(), theme.TEAL])
        trend_layout.addWidget(self.trend_chart)
        trend_layout.addWidget(label(
            "Gemeinsamer Verlauf der Auslastung. Zeitraum und Datenreihen frei wählbar.",
            "muted", wrap=True))
        self.body.addWidget(self.trend_group)

        self.record_group = QGroupBox("Gaming Session Analyzer")
        rg = QVBoxLayout(self.record_group)
        controls = QHBoxLayout()
        self.session_name = QLineEdit()
        self.session_name.setPlaceholderText("Sitzungsname, z. B. CS2 oder Cyberpunk")
        self.begin = QPushButton("Aufzeichnung starten")
        self.end = QPushButton("Stoppen & auswerten")
        self.begin.clicked.connect(self._begin_session)
        self.end.clicked.connect(self._stop_session)
        controls.addWidget(self.session_name, 1)
        controls.addWidget(self.begin)
        controls.addWidget(self.end)
        rg.addLayout(controls)
        buttons = QHBoxLayout()
        self.import_log = QPushButton("MangoHud-CSV importieren")
        self.import_log.clicked.connect(self._import_mangohud)
        self.save_session = QPushButton("Sitzung als JSON speichern")
        self.save_session.clicked.connect(self._save_session)
        buttons.addWidget(self.import_log)
        buttons.addWidget(self.save_session)
        rg.addLayout(buttons)
        self.session_report = QLabel(tr("Noch keine Gaming-Sitzung abgeschlossen."))
        self.session_report.setWordWrap(True)
        rg.addWidget(self.session_report)
        rg.addWidget(label("FPS und 1%-Lows nur aus importierten MangoHud-Daten; "
                           "1%-Low ist bei Stichproben ein Näherungswert.", "muted", wrap=True))
        self.body.addWidget(self.record_group)

        self.compare_group = QGroupBox("Vorher-Nachher-Vergleich")
        cg = QVBoxLayout(self.compare_group)
        cap = QHBoxLayout()
        self.before = QPushButton("Vorher speichern")
        self.after = QPushButton("Nachher speichern")
        self.before.clicked.connect(lambda: self._take_snapshot(0))
        self.after.clicked.connect(lambda: self._take_snapshot(1))
        cap.addWidget(self.before)
        cap.addWidget(self.after)
        cg.addLayout(cap)
        self.comparison = QLabel(tr("Speichere zuerst Vorher und Nachher."))
        self.comparison.setWordWrap(True)
        cg.addWidget(self.comparison)
        cg.addWidget(label("Einzelne Momentaufnahmen sind kein Benchmark. Für belastbare "
                           "Vergleiche gleiche Testbedingungen verwenden.", "muted", wrap=True))
        self.body.addWidget(self.compare_group)

        self.timeline_group = QGroupBox("Ereignis-Timeline")
        tl = QVBoxLayout(self.timeline_group)
        self.timeline = QListWidget()
        self.timeline.setMaximumHeight(165)
        self.timeline.currentItemChanged.connect(self._select_event)
        tl.addWidget(self.timeline)
        self.event_detail = QLabel("Wähle ein Ereignis, um die damaligen Werte zu sehen.")
        self.event_detail.setWordWrap(True)
        tl.addWidget(self.event_detail)
        self.body.addWidget(self.timeline_group)

        self.hardware_group = QGroupBox("Interaktive Hardware-Übersicht")
        hw = QVBoxLayout(self.hardware_group)
        hw.addWidget(label("Komponenten auswählen · schematische Gruppierung, "
                           "keine Aussage über den tatsächlichen PCIe-Kabelweg.",
                           "muted", wrap=True))
        self.map = HardwareMap(self._select_hardware)
        hw.addWidget(self.map)
        self.hardware_detail = QLabel("Klicke auf eine Komponente.")
        self.hardware_detail.setWordWrap(True)
        hw.addWidget(self.hardware_detail)
        self.body.addWidget(self.hardware_group)

        self.show_advanced = QPushButton("Analysewerkzeuge einklappen")
        self.show_advanced.setCheckable(True)
        self.show_advanced.setChecked(True)
        self.show_advanced.toggled.connect(self._advanced_visible)
        # Keep the primary observation on top; other tools can be collapsed.
        self.body.insertWidget(2, self.show_advanced)
        self._tools = (self.trend_group, self.record_group, self.compare_group,
                       self.timeline_group, self.hardware_group)
        for group in (self.detector, *self._tools):
            group.setObjectName("insightGroup")
        self._advanced_visible(False)
        self.show_advanced.setChecked(False)
        self._update_session()
        self._update_comparison()

    def retranslate(self):
        for group, title in (
            (self.detector, "Performance Detective"),
            (self.trend_group, "Performance-Verlauf"),
            (self.record_group, "Gaming Session Analyzer"),
            (self.compare_group, "Vorher-Nachher-Vergleich"),
            (self.timeline_group, "Ereignis-Timeline"),
            (self.hardware_group, "Interaktive Hardware-Übersicht"),
        ):
            group.setTitle(tr(title))
        names = {"mainboard": "Mainboard", "cpu": "CPU", "ram": "RAM",
                 "gpu": "Grafik", "disk": "Laufwerke"}
        for node in self.map.scene().items():
            if isinstance(node, _HardwareNode):
                node.text.setText(tr(names[node.key]).upper())
        self._advanced_visible(self.show_advanced.isChecked())

    def _advanced_visible(self, shown):
        for widget in getattr(self, "_tools", ()):
            widget.setVisible(shown)
        self.show_advanced.setText(tr("Analysewerkzeuge einklappen") if shown
                                   else tr("Analysewerkzeuge anzeigen"))

    def _begin_session(self):
        try:
            self.lab.start_session(self.session_name.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))
        self._update_session()

    def _stop_session(self):
        try:
            self.lab.stop_session()
        except ValueError as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))
        self._update_session()

    def _import_mangohud(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, tr("MangoHud-Protokoll öffnen"), "", "CSV (*.csv);;Alle Dateien (*)")
        if not filename:
            return
        try:
            self.lab.import_mangohud(filename)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))
        self._update_session()

    def _save_session(self):
        if not self.lab.last_session:
            QMessageBox.information(self, "Vitalux", tr("Noch keine Gaming-Sitzung abgeschlossen."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Gaming-Sitzung speichern"), "Vitalux-Gaming-Session.json", "JSON (*.json)")
        if not path:
            return
        try:
            self.lab.export_session(path if path.lower().endswith(".json") else path + ".json")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))

    def _update_session(self):
        live = self.lab.started is not None
        self.begin.setEnabled(not live)
        self.end.setEnabled(live)
        self.save_session.setEnabled(self.lab.last_session is not None)
        if live:
            self.session_report.setText(
                f"Aufzeichnung läuft: {self.lab.session_name} · {self.lab.session_count} Messpunkte")
            return
        report = self.lab.last_session
        if report:
            parts = [f"{report['name']} · {report['samples']} Messpunkte"]
            for key in ("gpu_usage", "gpu_temp", "gpu_clock", "cpu_usage", "vram_usage"):
                data = report["metrics"].get(key)
                if data:
                    title, unit = METRIC_TITLES[key]
                    parts.append(f"{title}: Ø {fmt(data['avg'],unit)}, "
                                 f"Min {fmt(data['min'],unit)}, Max {fmt(data['max'],unit)}")
            if self.lab.mangohud:
                hud = self.lab.mangohud
                parts.append(f"MangoHud ({hud['source']}): "
                             f"Ø FPS {_f(hud.get('avg_fps'))}; "
                             f"1%-Low ≈ {_f(hud.get('one_percent_low_approx'))}")
            self.session_report.setText("\n".join(parts))
        elif self.lab.mangohud:
            hud = self.lab.mangohud
            self.session_report.setText(
                f"MangoHud: Ø FPS {_f(hud.get('avg_fps'))} · "
                f"1%-Low ≈ {_f(hud.get('one_percent_low_approx'))}")
        else:
            self.session_report.setText(tr("Noch keine Gaming-Sitzung abgeschlossen."))

    def _take_snapshot(self, slot):
        if self.last_sample is None:
            return
        try:
            self.lab.snapshot(slot, self.last_sample)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))
            return
        self._update_comparison()

    def _update_comparison(self):
        lines = []
        if (all(self.lab.snapshots) and
                self.lab.snapshots[0]["gpu"] != self.lab.snapshots[1]["gpu"]):
            self.comparison.setText(tr(
                "Unterschiedliche Grafikkarten – Messungen nicht direkt vergleichbar."))
            return
        for key, a, b, delta in self.lab.comparison():
            title, unit = METRIC_TITLES[key]
            lines.append(f"{title}: {fmt(a,unit)} → {fmt(b,unit)} "
                         f"({'+' if delta > 0 else ''}{delta:.1f} {unit})")
        self.comparison.setText("\n".join(lines) if lines
                                else tr("Speichere zuerst Vorher und Nachher."))

    def _select_event(self, current, previous):
        if not current:
            return
        event = current.data(Qt.UserRole)
        values = event["metrics"]
        self.event_detail.setText(
            f"{event['time']} · {event['title']}\n"
            + "  ·  ".join(
                f"{METRIC_TITLES[k][0]} {fmt(values.get(k), METRIC_TITLES[k][1])}"
                for k in ("cpu_usage", "gpu_usage", "gpu_temp", "vram_usage")
            ))

    def _select_hardware(self, key):
        sample = self.last_sample or {}
        static = self._static
        gpu = next(iter(sample.get("gpus") or ()), {})
        if key == "mainboard":
            text = f"Mainboard: {static.get('board') or '–'} · BIOS: {static.get('bios') or '–'}"
        elif key == "cpu":
            cpu = sample.get("cpu") or {}
            text = f"{cpu.get('model') or 'CPU'} · Last {fmt(cpu.get('usage'), '%')} · " \
                   f"Temperatur {fmt(cpu.get('temp'), '°C')}"
        elif key == "gpu":
            text = f"{gpu.get('name') or 'GPU'} · {gpu.get('driver') or 'Treiber unbekannt'} · " \
                   f"Last {fmt(gpu.get('usage'), '%')} · " \
                   f"PCIe {gpu.get('pcie_current') or 'nicht verfügbar'}"
        elif key == "ram":
            ram = sample.get("ram") or {}
            text = f"RAM · Auslastung {fmt(ram.get('percent'), '%')}"
        else:
            disks = sample.get("disks") or []
            text = "Laufwerke: " + (", ".join(str(item.get("mount") or item.get("device") or "–")
                                               for item in disks[:5]) or "nicht verfügbar")
        self.hardware_detail.setText(text)

    def refresh(self, sample):
        self.last_sample = sample
        result = self.lab.detective({
            key: settings.get(key, default)
            for key, default in (("cpu_temp", 90), ("gpu_temp", 90),
                                 ("ram_usage", 90))
        })
        signature = tuple((name, detail) for name, detail, _ in result)
        if self._last_findings != signature:
            self._last_findings = signature
            self.findings.setText("\n\n".join(f"• {name}: {detail}"
                                             for name, detail, _ in result))
        self._update_session()
        if self.show_advanced.isChecked():
            rows = list(self.lab.history)[-900:]
            self.trend_chart.set_series([
                ([row["metrics"].get(metric) for row in rows], color)
                for metric, color in (
                    ("cpu_usage", theme.accent()),
                    ("gpu_usage", theme.secondary_accent()),
                    ("vram_usage", theme.TEAL),
                )
            ])
            events = tuple((event["time"], event["title"]) for event in self.lab.events)
            if events != self._last_events:
                self._last_events = events
                self.timeline.blockSignals(True)
                self.timeline.clear()
                for event in self.lab.events:
                    item = QListWidgetItem(f"{event['time'][11:19]}  ·  {event['title']}")
                    item.setData(Qt.UserRole, event)
                    self.timeline.addItem(item)
                self.timeline.blockSignals(False)


def _f(value):
    return f"{value:.1f}" if number(value) else "–"
