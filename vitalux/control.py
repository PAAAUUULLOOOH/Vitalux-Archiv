"""Hardware-sensor page, appearance settings and customizable dashboard controls."""
import json
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QGridLayout, QHBoxLayout, QInputDialog, QListWidget, QVBoxLayout, QWidget, QSpinBox)
from .ui_locale import QCheckBox, QComboBox, QDialog, QFileDialog, QListWidgetItem, QMessageBox, QPushButton

from . import __version__, settings, theme, motion
from .pages import Page
from .sensors import fmt_bytes, fmt_rate, system_static
from .widgets import Card, KeyValue, Meter, label
from .i18n import tr


class SensorsPage(Page):
    def __init__(self):
        super().__init__('Sensoren', 'Temperaturen, Lüfter und Spannungen · direkt aus Linux hwmon')
        self.cards = {}
        self.rows = {}
        for ident, title in [('temps', 'Temperaturen'), ('fans', 'Lüfter'), ('voltages', 'Spannungen'), ('powers', 'Leistungsaufnahme'), ('frequencies', 'Frequenzen')]:
            card = Card(title)
            self.cards[ident] = card
            self.rows[ident] = {}
            self.content.addWidget(card)
        self.message = label('', 'muted', wrap=True)
        self.content.addWidget(self.message)

    def refresh(self, d, h):
        sensors = d.get('sensors', {})
        count = 0
        for ident in ('temps', 'fans', 'voltages', 'powers', 'frequencies'):
            seen = set()
            entries = sensors.get(ident, [])
            for sensor in entries[:80]:
                key = sensor['name']
                seen.add(key)
                row = self.rows[ident].get(key)
                if row is None:
                    row = self.rows[ident][key] = KeyValue(key)
                    self.cards[ident].body.addWidget(row)
                val = sensor['value']
                unit = {'temps': '°C', 'fans': tr('U/min'), 'voltages': 'V', 'powers': 'W', 'frequencies': 'MHz'}[ident]
                if val is None:
                    row.set('–')
                else:
                    row.set(f'{val:.1f} {unit}' if ident != 'fans' else f'{val:.0f} {unit}')
                count += 1
            for key, widget in self.rows[ident].items():
                widget.setVisible(key in seen)
            self.cards[ident].setVisible(bool(entries))
        self.message.setText(tr('Keine zusätzlichen Sensoren verfügbar.') if not count else
            tr('Nicht jeder Sensor ist von jedem Mainboard/Grafiktreiber verfügbar; fehlende Werte werden nicht erfunden.'))


class PreferencesPage(Page):
    DEFAULTS = {
        'theme': 'glass', 'accent': 'auto', 'motion': 'smooth',
        'interval': 1, 'close_to_tray': True, 'alerts_enabled': False,
        'cpu_temp': 90, 'gpu_temp': 90, 'ram_usage': 90, 'disk_usage': 95,
    }

    def __init__(self, window):
        super().__init__('Einstellungen', 'Design, Messintervall, Dashboard und Datenexport')
        self.window = window
        look = Card('Erscheinungsbild')
        self.mode = QComboBox()
        for title, value in [('Dark', 'dark'), ('Light', 'light'), ('Glass', 'glass'), ('Black Glass', 'black_glass'), ('Minimalistisch', 'minimal')]:
            self.mode.addItem(title, value)
        self.mode.setCurrentIndex(max(0, self.mode.findData(theme.mode())))
        self.mode.currentIndexChanged.connect(self.change_mode)
        r = QHBoxLayout()
        r.addWidget(label('Farbschema', 'strong'))
        r.addWidget(self.mode)
        r.addStretch(1)
        look.body.addLayout(r)
        self.theme_note = label('', 'muted', wrap=True)
        self.theme_note.setObjectName('themeDescription')
        look.body.addWidget(self.theme_note)
        self.mode_notes = {
            'dark': 'Dark · Kontrastreiche, ruhige Flächen ohne Glasunschärfe.',
            'light': 'Light · Helle, gut lesbare Karten ohne Glaseffekt.',
            'glass': 'Glass · Halbtransparente Panels mit Lichtreflexen und weichgezeichnetem Hintergrund.',
            'black_glass': 'Black Glass · Tiefschwarze Glasflächen mit dezenten Reflexionen und silbernen Kanten.',
            'minimal': 'Minimalistisch · Einfache Flächen ohne Glas, Schatten und dekorative Animationen. Spart Zeichenaufwand.',
        }
        self.theme_note.setText(tr(self.mode_notes.get(theme.mode(), self.mode_notes['dark'])))
        r2 = QHBoxLayout()
        r2.addWidget(label('Akzentfarbe', 'strong'))
        accent = QComboBox()
        self.accent_combo = accent
        for title, value in [('Distribution', 'auto'), ('Vitalux Blau', '#4f8cff'),
            ('Cyan', '#52d3ff'), ('Violett', '#a78bfa'), ('Grün', '#73ba25'),
            ('Orange', '#f59e0b'), ('Rosa', '#f472b6')]:
            accent.addItem(title, value)
        self.custom_accents = self._read_custom_accents()
        stored = settings.get('accent', 'auto')
        if accent.findData(stored) < 0 and QColor(str(stored)).isValid():
            # Migrate the unnamed color from earlier Vitalux installations.
            if not any(item['color'] == QColor(stored).name() for item in self.custom_accents):
                self.custom_accents.append({'name': 'Eigene Farbe', 'color': QColor(stored).name()})
                settings.set('custom_accents', self.custom_accents)
        for item in self.custom_accents:
            if accent.findData(item['color']) < 0:
                accent.addItem(item['name'], item['color'])
        accent.setCurrentIndex(max(0, accent.findData(stored)))
        accent.currentIndexChanged.connect(lambda _: self.change_accent(accent.currentData()))
        r2.addWidget(accent)
        # Both actions appear only when a saved custom accent is selected.
        self.edit_custom_accent_button = QPushButton('Bearbeiten')
        self.edit_custom_accent_button.setObjectName('ghostBtn')
        self.edit_custom_accent_button.setCursor(Qt.PointingHandCursor)
        self.edit_custom_accent_button.setToolTip(tr('Ausgewählte eigene Farbe bearbeiten'))
        self.edit_custom_accent_button.clicked.connect(self.edit_custom_accent)
        r2.addWidget(self.edit_custom_accent_button)
        custom = QPushButton('Eigene Farbe …')
        custom.setObjectName('ghostBtn')
        custom.clicked.connect(lambda: self.custom_accent(accent))
        r2.addWidget(custom)
        self.remove_custom_accent_button = QPushButton('Löschen')
        self.remove_custom_accent_button.setObjectName('ghostBtn')
        self.remove_custom_accent_button.setCursor(Qt.PointingHandCursor)
        self.remove_custom_accent_button.setToolTip(tr('Ausgewählte eigene Farbe löschen'))
        self.remove_custom_accent_button.clicked.connect(self.remove_custom_accent)
        r2.addWidget(self.remove_custom_accent_button)
        r2.addStretch(1)
        look.body.addLayout(r2)
        self._sync_custom_accent_actions()
        look.body.addWidget(label('Akzentfarben gelten für Reiter, Kartenkanten, Kurven und Bedienelemente.', 'muted', wrap=True))
        self.accent_preview = QWidget()
        self.accent_preview.setMinimumHeight(14)
        self.accent_preview.setObjectName('accentPreview')
        self.accent_preview.setStyleSheet(f'background: {theme.accent()}; border-radius: 7px;')
        look.body.addWidget(self.accent_preview)
        # A presentation preference, not a global reduction of monitoring speed.
        # Runtime widgets read the profile on their next interaction.
        r_motion = QHBoxLayout()
        r_motion.addWidget(label('Animationen', 'strong'))
        self.motion_combo = QComboBox()
        for name, value in [('Flüssig', 'smooth'), ('Reduziert', 'reduced'), ('Aus', 'off')]:
            self.motion_combo.addItem(name, value)
        self.motion_combo.setCurrentIndex(max(0, self.motion_combo.findData(motion.level())))
        self.motion_combo.currentIndexChanged.connect(self.change_motion)
        r_motion.addWidget(self.motion_combo)
        r_motion.addStretch(1)
        look.body.addLayout(r_motion)
        look.body.addWidget(label('Übergänge anpassen: weich, verkürzt oder ohne Animation.', 'muted', wrap=True))
        self.content.addWidget(look)

        monitor = Card('Live-Monitoring')
        row = QHBoxLayout()
        row.addWidget(label('Aktualisierungsintervall', 'strong'))
        self.interval = QComboBox()
        for val in (1, 2, 5):
            self.interval.addItem(f'{val} Sekunde' if val == 1 else f'{val} Sekunden', val)
        self.interval.setCurrentIndex(max(0, self.interval.findData(settings.get('interval', 1))))
        self.interval.currentIndexChanged.connect(self.change_interval)
        row.addWidget(self.interval)
        row.addStretch()
        monitor.body.addLayout(row)
        monitor.body.addWidget(label('Die Diagramme bieten 60 Sekunden, 5 Minuten und 15 Minuten Verlauf sowie einzeln schaltbare Datenreihen.', 'muted', wrap=True))
        self.content.addWidget(monitor)
        tray = Card('Systemleiste')
        self.close_to_tray = QCheckBox('Fenster schließen → in Systemleiste weiterlaufen')
        self.close_to_tray.setChecked(bool(settings.get('close_to_tray', True)))
        self.close_to_tray.setEnabled(self.window._tray is not None)
        self.close_to_tray.toggled.connect(lambda enabled: self._set_preference('close_to_tray', enabled))
        tray.body.addWidget(self.close_to_tray)
        tray.body.addWidget(label('Ein Linksklick auf das Tray-Symbol öffnet Vitalux. Über das Kontextmenü kann Vitalux vollständig beendet werden.', 'muted', wrap=True))
        self.content.addWidget(tray)

        notifications = Card('Hardware-Warnungen')
        self.alert_toggle = QCheckBox('Grenzwert-Warnungen aktivieren')
        self.alert_toggle.setChecked(bool(settings.get('alerts_enabled', False)))
        self.alert_toggle.toggled.connect(lambda checked: self._set_preference('alerts_enabled', checked))
        notifications.body.addWidget(self.alert_toggle)
        notifications.body.addWidget(label('Warnungen erscheinen beim Überschreiten eines Grenzwerts. Erst nach Abkühlung oder sinkender Auslastung kann eine erneute Warnung erfolgen.', 'muted', wrap=True))
        threshold_grid = QGridLayout()
        # Keep the warning card size. Labels on the left; narrow, centered
        # numeric fields follow on the right, as requested.
        threshold_grid.setColumnStretch(0, 1)
        threshold_grid.setColumnStretch(1, 0)
        threshold_grid.setHorizontalSpacing(14)
        self.alert_boxes = {}
        self.alert_labels = {}
        for idx, (key, title, default, lo, hi, unit) in enumerate((
            ('cpu_temp', 'CPU-Temperatur', 90, 40, 110, '°C'),
            ('gpu_temp', 'GPU-Temperatur', 90, 40, 115, '°C'),
            ('ram_usage', 'RAM-Auslastung', 90, 50, 100, '%'),
            ('disk_usage', 'Systemlaufwerk-Belegung', 95, 50, 100, '%'),
        )):
            value = QSpinBox()
            value.setObjectName('alertThresholdSpin')
            value.setFixedWidth(112)
            value.setAlignment(Qt.AlignCenter)
            value.setRange(lo, hi)
            value.setSuffix(' ' + unit)
            value.setValue(int(settings.get(key, default)))
            value.valueChanged.connect(lambda v, k=key: self._set_preference(k, v))
            text = label(title, 'strong')
            threshold_grid.addWidget(text, idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            threshold_grid.addWidget(value, idx, 1, Qt.AlignRight)
            self.alert_boxes[key] = value
            self.alert_labels[key] = text
        notifications.body.addLayout(threshold_grid)
        self.content.addWidget(notifications)

        export = Card('Diagnose & Berichte')
        export.body.addWidget(label('Exportiert alle aktuell erfassten Messwerte in eine lokale JSON-Datei. Enthält auch Host- und Netzwerkangaben.', 'muted', wrap=True))
        btn = QPushButton('Systembericht exportieren …')
        btn.setObjectName('ghostBtn')
        btn.clicked.connect(self.export)
        export.body.addWidget(btn)
        diag_btn = QPushButton('Fehlerdiagnose exportieren …')
        diag_btn.setObjectName('ghostBtn')
        diag_btn.clicked.connect(self.export_diagnostics)
        export.body.addWidget(diag_btn)
        export.body.addWidget(label('Diagnoseberichte enthalten möglicherweise private Systemangaben. Sie werden nur lokal gespeichert, nicht automatisch versendet.', 'muted', wrap=True))
        self.content.addWidget(export)

        # Only visible when the *preferences* deviate from the original values.
        # Dashboard tile positions, update source and language are intentionally
        # not touched by this button.
        restore_row = QHBoxLayout()
        restore_row.addStretch(1)
        self.restore_button = QPushButton('Standardwerte wiederherstellen')
        self.restore_button.setObjectName('ghostBtn')
        self.restore_button.clicked.connect(self.restore_defaults)
        restore_row.addWidget(self.restore_button)
        self.content.addLayout(restore_row)
        self._refresh_restore_button()

    def _set_preference(self, key, value):
        settings.set(key, value)
        self._refresh_restore_button()

    def _refresh_restore_button(self):
        self.restore_button.setVisible(any(
            settings.get(key, default) != default
            for key, default in self.DEFAULTS.items()
        ))

    def restore_defaults(self):
        answer = QMessageBox.question(
            self, 'Vitalux',
            tr('Alle Anzeige-, Überwachungs- und Warnungseinstellungen auf die Standardwerte zurücksetzen? Dashboard-Anordnung und Sprache bleiben erhalten.'),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        # Update visible widgets without emitting change handlers or tearing
        # down pages: the user keeps the current scroll position.
        for key, default in self.DEFAULTS.items():
            settings.set(key, default)
        self.mode.blockSignals(True)
        self.mode.setCurrentIndex(self.mode.findData('glass'))
        self.mode.blockSignals(False)
        self.accent_combo.blockSignals(True)
        self.accent_combo.setCurrentIndex(self.accent_combo.findData('auto'))
        self.accent_combo.blockSignals(False)
        self.motion_combo.blockSignals(True)
        self.motion_combo.setCurrentIndex(self.motion_combo.findData('smooth'))
        self.motion_combo.blockSignals(False)
        self.interval.blockSignals(True)
        self.interval.setCurrentIndex(self.interval.findData(1))
        self.interval.blockSignals(False)
        self.close_to_tray.blockSignals(True)
        self.close_to_tray.setChecked(True)
        self.close_to_tray.blockSignals(False)
        self.alert_toggle.blockSignals(True)
        self.alert_toggle.setChecked(False)
        self.alert_toggle.blockSignals(False)
        for key, box in self.alert_boxes.items():
            box.blockSignals(True)
            box.setValue(self.DEFAULTS[key])
            box.blockSignals(False)
        self.window.set_interval(1)
        self.window.apply_appearance()
        self._refresh_restore_button()

    def refresh_appearance(self):
        self._sync_custom_accent_actions()
        self.theme_note.setText(tr(self.mode_notes.get(theme.mode(), self.mode_notes['dark'])))
        self.accent_preview.setStyleSheet(f'background: {theme.accent()}; border-radius: 7px;')

    def change_mode(self, *_):
        val = self.mode.currentData()
        settings.set('theme', val)
        self.window.apply_appearance()
        self._refresh_restore_button()

    def change_accent(self, val):
        if not val:
            return
        settings.set('accent', val)
        self._sync_custom_accent_actions()
        self.window.apply_appearance()
        self._refresh_restore_button()

    @staticmethod
    def _read_custom_accents():
        saved = settings.get('custom_accents', [])
        if not isinstance(saved, list):
            return []
        result, seen = [], set()
        for entry in saved[:60]:
            if not isinstance(entry, dict):
                continue
            color = QColor(str(entry.get('color', '')))
            name = str(entry.get('name', '')).strip()[:32]
            if color.isValid() and name and color.name() not in seen:
                result.append({'name': name, 'color': color.name()})
                seen.add(color.name())
        return result

    def _sync_custom_accent_actions(self):
        selected = self.accent_combo.currentData()
        own_color_selected = any(item['color'] == selected for item in self.custom_accents)
        self.edit_custom_accent_button.setVisible(own_color_selected)
        self.remove_custom_accent_button.setVisible(own_color_selected)

    @staticmethod
    def _unique_custom_accent_name(combo, requested, exclude_index=None):
        name = requested.strip()[:32] or tr('Eigene Farbe')
        taken = {combo.itemText(i).casefold() for i in range(combo.count())
                 if i != exclude_index}
        original, number = name, 2
        while name.casefold() in taken:
            name = f'{original[:25]} ({number})'
            number += 1
        return name

    def edit_custom_accent(self):
        """Edit name and/or color of the selected saved accent, keeping its slot."""
        combo = self.accent_combo
        index = combo.currentIndex()
        original_color = combo.currentData()
        entry = next((item for item in self.custom_accents
                      if item['color'] == original_color), None)
        if entry is None or index < 0:
            return
        updated = QColorDialog.getColor(
            QColor(original_color), self, tr('Eigene Farbe bearbeiten'))
        if not updated.isValid():
            return
        new_color = updated.name()
        # The color palette is a unique-keyed collection: don't steal another
        # preset's value or leave two identically keyed custom entries.
        if new_color != original_color and any(
                combo.itemData(i) == new_color for i in range(combo.count()) if i != index):
            QMessageBox.information(self, 'Vitalux', tr('Diese Akzentfarbe ist bereits vorhanden.'))
            return
        new_name, accepted = QInputDialog.getText(
            self, tr('Eigene Farbe bearbeiten'),
            tr('Wie soll diese Akzentfarbe heißen?'), text=entry['name'])
        if not accepted:
            return
        new_name = self._unique_custom_accent_name(combo, new_name, index)
        if new_color == original_color and new_name == entry['name']:
            return
        # Apply the edit as a single operation; do not accidentally add an
        # extra entry or switch to the distribution color along the way.
        combo.blockSignals(True)
        try:
            combo.setItemText(index, new_name)
            combo.setItemData(index, new_color)
        finally:
            combo.blockSignals(False)
        entry['color'], entry['name'] = new_color, new_name
        settings.set('custom_accents', self.custom_accents)
        self.change_accent(new_color)

    def remove_custom_accent(self):
        value = self.accent_combo.currentData()
        if not any(item['color'] == value for item in self.custom_accents):
            return
        self.custom_accents = [item for item in self.custom_accents if item['color'] != value]
        settings.set('custom_accents', self.custom_accents)
        idx = self.accent_combo.findData(value)
        if idx >= 0:
            self.accent_combo.removeItem(idx)
        self.accent_combo.setCurrentIndex(0)  # Distribution is a safe fallback.
        self.change_accent('auto')
        self._sync_custom_accent_actions()

    def custom_accent(self, combo):
        color = QColorDialog.getColor(QColor(theme.accent()), self, tr('Akzentfarbe wählen'))
        if not color.isValid():
            return
        value = color.name()
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return
        name, accepted = QInputDialog.getText(
            self, tr('Eigene Farbe benennen'),
            tr('Wie soll diese Akzentfarbe heißen?'), text=tr('Eigene Farbe'))
        if not accepted:
            return
        name = self._unique_custom_accent_name(combo, name)
        self.custom_accents.append({'name': name, 'color': value})
        settings.set('custom_accents', self.custom_accents)
        combo.addItem(name, value)
        combo.setCurrentIndex(combo.count()-1)
        self._sync_custom_accent_actions()

    def change_motion(self, *_):
        profile = self.motion_combo.currentData()
        if profile in motion.MODES:
            self._set_preference('motion', profile)

    def change_interval(self, *_):
        val = self.interval.currentData()
        if val:
            self._set_preference('interval', int(val))
            self.window.set_interval(int(val))

    def export_diagnostics(self):
        from .diagnostics import export_report
        filename, _ = QFileDialog.getSaveFileName(self, 'Fehlerbericht speichern',
             f'Vitalux-Diagnose-{datetime.now():%Y%m%d-%H%M%S}.json', 'JSON (*.json)')
        if not filename:
            return
        try:
            export_report(filename, include_errors=True, sample=self.window.last_sample)
        except OSError as exc:
            QMessageBox.warning(self, 'Vitalux', f'Export fehlgeschlagen: {exc}')
        else:
            QMessageBox.information(self, 'Vitalux', 'Fehlerbericht gespeichert.')

    def export(self):
        if not self.window.last_sample:
            QMessageBox.information(self, 'Vitalux', 'Warte auf die erste Messung.')
            return
        suggested = f'Vitalux-Bericht-{datetime.now():%Y%m%d-%H%M%S}.json'
        filename, _ = QFileDialog.getSaveFileName(self, 'Systembericht speichern', suggested, 'JSON (*.json)')
        if not filename:
            return
        data = {'app': 'Vitalux', 'version': __version__, 'captured': datetime.now().astimezone().isoformat(),
                'system': system_static(), 'sample': self.window.last_sample}
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except OSError as exc:
            QMessageBox.warning(self, 'Vitalux', f'Export fehlgeschlagen: {exc}')
        else:
            QMessageBox.information(self, 'Vitalux', 'Systembericht gespeichert.')
