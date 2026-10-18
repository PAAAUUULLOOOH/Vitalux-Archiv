"""Native Vitalux tuning panel backed by the original LACT daemon."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from copy import deepcopy

from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QInputDialog, QLineEdit,
                              QSpinBox, QDoubleSpinBox, QPlainTextEdit, QMenu,
                              QGroupBox, QVBoxLayout, QGridLayout, QLabel)

from .ui_locale import QPushButton, QComboBox, QMessageBox, QCheckBox
from .widgets import Card, label
from .lact_client import (LactClient, LactError, CLOCK_FIELDS, merged_gpu_config,
                          parse_fan_curve, format_fan_curve,
                          complete_fan_settings, read_gpu_metrics, fan_temperature_sources)
from .i18n import tr
from .gpu_setup import stage_gpu_setup, remove_gpu_setup


class LactTuningCard(Card):
    """Profile, overclock, voltage and fan controls. No GPU writes on page load."""
    def __init__(self):
        super().__init__("Vitalux GPU-Tuning")
        self.client = LactClient()
        self.gpu_id = None
        self.current_config = {}
        self.stats = {}
        self.profile_state = {}
        self.capabilities = {}
        self.clock_info = {}
        self._loading = False
        self.pending = False
        self.confirm_timer = QTimer(self)
        self.confirm_timer.setSingleShot(True)
        self.confirm_timer.timeout.connect(self._expired)

        self.status = label("Vitalux erkennt deine Grafikkarte.", "muted", wrap=True)
        self.body.addWidget(self.status)
        self.setup_button = QPushButton("GPU-Steuerung einrichten")
        self.setup_button.clicked.connect(self._setup_service)
        self.setup_button.setToolTip(
            "Installiert den mit Vitalux mitgelieferten GPU-Dienst. "
            "Einmalige Administratorbestätigung erforderlich.")
        self.body.addWidget(self.setup_button)
        self.setup_process = None
        self.setup_staging_dir = None
        devices = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._device_selected)
        self.connect_button = QPushButton("Aktualisieren")
        self.connect_button.clicked.connect(self.reload)
        devices.addWidget(label("Grafikkarte"))
        devices.addWidget(self.device_combo, 1)
        devices.addWidget(self.connect_button)
        self.body.addLayout(devices)

        self.live_group = QGroupBox("Aktuelle GPU-Werte")
        live_layout = QGridLayout(self.live_group)
        live_layout.setHorizontalSpacing(20)
        live_layout.setVerticalSpacing(10)
        self.live_readings = {}
        for i, (key, title) in enumerate((
            ("gpu", "GPU-Takt"), ("vram", "VRAM-Takt"),
            ("voltage", "GPU-Spannung"), ("temperature", "Temperatur"),
            ("power", "Leistungsaufnahme"), ("fan", "Lüfter"),
            ("power_cap", "Power-Limit (aktuell)"), ("load", "Auslastung"),
        )):
            row, column = divmod(i, 2)
            cell = QVBoxLayout()
            cell.setSpacing(1)
            cell.addWidget(label(title, "muted"))
            value = QLabel("–")
            value.setObjectName("gpuReadingValue")
            self.live_readings[key] = value
            cell.addWidget(value)
            live_layout.addLayout(cell, row, column)
        self.body.addWidget(self.live_group)

        self.profile_group = QGroupBox("GPU-Profile")
        profile_layout = QVBoxLayout(self.profile_group)
        profile_layout.setSpacing(8)
        profiles = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        for text, attr, action in (
            ("Profil laden", "load_btn", self._load_profile),
            ("Neu", "create_btn", self._create_profile),
            ("Löschen", "delete_btn", self._delete_profile)):
            button = QPushButton(text)
            setattr(self, attr, button)
            button.clicked.connect(action)
        profiles.addWidget(label("Profil"))
        profiles.addWidget(self.profile_combo, 1)
        for button in (self.load_btn, self.create_btn, self.delete_btn):
            profiles.addWidget(button)
        profile_layout.addLayout(profiles)
        self.auto = QCheckBox("Profile automatisch wechseln")
        self.auto.clicked.connect(self._change_auto)
        profile_layout.addWidget(self.auto)

        rule = QHBoxLayout()
        self.rule_type = QComboBox()
        for title, value in (("Keine Regel", None), ("Prozess", "process"), ("GameMode", "gamemode")):
            self.rule_type.addItem(title, value)
        self.rule_process = QLineEdit()
        self.rule_process.setPlaceholderText("Prozessname, z. B. vkcube")
        self.rule_save = QPushButton("Regel speichern")
        self.rule_save.clicked.connect(self._save_rule)
        rule.addWidget(self.rule_type)
        rule.addWidget(self.rule_process, 1)
        rule.addWidget(self.rule_save)
        profile_layout.addLayout(rule)
        self.body.addWidget(self.profile_group)

        self.clock_group = QGroupBox("Taktraten, Leistung und Spannung")
        clock_layout = QVBoxLayout(self.clock_group)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignLeft)
        self.form.setSpacing(10)
        self.fields = {}
        for key, title, minimum, maximum, suffix in (
            ("power_cap", "Power-Limit", 1, 1000, " W"),
            ("min_core_clock", "GPU-Takt Minimum", 0, 6000, " MHz"),
            ("max_core_clock", "GPU-Takt Maximum", 0, 6000, " MHz"),
            ("min_memory_clock", "VRAM-Takt Minimum", 0, 6000, " MHz"),
            ("max_memory_clock", "VRAM-Takt Maximum", 0, 6000, " MHz"),
            ("voltage_offset", "Spannungs-Offset", -500, 500, " mV"),
            ("min_voltage", "Spannung Minimum", 0, 2000, " mV"),
            ("max_voltage", "Spannung Maximum", 0, 2000, " mV"),
            ("voltage_boost", "Spannungs-Boost", 0, 100, " %")):
            widget = QDoubleSpinBox() if key == "power_cap" else QSpinBox()
            widget.setRange(minimum, maximum)
            widget.setSuffix(suffix)
            widget.setSpecialValueText("Nicht gesetzt")
            widget.setProperty("lact_null", True)
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda pos, w=widget: self._show_clear_menu(w, pos))
            widget.valueChanged.connect(
                lambda _v, w=widget: w.setProperty("lact_null", False))
            self.fields[key] = widget
            self.form.addRow(label(title), widget)
        self.performance = QComboBox()
        for title, value in (("Treiberstandard", None), ("Automatisch", "auto"), ("Niedrig", "low"),
                             ("Hoch", "high"), ("Manuell", "manual")):
            self.performance.addItem(title, value)
        self.form.addRow(label("Leistungsprofil"), self.performance)
        self.gpu_offset = QSpinBox()
        self.gpu_offset.setRange(-500, 1000)
        self.gpu_offset.setSuffix(" MHz")
        self.gpu_offset.setProperty("lact_null", True)
        self.gpu_offset.setToolTip("GPU-Taktoffset – verfügbar bei unterstützten GPUs.")
        self.gpu_offset.valueChanged.connect(
            lambda _v: self.gpu_offset.setProperty("lact_null", False))
        self.form.addRow(label("GPU-Takt-Offset"), self.gpu_offset)
        clock_layout.addLayout(self.form)
        clock_layout.addWidget(label(
            "Oben stehen aktuelle Messwerte. Hier legst du unterstützte Grenzen und Offsets fest.",
            "muted", wrap=True))
        self.body.addWidget(self.clock_group)

        self.fan_group = QGroupBox("Lüftersteuerung")
        fan_layout = QVBoxLayout(self.fan_group)
        fan_row = QHBoxLayout()
        self.fan_enabled = QCheckBox("Eigene Lüftersteuerung")
        self.fan_mode = QComboBox()
        self.fan_mode.addItem("Feste Drehzahl", "static")
        self.fan_mode.addItem("Lüfterkurve", "curve")
        self.fan_speed = QSpinBox()
        self.fan_speed.setRange(0, 100)
        self.fan_speed.setSuffix(" %")
        self.fan_mode.currentIndexChanged.connect(self._toggle_fan_controls)
        fan_row.addWidget(self.fan_enabled)
        fan_row.addWidget(self.fan_mode)
        fan_row.addWidget(self.fan_speed)
        fan_layout.addLayout(fan_row)
        source_row = QHBoxLayout()
        source_row.addWidget(label("Temperaturquelle"))
        self.fan_temperature = QComboBox()
        self.fan_temperature.addItem("GPU (edge)", "edge")
        source_row.addWidget(self.fan_temperature, 1)
        fan_layout.addLayout(source_row)
        fan_layout.addWidget(label("Lüfterkurve · Temperatur °C: Drehzahl %", "muted"))
        self.fan_curve = QPlainTextEdit()
        self.fan_curve.setMaximumHeight(116)
        self.fan_curve.setPlaceholderText("40: 30\n50: 35\n60: 50\n70: 75\n80: 100")
        fan_layout.addWidget(self.fan_curve)
        self.body.addWidget(self.fan_group)
        self.advanced_toggle = QPushButton("Expertenoptionen anzeigen")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        self.body.addWidget(self.advanced_toggle)
        self.advanced_group = QGroupBox("Experten-Einstellungen (JSON)")
        advanced_layout = QVBoxLayout(self.advanced_group)
        advanced_layout.addWidget(label(
            "Optionale Treiberparameter. Bestehende Einstellungen bleiben erhalten.",
            "muted", wrap=True))
        self.extra = QPlainTextEdit()
        self.extra.setMaximumHeight(110)
        self.extra.setToolTip("Erweiterte GPU-Konfiguration; bestehende Einstellungen bleiben erhalten.")
        advanced_layout.addWidget(self.extra)
        self.body.addWidget(self.advanced_group)
        self.advanced_group.hide()
        buttons = QHBoxLayout()
        self.apply_btn = QPushButton("Änderungen testen")
        self.apply_btn.clicked.connect(self._apply)
        self.confirm_btn = QPushButton("Bestätigen")
        self.confirm_btn.clicked.connect(self._confirm)
        self.revert_btn = QPushButton("Zurücksetzen")
        self.revert_btn.clicked.connect(self._revert)
        for button in (self.apply_btn, self.confirm_btn, self.revert_btn):
            buttons.addWidget(button)
        self.body.addLayout(buttons)
        self.body.addWidget(label(
            "Vitalux setzt unbestätigte Änderungen automatisch zurück (standardmäßig nach 5 Sekunden). "
            "Nur unterstützte GPU-Optionen verwenden; Übertaktung kann das System instabil machen.",
            "muted", wrap=True))
        self.fan_enabled.toggled.connect(self._toggle_fan_controls)
        for group in (self.live_group, self.profile_group, self.clock_group,
                      self.fan_group, self.advanced_group):
            group.setObjectName("gpuTuningGroup")
        self.fan_curve.setObjectName("gpuCurveInput")
        self.extra.setObjectName("gpuExpertInput")
        self.apply_btn.setObjectName("primaryBtn")
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(4000)
        self.refresh_timer.timeout.connect(self._refresh_live)
        self._set_access(False)
        self._first_show = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(0, self.reload)

    def _toggle_advanced(self, shown):
        self.advanced_group.setVisible(shown)
        self.advanced_toggle.setText(
            tr("Expertenoptionen ausblenden") if shown else tr("Expertenoptionen anzeigen"))

    def _set_access(self, available):
        for widget in (self.profile_combo, self.load_btn, self.create_btn, self.delete_btn,
                       self.auto, self.rule_type, self.rule_process, self.rule_save,
                       self.performance, self.fan_enabled, self.fan_mode, self.fan_speed,
                       self.fan_temperature, self.fan_curve, self.extra, self.gpu_offset, *self.fields.values()):
            widget.setEnabled(available and not self.pending)
        if available and not self.pending:
            for key, widget in self.fields.items():
                widget.setEnabled(self.capabilities.get(key, False))
            self.gpu_offset.setEnabled(self.capabilities.get("gpu_offset", False))
            self.fan_enabled.setEnabled(self.capabilities.get("fan", False))
            self._toggle_fan_controls()
            name = self.profile_combo.currentData()
            self.rule_save.setEnabled(bool(name))
            self.delete_btn.setEnabled(bool(name))
        self.apply_btn.setEnabled(available and not self.pending)
        self.confirm_btn.setEnabled(self.pending)
        self.revert_btn.setEnabled(self.pending)

    def _error(self, error):
        QMessageBox.warning(self, "GPU-Tuning", str(error))
        self.status.setText(str(error))

    def _setup_service(self):
        if self.setup_process is not None:
            return
        if not shutil.which("pkexec"):
            self._error("Die Administratorabfrage (pkexec) fehlt auf diesem System.")
            return
        root = Path(__file__).resolve().parents[1]
        try:
            self.setup_staging_dir, installer = stage_gpu_setup(root)
        except (OSError, ValueError) as exc:
            self._error(tr("GPU-Steuerung konnte nicht vorbereitet werden: {}").format(exc))
            return
        self.setup_button.setEnabled(False)
        self.status.setText("Vitalux GPU-Steuerung wird eingerichtet. Administratorabfrage öffnen.")
        process = QProcess(self)
        self.setup_process = process
        process.finished.connect(self._setup_finished)
        process.errorOccurred.connect(self._setup_process_error)
        process.start(shutil.which("pkexec"), ["/usr/bin/python3", str(installer), "--install"])

    def _setup_process_error(self, _error):
        process = self.setup_process
        if process is not None and process.state() == QProcess.NotRunning:
            self._setup_finished(1, QProcess.CrashExit)

    def _cleanup_setup_staging(self):
        stage, self.setup_staging_dir = self.setup_staging_dir, None
        remove_gpu_setup(stage)

    def _setup_finished(self, code, _status):
        process = self.setup_process
        if process is None:
            return
        error_text = bytes(process.readAllStandardError()).decode("utf-8", "replace").strip()
        if not error_text and process.error() != QProcess.UnknownError:
            error_text = process.errorString()
        process.deleteLater()
        self.setup_process = None
        self._cleanup_setup_staging()
        self.setup_button.setEnabled(True)
        if code == 0:
            self.status.setText("Vitalux GPU-Steuerung gestartet. Grafikkarte wird verbunden.")
            QTimer.singleShot(800, self.reload)
        elif code not in (126, 127):
            self._error(error_text or "GPU-Steuerung konnte nicht eingerichtet werden.")
        else:
            self.status.setText("Einrichtung abgebrochen. GPU-Monitoring funktioniert weiterhin.")

    def _show_detected_gpus(self, reason):
        """GPU detection belongs to Vitalux, even when tuning is not configured."""
        from .sensors import gpu_info
        detected = gpu_info()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for gpu in detected:
            self.device_combo.addItem(gpu.get("name") or "Grafikkarte erkannt", None)
        self.device_combo.blockSignals(False)
        if detected:
            source = detected[0]
            def val(key, unit):
                number = source.get(key)
                return f"{number:.0f} {unit}" if isinstance(number, (int, float)) else "–"
            metrics = {
                "gpu": val("clock", "MHz"), "vram": val("clock_mem", "MHz"),
                "voltage": "–", "temperature": val("temp", "°C"),
                "power": val("power", "W"), "fan": val("fan_rpm", "U/min"),
                "power_cap": "–", "load": val("usage", "%"),
            }
            for key, widget in self.live_readings.items():
                widget.setText(metrics[key])
            names = ", ".join(str(g.get("name") or "Grafikkarte") for g in detected)
            self.status.setText("Grafikkarte erkannt: " + names + ". "
                                "Für das GPU-Tuning bitte Vitalux GPU-Steuerung einrichten.")
        else:
            self.status.setText("Noch keine Grafikkarte erkannt. " + str(reason))
        self.setup_button.setVisible(True)

    def reload(self):
        if self.pending:
            return
        try:
            devices = self.client.devices()
            self._loading = True
            selected = self.gpu_id
            self.device_combo.clear()
            devices.sort(key=lambda item: item.get("device_type") != "Dedicated")
            for device in devices:
                self.device_combo.addItem(device.get("name") or device["id"], device["id"])
            target = self.device_combo.findData(selected)
            if target >= 0:
                self.device_combo.setCurrentIndex(target)
            self._loading = False
            self.setup_button.setVisible(False)
            self._device_selected()
        except (LactError, ValueError) as exc:
            self._loading = False
            self.gpu_id = None
            self.refresh_timer.stop()
            self._set_access(False)
            self._show_detected_gpus(exc)

    def _device_selected(self, *_):
        if self._loading or self.pending:
            return
        self.gpu_id = self.device_combo.currentData()
        if not self.gpu_id:
            self._set_access(False)
            return
        try:
            self.current_config = self.client.gpu_config(self.gpu_id)
            try:
                self.stats = self.client.device_stats(self.gpu_id) or {}
            except LactError:
                self.stats = {}
            try:
                clocks = self.client.device_clocks(self.gpu_id) or {}
            except LactError:
                clocks = {}
            self._detect_capabilities(clocks)
            self._update_live_readings(self.stats)
            self._load_fields()
            try:
                self._load_profiles()
            except LactError as exc:
                self.profile_state = {"profiles": {}}
                self.status.setText(tr("Profilverwaltung ist derzeit nicht verfügbar: {}").format(exc))
            else:
                self.status.setText("Vitalux GPU-Steuerung aktiv · Einstellungen verfügbar")
            self._set_access(True)
            self.refresh_timer.start()
        except (LactError, ValueError) as exc:
            self._set_access(False)
            self.status.setText(str(exc))

    @staticmethod
    def _clock_limits(clocks):
        """Real, driver-advertised AMD ranges; do not show fabricated limits."""
        table = clocks.get("table") if isinstance(clocks, dict) else None
        if not isinstance(table, dict):
            return {}
        if table.get("type") != "amd":
            return {}
        value = table.get("value") or {}
        data = value.get("data") or {} if isinstance(value, dict) else {}
        od = data.get("od_range") or {} if isinstance(data, dict) else {}
        return {
            "min_core_clock": od.get("sclk"),
            "max_core_clock": od.get("sclk"),
            "min_memory_clock": od.get("mclk"),
            "max_memory_clock": od.get("mclk"),
            "voltage_offset": od.get("voltage_offset"),
            "gpu_offset": od.get("sclk_offset"),
        }

    def _detect_capabilities(self, clocks):
        self.clock_info = clocks if isinstance(clocks, dict) else {}
        cap = self.capabilities = {key: False for key in CLOCK_FIELDS}
        ranges = self._clock_limits(self.clock_info)
        for key, raw in ranges.items():
            supported = (
                isinstance(raw, dict) and
                type(raw.get("min")) is int and type(raw.get("max")) is int
                and raw["min"] < raw["max"]
            )
            cap[key] = supported
            widget = self.gpu_offset if key == "gpu_offset" else self.fields[key]
            if supported:
                widget.setRange(raw["min"], raw["max"])
                widget.setToolTip(f"Treiberbereich: {raw['min']} bis {raw['max']}")
        power = self.stats.get("power") or {} if isinstance(self.stats, dict) else {}
        cap["power_cap"] = isinstance(power, dict) and (
            isinstance(power.get("cap_max"), (int, float))
            and isinstance(power.get("cap_min"), (int, float))
            and power["cap_max"] > power["cap_min"])
        fan = self.stats.get("fan") or {} if isinstance(self.stats, dict) else {}
        cap["fan"] = isinstance(fan, dict) and (
            fan.get("speed_max") is not None or fan.get("pwm_max") is not None
            or fan.get("control_enabled") is True)

    def _update_live_readings(self, stats):
        values = read_gpu_metrics(stats)
        for key, widget in self.live_readings.items():
            widget.setText(values[key])

    def _refresh_live(self):
        if not self.gpu_id or self.pending or not self.isVisible():
            return
        try:
            current = self.client.device_stats(self.gpu_id)
            if isinstance(current, dict):
                self.stats = current
                self._update_live_readings(current)
        except LactError:
            # Monitoring elsewhere in Vitalux is unaffected by a service restart.
            pass

    def _load_fields(self):
        config = self.current_config
        power = (self.stats.get("power") or {}) if isinstance(self.stats, dict) else {}
        if isinstance(power, dict):
            lo, hi = power.get("cap_min"), power.get("cap_max")
            if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo < hi and hi > 0:
                self.fields["power_cap"].setRange(max(1.0, float(lo)), float(hi))
        for key, widget in self.fields.items():
            value = config.get(key)
            widget.blockSignals(True)
            widget.setValue(value if value is not None else widget.minimum())
            widget.blockSignals(False)
            widget.setProperty("lact_null", value is None)
            widget.setToolTip("Wert einstellen. Mit 'Zurücksetzen' im Kontextmenü wieder auf Standard.")
        table = (self.clock_info.get("table") or {}).get("value") or {}
        data = table.get("data") or {} if isinstance(table, dict) else {}
        offsets = config.get("gpu_clock_offsets") or {}
        active_offset = offsets.get("0", data.get("sclk_offset", 0)) if isinstance(offsets, dict) else 0
        self.gpu_offset.blockSignals(True)
        self.gpu_offset.setValue(int(active_offset or 0))
        self.gpu_offset.blockSignals(False)
        self.gpu_offset.setProperty("lact_null", not isinstance(offsets, dict) or "0" not in offsets)
        self.performance.blockSignals(True)
        performance = self.performance.findData(config.get("performance_level"))
        self.performance.setCurrentIndex(max(0, performance))
        self.performance.blockSignals(False)
        settings = config.get("fan_control_settings") or {}
        fan = self.stats.get("fan") or {} if isinstance(self.stats, dict) else {}
        keys = fan_temperature_sources(self.stats)
        selected = settings.get("temperature_key") or fan.get("temperature_key") or ("edge" if "edge" in keys else keys[0])
        if selected not in keys:
            keys.append(selected)
        self.fan_temperature.blockSignals(True)
        self.fan_temperature.clear()
        for key in keys:
            self.fan_temperature.addItem(key.capitalize(), key)
        self.fan_temperature.setCurrentIndex(max(0, self.fan_temperature.findData(selected)))
        self.fan_temperature.blockSignals(False)
        self.fan_enabled.setChecked(bool(config.get("fan_control_enabled", False)))
        self.fan_mode.setCurrentIndex(max(0, self.fan_mode.findData(settings.get("mode", "curve"))))
        self.fan_speed.setValue(round(float(settings.get("static_speed", 0.5)) * 100))
        self.fan_curve.setPlainText(format_fan_curve(settings.get("curve")))
        handled = {"power_cap", "performance_level", "fan_control_enabled",
                   "fan_control_settings", "gpu_clock_offsets", *CLOCK_FIELDS}
        self.extra.setPlainText(json.dumps(
            {k: v for k, v in config.items() if k not in handled},
            ensure_ascii=False, indent=2))

    def _toggle_fan_controls(self, *_):
        enabled = not self.pending and self.capabilities.get("fan", False)
        for widget in (self.fan_mode, self.fan_speed, self.fan_curve, self.fan_temperature):
            widget.setEnabled(enabled and self.fan_enabled.isChecked())
        if enabled and self.fan_enabled.isChecked():
            self.fan_speed.setEnabled(self.fan_mode.currentData() == "static")
            self.fan_curve.setEnabled(self.fan_mode.currentData() == "curve")
            self.fan_temperature.setEnabled(self.fan_mode.currentData() == "curve")

    def _show_clear_menu(self, widget, pos):
        menu = QMenu(widget)
        reset = menu.addAction(tr("Auf Treiberstandard zurücksetzen"))
        if menu.exec(widget.mapToGlobal(pos)) == reset:
            widget.setValue(widget.minimum())
            widget.setProperty("lact_null", True)

    def _load_profiles(self):
        self.profile_state = self.client.profiles()
        selected = self.profile_state.get("current_profile")
        self._loading = True
        self.profile_combo.clear()
        self.profile_combo.addItem("Standard", None)
        for name in self.profile_state["profiles"]:
            self.profile_combo.addItem(name, name)
        index = self.profile_combo.findData(selected)
        self.profile_combo.setCurrentIndex(max(0, index))
        self.auto.setChecked(bool(self.profile_state.get("auto_switch")))
        self._loading = False
        self._profile_changed()

    def _profile_changed(self, *_):
        if self._loading:
            return
        name = self.profile_combo.currentData()
        rule = (self.profile_state.get("profiles") or {}).get(name) or {}
        if not isinstance(rule, dict):
            rule = {}
        self.rule_type.setCurrentIndex(max(0, self.rule_type.findData(rule.get("type"))))
        filt = rule.get("filter")
        self.rule_process.setText(filt.get("name", "") if isinstance(filt, dict) else "")
        self.rule_save.setEnabled(bool(name) and not self.pending)
        self.delete_btn.setEnabled(bool(name) and not self.pending)

    def _load_profile(self):
        self._set_profile(self.profile_combo.currentData(), self.auto.isChecked())

    def _change_auto(self, *_):
        self._set_profile(self.profile_combo.currentData(), self.auto.isChecked())

    def _set_profile(self, name, auto):
        try:
            self.client.select_profile(name, auto=auto)
            self._device_selected()
        except LactError as exc:
            self._error(exc)

    def _create_profile(self):
        name, ok = QInputDialog.getText(self, tr("Neues Profil"), tr("Profilname"))
        if not ok or not name.strip():
            return
        try:
            if name in self.profile_state.get("profiles", {}):
                raise ValueError("Profil existiert bereits.")
            self.client.create_profile(name, base="default")
            self._load_profiles()
            self.profile_combo.setCurrentIndex(self.profile_combo.findData(name))
        except (LactError, ValueError) as exc:
            self._error(exc)

    def _delete_profile(self):
        name = self.profile_combo.currentData()
        if not name:
            return
        if QMessageBox.question(self, "Profil löschen", f"Profil '{name}' wirklich löschen?") != QMessageBox.Yes:
            return
        try:
            self.client.delete_profile(name)
            self._device_selected()
        except LactError as exc:
            self._error(exc)

    def _save_rule(self):
        name = self.profile_combo.currentData()
        if not name:
            return
        kind = self.rule_type.currentData()
        proc = self.rule_process.text().strip()
        if kind == "process" and not proc:
            self._error("Bitte einen Prozessnamen angeben.")
            return
        rule = {"type": kind, "filter": {"name": proc}} if kind == "process" else (
            {"type": "gamemode", "filter": {"name": proc}} if kind == "gamemode" and proc else
            {"type": "gamemode"} if kind == "gamemode" else None)
        try:
            hooks = self.profile_state.get("profile_hooks", {}).get(name, {})
            self.client.set_profile_rule(name, rule, hooks)
            self._load_profiles()
            self.status.setText("Profilregel gespeichert")
        except LactError as exc:
            self._error(exc)

    def _collect(self):
        overrides = {}
        for key, widget in self.fields.items():
            if not widget.isEnabled():
                continue
            value = None if widget.property("lact_null") else widget.value()
            if value != self.current_config.get(key):
                overrides[key] = value
        if self.gpu_offset.isEnabled() and not self.gpu_offset.property("lact_null"):
            old_offsets = self.current_config.get("gpu_clock_offsets") or {}
            new_offsets = deepcopy(old_offsets)
            new_offsets["0"] = self.gpu_offset.value()
            if new_offsets != old_offsets:
                overrides["gpu_clock_offsets"] = new_offsets
        mode = self.performance.currentData()
        if mode != self.current_config.get("performance_level"):
            overrides["performance_level"] = mode
        if self.capabilities.get("fan", False):
            enabled = self.fan_enabled.isChecked()
            if enabled != bool(self.current_config.get("fan_control_enabled", False)):
                overrides["fan_control_enabled"] = enabled
            if enabled:
                old_fan = self.current_config.get("fan_control_settings") or {}
                mode = self.fan_mode.currentData()
                old_speed = round(float(old_fan.get("static_speed", 0.5)) * 100)
                current_temp = old_fan.get("temperature_key")
                temperature_changed = (
                    mode == "curve" and self.fan_temperature.currentData() !=
                    (current_temp or (self.stats.get("fan") or {}).get("temperature_key") or "edge"))
                dirty = (
                    not self.current_config.get("fan_control_enabled")
                    or mode != old_fan.get("mode", "curve")
                    or any(key not in old_fan for key in ("temperature_key", "interval_ms", "curve"))
                    or (mode == "static" and self.fan_speed.value() != old_speed)
                    or (mode == "curve" and (temperature_changed or
                        self.fan_curve.toPlainText() != format_fan_curve(old_fan.get("curve"))))
                )
                if dirty:
                    curve = (parse_fan_curve(self.fan_curve.toPlainText())
                             if mode == "curve" else old_fan.get("curve"))
                    fan = complete_fan_settings(
                        old_fan, self.stats, mode=mode,
                        speed_percent=self.fan_speed.value(), curve=curve)
                    if mode == "curve":
                        fan["temperature_key"] = self.fan_temperature.currentData()
                    overrides["fan_control_settings"] = fan
        config = merged_gpu_config(self.current_config, overrides)
        advanced = json.loads(self.extra.toPlainText() or "{}")
        if not isinstance(advanced, dict):
            raise ValueError("Erweiterte Optionen müssen ein JSON-Objekt sein.")
        handled = {"power_cap", "performance_level", "fan_control_enabled",
                   "fan_control_settings", "gpu_clock_offsets", *CLOCK_FIELDS}
        if handled.intersection(advanced):
            raise ValueError("Erweiterte Option überschreibt eine reguläre Einstellung.")
        for key in tuple(config):
            if key not in handled and key not in advanced:
                del config[key]
        config.update(advanced)
        return config

    def _apply(self):
        if not self.gpu_id or self.pending:
            return
        try:
            config = self._collect()
            if config == self.current_config:
                self.status.setText("Keine Änderungen vorhanden")
                return
            if QMessageBox.question(self, "GPU-Tuning", 
                    "GPU-Einstellungen jetzt testen? Nicht bestätigte Änderungen werden automatisch zurückgesetzt.") != QMessageBox.Yes:
                return
            seconds = self.client.set_gpu_config(self.gpu_id, config)
            self.pending = True
            # LACT's daemon performs the real rollback. Keep this UI timer shorter
            # than the default daemon confirmation window; do not auto-confirm.
            try:
                timeout = float(seconds)
            except (TypeError, ValueError):
                timeout = 5.0
            self.confirm_timer.start(max(300, round((timeout - 0.7) * 1000)))
            self._set_access(True)
            self.status.setText("Änderung aktiv: Bitte sofort bestätigen oder zurücksetzen.")
        except (LactError, ValueError, TypeError) as exc:
            self._error(exc)

    def _confirm(self):
        if not self.pending:
            return
        try:
            self.client.confirm()
            self.pending = False
            self.confirm_timer.stop()
            self._device_selected()
            self.status.setText("GPU-Einstellungen von Vitalux bestätigt und gespeichert")
        except LactError as exc:
            self._error(exc)

    def _revert(self):
        if not self.pending:
            return
        try:
            self.client.revert()
        except LactError as exc:
            self._error(exc)
        finally:
            self.pending = False
            self.confirm_timer.stop()
            self._device_selected()

    def _expired(self):
        self.pending = False
        self.status.setText("Bestätigungszeit abgelaufen. Vitalux setzt unbestätigte Änderungen zurück.")
        self._device_selected()
