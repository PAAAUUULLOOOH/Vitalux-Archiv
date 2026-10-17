"""User-controlled nonintrusive telemetry threshold notifications.

No system calls. False/missing readings are never treated as zero temperatures.
Each metric latches until values return below the threshold - hysteresis.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Alert:
    metric: str
    value: float
    limit: float
    unit: str


class AlertMonitor:
    def __init__(self):
        self._active = set()

    def update(self, readings, limits, enabled):
        if not enabled:
            self._active.clear()
            return []
        triggered = []
        for metric, (value, unit) in readings.items():
            limit = limits.get(metric)
            if value is None or limit is None:
                continue
            try:
                value, limit = float(value), float(limit)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value) or not math.isfinite(limit):
                continue
            if value >= limit:
                if metric not in self._active:
                    self._active.add(metric)
                    triggered.append(Alert(metric, value, limit, unit))
            elif value <= limit - (3 if unit == '°C' else 4):
                self._active.discard(metric)
        return triggered


def readings_from_sample(sample):
    cpu = sample.get('cpu') or {}
    gpu_temperatures = []
    for gpu in sample.get('gpus') or []:
        try:
            temperature = float(gpu.get('temp'))
            if math.isfinite(temperature):
                gpu_temperatures.append(temperature)
        except (TypeError, ValueError, AttributeError):
            continue
    hottest_gpu = max(gpu_temperatures) if gpu_temperatures else None
    root = next((v for v in sample.get('disks', []) if v.get('mount') == '/'), None)
    ram = sample.get('ram') or {}
    return {
        'cpu_temp': (cpu.get('temp'), '°C'),
        'gpu_temp': (hottest_gpu, '°C'),
        'ram_usage': (ram.get('percent'), '%'),
        'disk_usage': ((root or {}).get('percent'), '%'),
    }
