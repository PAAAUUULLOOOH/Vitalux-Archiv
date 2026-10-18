"""Native Vitalux tuning panel backed by the original LACT daemon."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from copy import deepcopy

from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QInputDialog, QLineEdit,
                              QSpinBox, QDoubleSpinBox, QPlainTextEdit, QWidget,
                              QVBoxLayout, QGroupBox, QMenu)

from .ui_locale import QPushButton, QComboBox, QMessageBox, QCheckBox
from .widgets import Card, label
from .lact_client import (LactClient, LactError, CLOCK_FIELDS, merged_gpu_config,
                          parse_fan_curve, format_fan_curve)
from .i18n import tr


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
        devices = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._device_selected)
        self.connect_button = QPushButton("Aktualisieren")
        self.connect_button.clicked.connect(self.reload)
        devices.addWidget(label("Grafikkarte"))
        devices.addWidget(self.device_combo, 1)
        devices.addWidget(self.connect_button)
        self.body.addLayout(devices)

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
        self.body.addLayout(profiles)
        self.auto = QCheckBox("Profile automatisch wechseln")
        self.auto.clicked.connect(self._change_auto)
        self.body.addWidget(self.auto)

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
        self.body.addLayout(rule)

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
            self.fields[key] = widget
            self.form.addRow(label(title), widget)
        self.performance = QComboBox()
        for title, value in (("Treiberstandard", None), ("Automatisch", "auto"), ("Niedrig", "low"),
                             ("Hoch", "high"), ("Manuell", "manual")):
            self.performance.addItem(title, value)
        self.form.addRow(label("Leistungsprofil"), self.performance)
        self.body.addLayout(self.form)

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
        self.body.addLayout(fan_row)
        self.body.addWidget(label("Lüfterkurve · Temperatur °C: Drehzahl %", "muted"))
        self.fan_curve = QPlainTextEdit()
        self.fan_curve.setMaximumHeight(116)
        self.fan_curve.setPlaceholderText("40: 30\n50: 35\n60: 50\n70: 75\n80: 100")
        self.body.addWidget(self.fan_curve)

        self.body.addWidget(label("Experten-Einstellungen (JSON)", "muted"))
        self.extra = QPlainTextEdit()
        self.extra.setMaximumHeight(110)
        self.extra.setToolTip("Erweiterte GPU-Konfiguration; bestehende Einstellungen bleiben erhalten.")
        self.body.addWidget(self.extra)
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
        self._set_access(False)
        self._first_show = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(0, self.reload)

    def _set_access(self, available):
        for widget in (self.profile_combo, self.load_btn, self.create_btn, self.delete_btn,
                       self.auto, self.rule_type, self.rule_process, self.rule_save,
                       self.performance, self.fan_enabled, self.fan_mode, self.fan_speed,
                       self.fan_curve, self.extra, *self.fields.values()):
            widget.setEnabled(available and not self.pending)
        if available and not self.pending:
            for key, widget in self.fields.items():
                widget.setEnabled(self.capabilities.get(key, True))
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
        installer = root / "packaging" / "vitalux-gpu-service.py"
        engine = root / "bin" / "vitalux-gpu-engine"
        if not installer.is_file() or not engine.is_file():
            self._error("Die Vitalux-GPU-Steuerung fehlt im Programm-Paket. "
                        "Bitte die vollständige neue Vitalux-Version verwenden.")
            return
        self.setup_button.setEnabled(False)
        self.status.setText("Vitalux GPU-Steuerung wird eingerichtet. Administratorabfrage öffnen.")
        process = QProcess(self)
        self.setup_process = process
        process.finished.connect(self._setup_finished)
        process.start(shutil.which("pkexec"), ["/usr/bin/python3", str(installer), "--install"])

    def _setup_finished(self, code, _status):
        process = self.setup_process
        if process is None:
            return
        error_text = bytes(process.readAllStandardError()).decode("utf-8", "replace").strip()
        process.deleteLater()
        self.setup_process = None
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
            self._load_fields()
            self._load_profiles()
            self.status.setText("Vitalux GPU-Steuerung aktiv · Einstellungen verfügbar")
            self._set_access(True)
        except (LactError, ValueError) as exc:
            self._set_access(False)
            self.status.setText(str(exc))

    def _detect_capabilities(self, clocks):
        """Gate direct editing by hardware information returned by LACT."""
        cap = self.capabilities = {}
        table = clocks.get("table") if isinstance(clocks, dict) else None
        for key in CLOCK_FIELDS:
            cap[key] = isinstance(table, dict)
        stats = self.stats if isinstance(self.stats, dict) else {}
        power = stats.get("power") or {}
        if not isinstance(power, dict):
            power = {}
        cap["power_cap"] = any(power.get(k) is not None
                               for k in ("cap_min", "cap_max", "cap_current"))
        fan = stats.get("fan") or {}
        cap["fan"] = isinstance(fan, dict) and (
            fan.get("speed_max") is not None or
            fan.get("pwm_max") is not None or fan.get("control_enabled") is True)
        device_name = (self.device_combo.currentText() or "").lower()
        if "nvidia" in device_name or "geforce" in device_name:
            cap["voltage_offset"] = False
            cap["min_voltage"] = False
            cap["max_voltage"] = False
        else:
            cap["voltage_boost"] = False

    def _load_fields(self):
        config = self.current_config
        power = (self.stats.get("power") or {}) if isinstance(self.stats, dict) else {}
        if isinstance(power, dict):
            lo, hi = power.get("cap_min"), power.get("cap_max")
            if lo is not None and hi is not None and 0 < lo < hi:
                self.fields["power_cap"].setRange(float(lo), float(hi))
        for key, widget in self.fields.items():
            value = config.get(key)
            widget.setValue(value if value is not None else widget.minimum())
            widget.setProperty("lact_null", value is None)
            # Spinboxes have explicit clear-to-default via context menu.
            widget.setToolTip("Wert einstellen. Mit 'Zurücksetzen' im Kontextmenü wieder auf Standard.")
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            try:
                widget.customContextMenuRequested.disconnect()
            except (RuntimeError, TypeError):
                pass
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_clear_menu(w, pos))
            try:
                widget.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            widget.valueChanged.connect(lambda _v, w=widget: w.setProperty("lact_null", False))
        performance = self.performance.findData(config.get("performance_level"))
        self.performance.setCurrentIndex(max(0, performance))
        self.fan_enabled.setChecked(bool(config.get("fan_control_enabled", False)))
        settings = config.get("fan_control_settings") or {}
        self.fan_mode.setCurrentIndex(max(0, self.fan_mode.findData(settings.get("mode", "curve"))))
        self.fan_speed.setValue(round(float(settings.get("static_speed", 0.5)) * 100))
        self.fan_curve.setPlainText(format_fan_curve(settings.get("curve")))
        handled = {"power_cap", "performance_level", "fan_control_enabled",
                   "fan_control_settings", *CLOCK_FIELDS}
        self.extra.setPlainText(json.dumps(
            {k: v for k, v in config.items() if k not in handled},
            ensure_ascii=False, indent=2))

    def _toggle_fan_controls(self, *_):
        enabled = not self.pending and self.capabilities.get("fan", False)
        for widget in (self.fan_mode, self.fan_speed, self.fan_curve):
            widget.setEnabled(enabled and self.fan_enabled.isChecked())
        if enabled and self.fan_enabled.isChecked():
            self.fan_speed.setEnabled(self.fan_mode.currentData() == "static")
            self.fan_curve.setEnabled(self.fan_mode.currentData() == "curve")

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
                dirty = (
                    not self.current_config.get("fan_control_enabled")
                    or mode != old_fan.get("mode", "curve")
                    or (mode == "static" and self.fan_speed.value() != old_speed)
                    or (mode == "curve" and self.fan_curve.toPlainText()
                        != format_fan_curve(old_fan.get("curve")))
                )
                if dirty:
                    fan = deepcopy(old_fan)
                    fan["mode"] = mode
                    if mode == "static":
                        fan["static_speed"] = self.fan_speed.value() / 100.0
                    else:
                        fan["curve"] = parse_fan_curve(self.fan_curve.toPlainText())
                    overrides["fan_control_settings"] = fan
        config = merged_gpu_config(self.current_config, overrides)
        advanced = json.loads(self.extra.toPlainText() or "{}")
        if not isinstance(advanced, dict):
            raise ValueError("Erweiterte Optionen müssen ein JSON-Objekt sein.")
        handled = {"power_cap", "performance_level", "fan_control_enabled",
                   "fan_control_settings", *CLOCK_FIELDS}
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
