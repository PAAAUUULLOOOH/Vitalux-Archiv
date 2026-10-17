"""Native integrated disk benchmark in the Drives tab."""
import datetime
import os
import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QGridLayout,
    QHBoxLayout, QProgressBar, QSpinBox,
    QVBoxLayout, QWidget,
)
from .ui_locale import QCheckBox, QComboBox, QDialog, QFileDialog, QLabel, QMessageBox, QPushButton

from .disk_benchmark import (BenchmarkCancelled, FioUnavailable, PROFILES, get_profile_tests,
                             TestSpec, detect_fio, fio_source_info, resolve_target, run_benchmark)
from .widgets import Card, label
from .i18n import tr


BENCHMARK_DEFAULTS = {
    "profile": "Standard", "preset": "Standard", "size_mib": 1024, "runs": 5,
    "duration": 5, "interval": 5, "direct": True, "unit": "MB/s",
}


class DiskBenchmarkThread(QThread):
    update = Signal(int, str, object, str)
    complete = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, mountpoint, directory, size_mib, runs, tests, duration, interval,
                 direct, selected_row, profile, test_data, refill, parent=None):
        super().__init__(parent)
        self.params = dict(mountpoint=mountpoint, directory=directory, size_mib=size_mib,
                           runs=runs, tests=tests, duration=duration, interval=interval,
                           direct=direct, selected_row=selected_row, profile=profile,
                           test_data=test_data, refill=refill)
        self.cancel_event = threading.Event()

    def run(self):
        try:
            method = run_benchmark(**self.params, cancel=self.cancel_event,
                                   progress=lambda row, kind, value, text:
                                   self.update.emit(row, kind, value, text))
            self.complete.emit(method)
        except BenchmarkCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))

    def stop(self):
        self.cancel_event.set()


class TestOptionsDialog(QDialog):
    """Edit per-test block size, queue depth and threads without editing scripts."""
    def __init__(self, tests, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vitalux · Testparameter")
        self.setMinimumWidth(590)
        form = QVBoxLayout(self)
        form.addWidget(label("Jede Testzeile kann individuell angepasst werden:", "muted"))
        grid = QGridLayout()
        for col, title in enumerate(("Muster", "Blockgröße", "Queue Depth", "Threads")):
            grid.addWidget(label(title, "cardTitle"), 0, col)
        self.fields = []
        for i, test in enumerate(tests, start=1):
            pattern = QComboBox()
            pattern.addItem("SEQ", "seq")
            pattern.addItem("RND", "rand")
            pattern.setCurrentIndex(0 if test.pattern == "seq" else 1)
            block = QComboBox()
            for b in (4, 8, 16, 64, 128, 256, 512, 1024):
                block.addItem("1 MiB" if b == 1024 else f"{b} KiB", b)
            block.setCurrentIndex(block.findData(test.block_kib))
            depth = QSpinBox()
            depth.setRange(1, 64)
            depth.setValue(test.depth)
            threads = QSpinBox()
            threads.setRange(1, 16)
            threads.setValue(test.threads)
            for j, widget in enumerate((pattern, block, depth, threads)):
                grid.addWidget(widget, i, j)
            self.fields.append((pattern, block, depth, threads))
        form.addLayout(grid)
        form.addWidget(label("Hohe Queue Depth/Threadzahlen können das System vorübergehend stark auslasten.",
                             "muted", wrap=True))
        buttons = QHBoxLayout()
        cancel = QPushButton("Abbrechen")
        accept = QPushButton("Übernehmen")
        accept.setObjectName("primaryBtn")
        cancel.clicked.connect(self.reject)
        accept.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(accept)
        form.addLayout(buttons)

    def selection(self):
        return tuple(TestSpec(p.currentData(), b.currentData(), q.value(), t.value())
                     for p, b, q, t in self.fields)


class BenchmarkPanel(Card):
    def __init__(self):
        super().__init__("Laufwerks-Benchmark", hero=True)
        self.thread = None
        self._mountpoint = ""
        self._folder = ""
        self._volume_keys = ()
        self._completed = set()
        self._results = {}
        self._tests = PROFILES["Standard"]
        self._start_date = None
        self._last_profile = "Standard"
        self._preset = "Standard"

        self.body.addWidget(label("Laufwerksmessungen mit fio: wählbare Testprofile, Dateigrößen, "
                                  "Messzeitbegrenzung und Ergebnisauswertung.", "pageSub", wrap=True))
        opts = QGridLayout()
        opts.setHorizontalSpacing(12)
        opts.setVerticalSpacing(9)
        opts.addWidget(label("Laufwerk", "muted"), 0, 0)
        self.volumes = QComboBox()
        self.volumes.setMinimumWidth(260)
        self.volumes.currentIndexChanged.connect(self._volume_changed)
        opts.addWidget(self.volumes, 0, 1, 1, 5)
        opts.addWidget(label("Profil", "muted"), 1, 0)
        self.profile = QComboBox()
        for name in PROFILES:
            self.profile.addItem("Default" if name == "Standard" else name, name)
        self.profile.addItem("Benutzerdefiniert", "Benutzerdefiniert")
        self.profile.currentTextChanged.connect(self._profile_changed)
        opts.addWidget(self.profile, 1, 1, 1, 2)
        self.custom = QPushButton("Tests anpassen")
        self.custom.setObjectName("ghostBtn")
        self.custom.clicked.connect(self._customize)
        opts.addWidget(self.custom, 1, 3, 1, 3)
        opts.addWidget(label("Testgröße", "muted"), 2, 0)
        self.size_box = QComboBox()
        for size in (64, 128, 256, 512, 1024, 2048, 4096):
            self.size_box.addItem(f"{size} MiB" if size < 1024 else f"{size // 1024} GiB", size)
        self.size_box.setCurrentIndex(self.size_box.findData(1024))
        opts.addWidget(self.size_box, 2, 1)
        opts.addWidget(label("Durchläufe", "muted"), 2, 2)
        self.runs_box = QComboBox()
        for runs in (1, 3, 5, 9):
            self.runs_box.addItem(f"{runs}×", runs)
        self.runs_box.setCurrentIndex(self.runs_box.findData(5))
        opts.addWidget(self.runs_box, 2, 3)
        opts.addWidget(label("Messzeit", "muted"), 3, 0)
        self.duration_box = QComboBox()
        for seconds in (1, 3, 5, 10, 15, 30, 60):
            self.duration_box.addItem(f"{seconds} s", seconds)
        self.duration_box.setCurrentIndex(self.duration_box.findData(5))
        opts.addWidget(self.duration_box, 3, 1)
        opts.addWidget(label("Intervall", "muted"), 3, 2)
        self.interval_box = QComboBox()
        for seconds in (0, 1, 3, 5, 10):
            self.interval_box.addItem(f"{seconds} s", seconds)
        self.interval_box.setCurrentIndex(self.interval_box.findData(5))
        opts.addWidget(self.interval_box, 3, 3)
        self.direct_box = QCheckBox("Direct I/O (Systemcache umgehen)")
        self.direct_box.setChecked(True)
        opts.addWidget(self.direct_box, 3, 4, 1, 2)
        opts.addWidget(label("Testdaten", "muted"), 6, 0)
        self.test_data_box = QComboBox()
        self.test_data_box.addItem("Zufallsdaten", "random")
        self.test_data_box.addItem("Nullen", "zeros")
        opts.addWidget(self.test_data_box, 6, 1, 1, 2)
        self.refill_box = QCheckBox("Schreibpuffer kontinuierlich neu füllen")
        self.refill_box.setChecked(False)
        opts.addWidget(self.refill_box, 6, 3, 1, 3)
        opts.addWidget(label("Voreinstellung", "muted"), 7, 0)
        self.preset_box = QComboBox()
        self.preset_box.addItem("Standard", "Standard")
        self.preset_box.addItem("NVMe SSD", "NVMe SSD")
        self.preset_box.currentIndexChanged.connect(self._preset_changed)
        opts.addWidget(self.preset_box, 7, 1, 1, 2)
        opts.addWidget(label("Testordner", "muted"), 4, 0)
        self.path_label = label("–", "strong", wrap=True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        opts.addWidget(self.path_label, 4, 1, 1, 4)
        self.browse = QPushButton("Ordner wählen")
        self.browse.setObjectName("ghostBtn")
        self.browse.clicked.connect(self._browse)
        opts.addWidget(self.browse, 4, 5)
        opts.addWidget(label("Anzeige", "muted"), 5, 0)
        self.unit_box = QComboBox()
        self.unit_box.addItems(["MB/s", "IOPS", "µs"])
        self.unit_box.setCurrentIndex(0)  # MB/s is fio bandwidth (kB/s divided by 1000)
        self.unit_box.currentTextChanged.connect(self._change_unit)
        opts.addWidget(self.unit_box, 5, 1)
        self.body.addLayout(opts)

        results = QGridLayout()
        results.setHorizontalSpacing(11)
        results.setVerticalSpacing(10)
        results.addWidget(label("TEST  /  EINZELSTART", "cardTitle"), 0, 0)
        self.read_header = label(f"{tr('LESEN')}  /  MB/s", "cardTitle", Qt.AlignCenter)
        self.write_header = label(f"{tr('SCHREIBEN')}  /  MB/s", "cardTitle", Qt.AlignCenter)
        results.addWidget(self.read_header, 0, 1)
        results.addWidget(self.write_header, 0, 2)
        self.cells = {}
        self.row_buttons = []
        for row in range(4):
            btn = QPushButton(self._tests[row].name)
            btn.setObjectName("ghostBtn")
            btn.setMinimumHeight(52)
            btn.setToolTip("Nur diesen Test ausführen (Lesen und Schreiben)")
            btn.clicked.connect(lambda _=False, i=row: self._start(i))
            self.row_buttons.append(btn)
            results.addWidget(btn, row + 1, 0)
            for kind, col, color in (("read", 1, "#52d3ff"), ("write", 2, "#a78bfa")):
                cell = QLabel("–")
                cell.setAlignment(Qt.AlignCenter)
                cell.setMinimumHeight(70)
                cell.setObjectName('benchmarkResultRead' if kind == 'read'
                                   else 'benchmarkResultWrite')
                cell.setProperty('resultState', 'pending')
                results.addWidget(cell, row + 1, col)
                self.cells[(row, kind)] = cell
        results.setColumnStretch(0, 2)
        results.setColumnStretch(1, 3)
        results.setColumnStretch(2, 3)
        self.body.addLayout(results)

        actions = QHBoxLayout()
        self.start_button = QPushButton("▶  ALLE Tests starten")
        self.start_button.setObjectName("primaryBtn")
        self.start_button.clicked.connect(lambda: self._start(None))
        self.stop_button = QPushButton("■  Abbrechen")
        self.stop_button.setObjectName("ghostBtn")
        self.stop_button.clicked.connect(self._stop)
        self.stop_button.setEnabled(False)
        self.copy_button = QPushButton("Ergebnisse kopieren")
        self.copy_button.setObjectName("ghostBtn")
        self.copy_button.clicked.connect(self._copy)
        self.copy_button.setEnabled(False)
        self.save_button = QPushButton("Bericht speichern")
        self.save_button.setObjectName("ghostBtn")
        self.save_button.clicked.connect(self._save)
        self.save_button.setEnabled(False)
        self.reset_options_button = QPushButton("Standardwerte wiederherstellen")
        self.reset_options_button.setObjectName("ghostBtn")
        self.reset_options_button.setToolTip("Benchmark-Einstellungen auf die Standardwerte zurücksetzen")
        self.reset_options_button.clicked.connect(self._restore_benchmark_defaults)
        self.reset_options_button.setVisible(False)
        for w in (self.start_button, self.stop_button, self.copy_button, self.save_button,
                  self.reset_options_button):
            actions.addWidget(w)
        actions.addStretch()
        self.body.addLayout(actions)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.body.addWidget(self.progress_bar)
        self.status_label = label("Bereit. Standardprofil: 1 GiB × 5 Durchläufe, 5 s Testlimit.", "muted", wrap=True)
        self.body.addWidget(self.status_label)
        self.backend_label = label("", "muted", wrap=True)
        self.body.addWidget(self.backend_label)
        self._refresh_fio_info()
        self.body.addWidget(label('MB/s = 1.000.000 Bytes pro Sekunde. IOPS sind Ein-/Ausgabevorgänge pro Sekunde. Für Vergleichsmessungen identische Profile, Dauer, Dateigröße und Cache-Einstellungen verwenden.', 'muted', wrap=True))
        for widget in (self.profile, self.size_box, self.runs_box,
                       self.duration_box, self.interval_box, self.unit_box, self.test_data_box, self.preset_box):
            widget.currentIndexChanged.connect(self._update_reset_button)
        self.direct_box.toggled.connect(self._update_reset_button)
        self.refill_box.toggled.connect(self._update_reset_button)
        self._update_reset_button()
        self.body.addWidget(label(
            "Die Testdauer hängt von der Laufwerksgeschwindigkeit ab. Testdateien werden auf dem "
            "ausgewählten Dateisystem erstellt und nach Abschluss oder Abbruch entfernt. "
            "Achtung: hohe Last und echte Schreibvorgänge. Die Messwerte stammen direkt von fio. Globales Leeren des Linux-Page-Cache erfordert erhöhte Rechte und wird hier nicht automatisch durchgeführt.",
            "muted", wrap=True))

    def _options_differ_from_defaults(self):
        defaults = BENCHMARK_DEFAULTS
        return (self.profile.currentData() != defaults['profile']
                or self._tests != get_profile_tests(defaults['profile'], defaults['preset'])
                or self.preset_box.currentData() != defaults['preset']
                or self.size_box.currentData() != defaults['size_mib']
                or self.runs_box.currentData() != defaults['runs']
                or self.duration_box.currentData() != defaults['duration']
                or self.interval_box.currentData() != defaults['interval']
                or self.direct_box.isChecked() != defaults['direct']
                or self.unit_box.currentText() != defaults['unit']
                or self.test_data_box.currentData() != "random"
                or self.refill_box.isChecked())

    def _update_reset_button(self, *_):
        self.reset_options_button.setVisible(self._options_differ_from_defaults())

    def _restore_benchmark_defaults(self):
        """Restore measurement/display defaults, keeping the chosen target disk.

        Do not interfere with a benchmark in progress or change the chosen
        volume/target folder. Clearing old measurements avoids mixed profiles.
        """
        if self.thread is not None and self.thread.isRunning():
            return
        defaults = BENCHMARK_DEFAULTS
        widgets = (self.profile, self.size_box, self.runs_box,
                   self.duration_box, self.interval_box, self.unit_box, self.direct_box,
                   self.test_data_box, self.refill_box, self.preset_box)
        for widget in widgets:
            widget.blockSignals(True)
        try:
            self.profile.setCurrentIndex(self.profile.findData(defaults['profile']))
            self.preset_box.setCurrentIndex(self.preset_box.findData(defaults['preset']))
            self.size_box.setCurrentIndex(self.size_box.findData(defaults['size_mib']))
            self.runs_box.setCurrentIndex(self.runs_box.findData(defaults['runs']))
            self.duration_box.setCurrentIndex(self.duration_box.findData(defaults['duration']))
            self.interval_box.setCurrentIndex(self.interval_box.findData(defaults['interval']))
            self.direct_box.setChecked(defaults['direct'])
            self.test_data_box.setCurrentIndex(self.test_data_box.findData("random"))
            self.refill_box.setChecked(False)
            self.unit_box.setCurrentIndex(self.unit_box.findText(defaults['unit']))
            self._tests = get_profile_tests(defaults['profile'], defaults['preset'])
            self._preset = defaults['preset']
            self._last_profile = defaults['profile']
        finally:
            for widget in widgets:
                widget.blockSignals(False)
        self._update_rows()
        self._change_unit(defaults['unit'])
        self._update_reset_button()

    def _refresh_fio_info(self):
        info = fio_source_info()
        self.backend_label.setText(
            f"Benchmark-Engine: {info['version']} · "
            + ('integriert' if info['source'] == 'bundled' else 'System')
            if info else
            "Benchmark-Engine: fio ≥ 3.1 nicht verfügbar.")

    def _profile_changed(self, text):
        profile_key = self.profile.currentData()
        if profile_key in PROFILES:
            self._tests = get_profile_tests(profile_key, self.preset_box.currentData())
            self._last_profile = profile_key
            self._update_rows()
            self._update_reset_button()

    def _preset_changed(self, *_):
        self._preset = self.preset_box.currentData()
        name = self.profile.currentData()
        if name in PROFILES:
            self._tests = get_profile_tests(name, self._preset)
            self._update_rows()
        self._update_reset_button()

    def _customize(self):
        editor = TestOptionsDialog(self._tests, self)
        if editor.exec() == QDialog.Accepted:
            self._tests = editor.selection()
            self.profile.blockSignals(True)
            self.profile.setCurrentIndex(self.profile.findData("Benutzerdefiniert"))
            self.profile.blockSignals(False)
            self._update_rows()
            self._update_reset_button()

    def _update_rows(self):
        for row, button in enumerate(self.row_buttons):
            enabled = row < len(self._tests)
            button.setVisible(enabled)
            for mode in ("read", "write"):
                self.cells[(row, mode)].setVisible(enabled)
            if enabled:
                button.setText(self._tests[row].name)
        self._reset_results()

    def update_volumes(self, disks):
        keys = tuple(sorted((d["mount"], d["device"], d["fstype"]) for d in disks))
        if keys == self._volume_keys:
            return
        old_mount = self.volumes.currentData()
        self._volume_keys = keys
        self.volumes.blockSignals(True)
        self.volumes.clear()
        for mount, device, fstype in keys:
            self.volumes.addItem(f"{mount}  ·  {device} ({fstype})", mount)
        index = self.volumes.findData(old_mount) if old_mount else -1
        if index < 0:
            home = os.path.realpath(os.path.expanduser("~"))
            matches = sorted((m for m, _, _ in keys if home == m or home.startswith(m.rstrip("/") + "/")), key=len)
            index = self.volumes.findData(matches[-1]) if matches else self.volumes.findData("/")
        self.volumes.setCurrentIndex(max(0, index))
        self.volumes.blockSignals(False)
        if self.thread is None or not self.thread.isRunning():
            self._volume_changed(0)

    def _volume_changed(self, _):
        mount = self.volumes.currentData()
        self._mountpoint = mount or ""
        if not mount:
            self._folder = ""
        else:
            home = os.path.realpath(os.path.expanduser("~"))
            try:
                self._folder = resolve_target(mount, home)
            except (ValueError, OSError):
                self._folder = os.path.realpath(mount)
        self.path_label.setText(self._folder or "–")

    def _browse(self):
        chosen = QFileDialog.getExistingDirectory(self, "Testordner auswählen", self._folder or os.path.expanduser("~"))
        if not chosen:
            return
        try:
            self._folder = resolve_target(self._mountpoint, chosen)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))
            return
        self.path_label.setText(self._folder)

    def _format_value(self, result):
        unit = self.unit_box.currentText()
        if unit == "IOPS":
            return f"{result['iops']:,.1f}".replace(",", " ")
        if unit == "µs":
            latency = result.get('latency_us')
            return f"{latency:,.1f}".replace(",", " ") if latency is not None else "–"
        return f"{result['mbps']:,.2f}".replace(",", " ")

    def _change_unit(self, unit):
        self.read_header.setText(f"{tr('LESEN')}  /  {unit}")
        self.write_header.setText(f"{tr('SCHREIBEN')}  /  {unit}")
        for key, result in self._results.items():
            self.cells[key].setText(self._format_value(result))

    def _set_busy(self, busy):
        for w in (self.volumes, self.profile, self.custom, self.size_box, self.runs_box,
                  self.duration_box, self.interval_box, self.direct_box, self.refill_box, self.test_data_box, self.preset_box, self.browse,
                  self.unit_box, self.reset_options_button,
                  self.start_button, *self.row_buttons):
            w.setEnabled(not busy)
        self.stop_button.setEnabled(busy)

    @staticmethod
    def _mark_cell(cell, state):
        cell.setProperty('resultState', state)
        cell.style().unpolish(cell)
        cell.style().polish(cell)
        cell.update()

    def _reset_results(self):
        self._results.clear()
        self._completed.clear()
        for cell in self.cells.values():
            self._mark_cell(cell, 'pending')
            cell.setText("–")
            cell.setToolTip("")
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def _start(self, selected_row=None):
        if self.thread and self.thread.isRunning():
            return
        if not self._mountpoint:
            QMessageBox.warning(self, "Vitalux", "Bitte zuerst ein Laufwerk auswählen.")
            return
        try:
            directory = resolve_target(self._mountpoint, self._folder)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Vitalux", str(exc))
            return
        if detect_fio() is None:
            self._refresh_fio_info()
            QMessageBox.warning(self, "Vitalux · Benchmark",
                                "Das mitgelieferte fio kann nicht gestartet werden. Prüfe die Kompatibilität mit ./bin/fio --version und ./Portable-pruefen.sh.")
            return
        size = self.size_box.currentData()
        runs = self.runs_box.currentData()
        duration = self.duration_box.currentData()
        interval = self.interval_box.currentData()
        count = (len(self._tests) if selected_row is None else 1) * 2 * runs
        groups = (len(self._tests) if selected_row is None else 1) * 2
        estimate = count * duration + max(0, groups - 1) * interval
        minutes, seconds = divmod(estimate, 60)
        answer = QMessageBox.question(
            self, "Vitalux · Laufwerks-Benchmark",
            f"{tr('Laufwerk')}: {self._mountpoint}\n{tr('Testordner')}: {directory}\n"
            f"{tr('Dateigröße')}: {size} MiB · {tr('Durchläufe')}: {runs}×\n"
            f"{tr('Messzeit')}: {duration} s · {tr('Intervall')}: {interval} s\n"
            f"{tr('Anzahl Messungen')}: {count}\n"
            f"{tr('Messzeit maximal')}: {minutes} min {seconds} s + {tr('Vorbereitung')}.\n\n"
            + tr("ACHTUNG: Dies schreibt echte Daten und kann das Laufwerk stark beanspruchen. "
            "Nicht während wichtiger Dateioperationen ausführen.\n\nJetzt starten?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        if selected_row is None:
            self._reset_results()
        else:
            for kind in ("read", "write"):
                self._results.pop((selected_row, kind), None)
                self.cells[(selected_row, kind)].setText("–")
                self._mark_cell(self.cells[(selected_row, kind)], 'pending')
                self.cells[(selected_row, kind)].setToolTip("")
        self._start_date = datetime.datetime.now()
        self.progress_bar.setValue(0)
        self._set_busy(True)
        self.status_label.setText(tr("Testdatei wird angelegt …"))
        for i in range(len(self._tests)) if selected_row is None else (selected_row,):
            for kind in ('read', 'write'):
                self._mark_cell(self.cells[(i, kind)], 'running')
        self.thread = DiskBenchmarkThread(self._mountpoint, directory, size, runs,
                                          self._tests, duration, interval,
                                          self.direct_box.isChecked(), selected_row, self.profile.currentData(),
                                          self.test_data_box.currentData(),
                                          self.refill_box.isChecked(), self)
        self.thread.update.connect(self._progress)
        self.thread.complete.connect(self._finished)
        self.thread.failed.connect(self._error)
        self.thread.cancelled.connect(self._cancelled)
        self.thread.start()

    def _progress(self, row, kind, value, message):
        if kind == "phase":
            self.status_label.setText(tr(message))
            if isinstance(value, dict) and "percent" in value:
                # Progress never decreases, even if a queued stage update arrives
                # just after a pass or during a pause between tests.
                self.progress_bar.setValue(max(self.progress_bar.value(),
                                               min(99, int(value["percent"]))))
            return
        if kind == "pass":
            mode = value["mode"]
            res = value["result"]
            self.cells[(row, mode)].setText(self._format_value(res))
            self.status_label.setText(f"{tr(message)} · {res['mbps']:.2f} MB/s")
            self.progress_bar.setValue(max(self.progress_bar.value(),
                                           min(99, int(value.get("percent", 0)))))
            return
        if kind not in ("read", "write") or (row, kind) not in self.cells:
            return
        self._results[(row, kind)] = value
        self.cells[(row, kind)].setText(self._format_value(value))
        self._mark_cell(self.cells[(row, kind)], 'done')
        self.cells[(row, kind)].setToolTip(
            f"{'Bestwert aus' if self.profile.currentData() in ('Peak', 'Real World') else tr('Durchschnitt aus')} {value['passes']} {tr('Messungen')}\n"
            f"{value['mbps']:.2f} MB/s · {value['iops']:,.0f} IOPS\n"
            f"{tr('Latenz')}: {value['latency_us']:.1f} µs" if value['latency_us'] is not None
            else f"{value['mbps']:.2f} MB/s · {value['iops']:,.0f} IOPS")
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)

    def _finished(self, backend):
        for key, cell in self.cells.items():
            if cell.property('resultState') == 'running':
                self._mark_cell(cell, 'done' if key in self._results else 'pending')
        self._set_busy(False)
        self.progress_bar.setValue(100)
        self._refresh_fio_info()
        self.status_label.setText(tr("Alle gewählten Messdurchläufe abgeschlossen. Temporäre Dateien entfernt."))

    def _error(self, message):
        for cell in self.cells.values():
            if cell.property('resultState') == 'running': self._mark_cell(cell, 'pending')
        self._set_busy(False)
        self.status_label.setText(tr("Fehler") + ": " + tr(message))
        QMessageBox.warning(self, "Vitalux · Benchmarkfehler", message)

    def _cancelled(self):
        for cell in self.cells.values():
            if cell.property('resultState') == 'running': self._mark_cell(cell, 'pending')
        self._set_busy(False)
        self.status_label.setText(tr("Benchmark abgebrochen. Temporäre Dateien entfernt."))

    def _stop(self):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.stop_button.setEnabled(False)
            self.status_label.setText(tr("Stoppe laufenden Test …"))

    def _report(self):
        lines = [tr("Vitalux Laufwerks-Benchmark"), "=" * 44,
                 f"{tr('Datum')}: {self._start_date:%Y-%m-%d %H:%M:%S}" if self._start_date else "",
                 f"{tr('Laufwerk')}: {self._mountpoint}", f"{tr('Testordner')}: {self._folder}",
                 f"{tr('Profil')}: {self.profile.currentText()} · Voreinstellung: {self.preset_box.currentText()}",
                 f"{tr('Testgröße')}: {self.size_box.currentData()} MiB × {self.runs_box.currentData()} {tr('Durchläufe')}",
                 f"{tr('Messzeit')}: {self.duration_box.currentData()} s (Obergrenze); {tr('Intervall')}: {self.interval_box.currentData()} s",
                 f"Testdaten: {self.test_data_box.currentText()}; refill_buffers: {int(self.refill_box.isChecked())}",
                 "Messmethode: fio (libaio) · ohne systemweites drop_caches",
                 f"Direct I/O: {tr('Ja') if self.direct_box.isChecked() else tr('Nein')}", "",
                 tr("Test                     Lesen MB/s      Schreiben MB/s")]
        for i, test in enumerate(self._tests):
            read = self._results.get((i, 'read'))
            write = self._results.get((i, 'write'))
            lines.append(f"{test.name:24} {read['mbps']:10.2f}" if read else f"{test.name:24} {'–':>10}")
            lines[-1] += f"    {write['mbps']:10.2f}" if write else "              –"
            for kind, value in ((tr('Lesen'), read), (tr('Schreiben'), write)):
                if value:
                    latency = f"{value['latency_us']:.2f} µs" if value['latency_us'] is not None else "–"
                    lines.append(f"  {kind}: {value['iops']:.1f} IOPS; {tr('Latenz')} {latency}; {value['passes']} {tr('Messungen')}")
        lines.append(tr("\nHinweis: Testparameter, Dateisystem, Cache-/CoW-Verhalten und Systemlast beeinflussen Ergebnisse."))
        return "\n".join(lines) + "\n"

    def _copy(self):
        QApplication.clipboard().setText(self._report())
        self.status_label.setText("Messbericht in die Zwischenablage kopiert.")

    def _save(self):
        filename = "Vitalux-Benchmark-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".txt"
        path, _ = QFileDialog.getSaveFileName(self, "Benchmarkbericht speichern", filename, tr("Textdatei (*.txt)"))
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._report())
        except OSError as exc:
            QMessageBox.warning(self, "Vitalux", f"Bericht konnte nicht gespeichert werden: {exc}")
            return
        self.status_label.setText(f"{tr('Bericht gespeichert')}: {path}")

    def stop_and_wait(self):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            return bool(self.thread.wait(10000))
        return True
