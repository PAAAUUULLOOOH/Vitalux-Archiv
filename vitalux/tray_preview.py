"""Real live sensor summaries for KDE's tray tooltip and a compact Qt popup."""
import math
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)
from . import theme
from .i18n import tr


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def percent(value):
    value = number(value)
    return '–' if value is None else f'{value:.0f}%'


def temperature(value):
    value = number(value)
    return '–' if value is None else f'{value:.0f} °C'


def measurements(sample):
    sample = sample or {}
    cpu = sample.get('cpu') or {}
    ram = sample.get('ram') or {}
    gpu = next((g for g in (sample.get('gpus') or []) if isinstance(g, dict)), {})
    return (number(cpu.get('usage')), number(gpu.get('usage')),
            number(ram.get('percent')), number(cpu.get('temp')),
            number(gpu.get('temp')))


def tray_tooltip(sample):
    cpu, gpu, ram, cpu_temp, gpu_temp = measurements(sample)
    return ('Vitalux · ' + tr('Live-Übersicht') + '\n'
            + f'CPU {percent(cpu)}  ·  GPU {percent(gpu)}\n'
            + f'RAM {percent(ram)}\n'
            + f'{tr("CPU-Temperatur")}: {temperature(cpu_temp)}\n'
            + f'{tr("GPU-Temperatur")}: {temperature(gpu_temp)}')


class TrayPreview(QWidget):
    """Optional popup for Wayland hosts that only show a native tooltip on hover."""
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.setObjectName('vitaluxTrayPreview')
        self.setFixedWidth(318)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 15, 18, 17)
        outer.setSpacing(10)
        header = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName('trayHeading')
        header.addWidget(self.heading, 1)
        close = QPushButton('×')
        close.setFixedSize(28, 28)
        close.clicked.connect(self.hide)
        header.addWidget(close)
        outer.addLayout(header)
        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        self.values = {}
        self.bars = {}
        for i, key in enumerate(('CPU', 'GPU', 'RAM')):
            value = QLabel('–')
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setFixedHeight(9)
            bar.setTextVisible(False)
            grid.addWidget(QLabel(key), i * 2, 0)
            grid.addWidget(value, i * 2, 1)
            grid.addWidget(bar, i * 2 + 1, 0, 1, 2)
            self.values[key] = value
            self.bars[key] = bar
        outer.addLayout(grid)
        temperatures = QHBoxLayout()
        self.cpu_temp = QLabel('–')
        self.gpu_temp = QLabel('–')
        temperatures.addWidget(self.cpu_temp)
        temperatures.addStretch()
        temperatures.addWidget(self.gpu_temp)
        outer.addLayout(temperatures)
        self.retheme()

    def retheme(self):
        accent = theme.accent()
        self.setStyleSheet(
            f'QWidget#vitaluxTrayPreview {{ background: {theme.CARD}; '
            f'border: 1px solid {theme.BORDER}; border-radius: 14px; }}'
            f'QWidget#vitaluxTrayPreview QLabel {{ color: {theme.TEXT}; border: 0; }}'
            'QLabel#trayHeading { font-size: 16px; font-weight: 800; }'
            f'QWidget#vitaluxTrayPreview QProgressBar {{ background: {theme.TRACK}; '
            'border: none; border-radius: 4px; }}'
            f'QWidget#vitaluxTrayPreview QProgressBar::chunk {{ background: {accent}; '
            'border-radius: 4px; }}'
            f'QWidget#vitaluxTrayPreview QPushButton {{ background: transparent; '
            f'color: {theme.TEXT}; border: none; font-size: 20px; }}')
        self.heading.setText('Vitalux · ' + tr('Live-Übersicht'))

    def update_sample(self, sample):
        cpu, gpu, ram, cpu_temp, gpu_temp = measurements(sample)
        for key, value in (('CPU', cpu), ('GPU', gpu), ('RAM', ram)):
            self.values[key].setText(percent(value))
            self.bars[key].setValue(0 if value is None else max(0, min(100, round(value))))
        self.cpu_temp.setText('CPU  ' + temperature(cpu_temp))
        self.gpu_temp.setText('GPU  ' + temperature(gpu_temp))
