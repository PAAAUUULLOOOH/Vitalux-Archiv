"""Read-only system monitoring helpers for Vitalux.

No privileged tools, changes to hardware settings, or fabricated sensor values.
All history is in-memory and bounded to the current application session.
"""
from __future__ import annotations

from datetime import datetime
import json
import math

METRICS = ("cpu_usage", "cpu_temp", "gpu_usage", "gpu_temp", "gpu_clock",
           "gpu_power", "ram_usage")


def valid_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


class SessionExtrema:
    """Minimum and maximum of actual sampled values since startup/reset."""

    def __init__(self):
        self.values = {}
        self.started_at = datetime.now().astimezone().isoformat()

    def update(self, sample):
        cpu = sample.get("cpu") or {}
        ram = sample.get("ram") or {}
        gpu = next(iter(sample.get("gpus") or ()), {})
        values = {
            "cpu_usage": cpu.get("usage"),
            "cpu_temp": cpu.get("temp"),
            "gpu_usage": gpu.get("usage"),
            "gpu_temp": gpu.get("temp"),
            "gpu_clock": gpu.get("clock"),
            "gpu_power": gpu.get("power"),
            "ram_usage": ram.get("percent"),
        }
        for key, number in values.items():
            if not valid_number(number):
                continue
            low, high = self.values.get(key, (number, number))
            self.values[key] = (min(low, number), max(high, number))
        return self.snapshot()

    def snapshot(self):
        return {name: list(pair) for name, pair in self.values.items()}

    def reset(self):
        self.values.clear()
        self.started_at = datetime.now().astimezone().isoformat()


def format_range(values, key, unit="%", digits=0):
    pair = values.get(key)
    if (not isinstance(pair, (tuple, list)) or len(pair) != 2
            or not all(valid_number(n) for n in pair)):
        return "–"
    return f"{pair[0]:.{digits}f}–{pair[1]:.{digits}f} {unit}"


def pcie_speed(value):
    """Do not confuse GT/s (PCIe signaling) with GB/s throughput."""
    if not value:
        return "–"
    data = str(value).strip()
    return data if "GT/s" in data else data


def pcie_link(current_speed, current_width, max_speed, max_width):
    def display(speed, width):
        if not speed or not width:
            return "–"
        try:
            lanes = int(str(width).lower().removeprefix("x"))
        except (ValueError, TypeError):
            return "–"
        return f"{pcie_speed(speed)} · x{lanes}" if lanes > 0 else "–"
    return display(current_speed, current_width), display(max_speed, max_width)


def hardware_status(sample, limits=None):
    """Neutral, factual sensor status; missing readings are *never* safe/healthy."""
    limits = limits or {}
    c = sample.get("cpu") or {}
    r = sample.get("ram") or {}
    gpu = (sample.get("gpus") or [{}])[0]
    values = (
        ("CPU", c.get("temp"), limits.get("cpu_temp", 90), "°C"),
        ("GPU", gpu.get("temp"), limits.get("gpu_temp", 90), "°C"),
        ("RAM", r.get("percent"), limits.get("ram_usage", 90), "%"),
    )
    result = []
    for name, reading, threshold, unit in values:
        if not valid_number(reading) or not valid_number(threshold):
            result.append((name, "Nicht verfügbar"))
        elif reading >= threshold:
            result.append((name, f"Warnwert erreicht: {reading:.0f}{unit}"))
        else:
            result.append((name, f"{reading:.0f}{unit} · unter Warnwert"))
    disks = sample.get("disks") or []
    root = next((disk for disk in disks if disk.get("mount") == "/"), None)
    if root and valid_number(root.get("percent")):
        usage = root["percent"]
        threshold = limits.get("disk_usage", 95)
        result.append(("Systemlaufwerk",
                       f"Warnwert erreicht: {usage:.0f}%" if valid_number(threshold) and usage >= threshold
                       else f"{usage:.0f}% belegt"))
    else:
        result.append(("Systemlaufwerk", "Nicht verfügbar"))
    return result


def report_data(sample, static, version, extrema=None):
    """Produce a self-contained opt-in report without external I/O."""
    return {
        "application": "Vitalux",
        "version": version,
        "created_at": datetime.now().astimezone().isoformat(),
        "system": static,
        "sample": sample,
        "min_max_since_start": extrema or {},
        "note": "Sensordaten stammen aus verfügbaren Linux-Schnittstellen. "
                "Fehlende Werte sind nicht verfügbar.",
    }


def report_text(data):
    lines = [
        f"Vitalux · Systembericht · Version {data['version']}",
        f"Erstellt: {data['created_at']}",
        "",
        "SYSTEM",
    ]
    for key, value in (data.get("system") or {}).items():
        lines.append(f"{key}: {value}")
    lines += ["", "HARDWARE UND SENSOREN"]
    sample = data.get("sample") or {}
    for name in ("cpu", "ram", "gpus", "disks", "net", "io"):
        lines.append(f"{name}: {json.dumps(sample.get(name), ensure_ascii=False, default=str)}")
    lines += ["", "MINIMUM / MAXIMUM"]
    for name, bounds in (data.get("min_max_since_start") or {}).items():
        lines.append(f"{name}: {bounds}")
    lines += ["", str(data.get("note", ""))]
    return "\n".join(lines) + "\n"


def write_report(path, data):
    path = str(path)
    with open(path, "w", encoding="utf-8") as target:
        if path.lower().endswith(".json"):
            json.dump(data, target, ensure_ascii=False, indent=2, default=str)
        elif path.lower().endswith(".txt"):
            target.write(report_text(data))
        else:
            raise ValueError("Unterstützte Berichtsformate: .txt oder .json")
