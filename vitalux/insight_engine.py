"""Opt-in, read-only analysis for Vitalux's performance laboratory.

All results come from sampled sensor data. Diagnostic findings are hypotheses,
not hardware diagnoses. No external services, privileged writes or network I/O.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import csv
import json
import math
import os
import tempfile
import statistics


FIELDS = ("cpu_usage", "cpu_temp", "gpu_usage", "gpu_temp", "gpu_clock",
          "gpu_power", "ram_usage", "vram_usage")


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def telemetry(sample):
    cpu = sample.get("cpu") or {}
    ram = sample.get("ram") or {}
    gpu = next(iter(sample.get("gpus") or []), {})
    used, total = gpu.get("vram_used"), gpu.get("vram_total")
    return {
        "cpu_usage": cpu.get("usage"),
        "cpu_temp": cpu.get("temp"),
        "gpu_usage": gpu.get("usage"),
        "gpu_temp": gpu.get("temp"),
        "gpu_clock": gpu.get("clock"),
        "gpu_power": gpu.get("power"),
        "ram_usage": ram.get("percent"),
        "vram_usage": 100 * used / total if number(used) and number(total) and total > 0 else None,
    }


def _present(v, unit="", digits=1):
    return f"{v:.{digits}f}{unit}" if number(v) else "nicht verfügbar"


def findings(snapshot, recent=(), limits=None):
    """Return evidence-backed observations. NEVER infer definitive bottlenecks."""
    limits = limits or {}
    d = telemetry(snapshot)
    out = []
    if number(d["gpu_usage"]) and d["gpu_usage"] >= 95:
        out.append(("GPU-Auslastung hoch", "Die Grafikkarte ist aktuell stark ausgelastet. "
                    "Ein GPU-Limit ist möglich; ohne FPS-/Frametime-Daten nicht sicher bestimmbar.", "info"))
    if number(d["vram_usage"]) and d["vram_usage"] >= 90:
        out.append(("Videospeicher fast voll", f"{d['vram_usage']:.0f}% des VRAM sind belegt. "
                    "Stottern ist möglich, aber damit allein nicht nachgewiesen.", "warning"))
    for key, title, threshold, unit in (
        ("cpu_temp", "CPU-Temperatur", limits.get("cpu_temp", 90), "°C"),
        ("gpu_temp", "GPU-Temperatur", limits.get("gpu_temp", 90), "°C"),
    ):
        if number(d[key]) and number(threshold) and d[key] >= threshold:
            out.append((title, f"{d[key]:.1f}{unit} liegen am oder über dem eingestellten Warnwert "
                        f"({_present(threshold, unit)}).", "warning"))
    clocks = [telemetry(s).get("gpu_clock") for s in recent if isinstance(s, dict)]
    clocks = [v for v in clocks if number(v) and v > 0]
    if len(clocks) >= 10 and number(d["gpu_usage"]) and d["gpu_usage"] >= 85:
        prior = max(clocks)
        if number(d["gpu_clock"]) and prior and d["gpu_clock"] < prior * .7:
            out.append(("GPU-Takt gefallen", f"Der Takt liegt aktuell deutlich unter einem jüngsten "
                        f"Messwert ({_present(d['gpu_clock'], ' MHz', 0)} gegenüber "
                        f"{_present(prior, ' MHz', 0)}). Energiesparen und Lastwechsel "
                        "können dies ebenfalls erklären.", "info"))
    if not any(number(d[k]) for k in ("gpu_usage", "gpu_temp", "gpu_clock")):
        out.append(("GPU-Sensordaten fehlen", "Der aktuelle Treiber liefert keine ausreichenden "
                    "GPU-Werte für eine Leistungsbewertung.", "muted"))
    if not out:
        out.append(("Keine Auffälligkeiten", "Die verfügbaren Messwerte liegen derzeit "
                    "unter den beobachteten Warnschwellen. Das ist keine Hardwarediagnose.", "muted"))
    return out[:6]


class MonitoringLab:
    """One lightweight bounded stream used by detective, timeline and gaming."""
    def __init__(self, max_samples=3600, snapshot_path=None):
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self.recent = deque(maxlen=20)
        self.history = deque(maxlen=max_samples)
        self.events = deque(maxlen=300)
        self.prev = {}
        self.started = None
        self.session = deque(maxlen=900)
        self.session_count = 0
        self.session_aggregates = {}
        self.session_name = ""
        self.last_session = None
        self.snapshots = [None, None]
        self.mangohud = None
        self._load_snapshots()

    @staticmethod
    def _now():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def ingest(self, sample, limits=None, timestamp=None):
        if not isinstance(sample, dict):
            return
        now = timestamp or self._now()
        current = telemetry(sample)
        row = {"time": now, "metrics": current}
        self.history.append(row)
        self.recent.append(sample)
        if self.started is not None:
            self.session.append(row)
            self.session_count += 1
            for key in FIELDS:
                value = current.get(key)
                if not number(value):
                    continue
                record = self.session_aggregates.get(key)
                if record is None:
                    record = self.session_aggregates[key] = {
                        "count": 0, "sum": 0.0, "min": value, "max": value}
                record["count"] += 1
                record["sum"] += value
                record["min"] = min(record["min"], value)
                record["max"] = max(record["max"], value)
        limits = limits or {}
        checks = (
            ("cpu_temp", "CPU-Temperatur überschreitet Warnwert", limits.get("cpu_temp", 90)),
            ("gpu_temp", "GPU-Temperatur überschreitet Warnwert", limits.get("gpu_temp", 90)),
            ("ram_usage", "RAM-Auslastung überschreitet Warnwert", limits.get("ram_usage", 90)),
            ("vram_usage", "Videospeicher über 90 %", 90),
            ("gpu_usage", "GPU-Auslastung über 95 %", 95),
        )
        for key, title, limit in checks:
            v = current[key]
            prev = self.prev.get(key)
            if number(v) and number(limit) and v >= limit and not (number(prev) and prev >= limit):
                self.events.appendleft({"time": now, "title": title,
                                        "detail": f"{v:.1f}% " if key.endswith("usage") else f"{v:.1f} °C",
                                        "metrics": dict(current)})
            if key in ("gpu_temp", "gpu_usage") and not number(v) and number(prev):
                self.events.appendleft({"time": now, "title": "GPU-Sensor ausgefallen",
                                        "detail": key, "metrics": dict(current)})
        self.prev = current

    def detective(self, limits=None):
        if not self.recent:
            return [("Noch keine Messungen", "Vitalux wartet auf Sensordaten.", "muted")]
        return findings(self.recent[-1], self.recent, limits)

    def start_session(self, name="Gaming-Sitzung"):
        if self.started is not None:
            raise ValueError("Eine Aufzeichnung läuft bereits.")
        self.session_name = (name or "Gaming-Sitzung").strip()[:80]
        self.started = self._now()
        self.session = deque(maxlen=900)
        self.session_count = 0
        self.session_aggregates = {}
        self.last_session = None
        self.mangohud = None

    def stop_session(self):
        if self.started is None:
            raise ValueError("Es läuft keine Aufzeichnung.")
        self.last_session = self._summarize(self.session, self.session_name, self.started)
        self.last_session["samples"] = self.session_count
        self.last_session["metrics"] = {
            key: {"avg": round(record["sum"] / record["count"], 2),
                  "min": record["min"], "max": record["max"]}
            for key, record in self.session_aggregates.items()
        }
        self.started = None
        self.session = deque(maxlen=900)
        return self.last_session

    @staticmethod
    def _summarize(rows, name, start):
        summary = {"name": name, "started": start, "ended": MonitoringLab._now(),
                   "samples": len(rows), "metrics": {}}
        for field in FIELDS:
            values = [row["metrics"].get(field) for row in rows]
            values = [v for v in values if number(v)]
            if values:
                summary["metrics"][field] = {"avg": round(statistics.fmean(values), 2),
                                             "min": min(values), "max": max(values)}
        return summary

    def _load_snapshots(self):
        if self.snapshot_path is None:
            return
        try:
            if self.snapshot_path.stat().st_size > 30000:
                return
            data = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            entries = data.get("snapshots") if isinstance(data, dict) else None
            if isinstance(entries, list) and len(entries) == 2:
                for i, entry in enumerate(entries):
                    if (isinstance(entry, dict) and isinstance(entry.get("metrics"), dict)
                            and isinstance(entry.get("time"), str)):
                        self.snapshots[i] = entry
        except (OSError, ValueError, TypeError):
            return

    def _save_snapshots(self):
        if self.snapshot_path is None:
            return
        path = self.snapshot_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=".insights-", dir=path.parent)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "snapshots": self.snapshots}, handle,
                          ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass

    def snapshot(self, slot, sample):
        if slot not in (0, 1) or not isinstance(sample, dict):
            raise ValueError("Ungültiger Vergleichsschnappschuss.")
        self.snapshots[slot] = {"time": self._now(), "metrics": telemetry(sample),
                                "gpu": ((sample.get("gpus") or [{}])[0]).get("name") or "–"}
        self._save_snapshots()

    def comparison(self):
        a, b = self.snapshots
        if not a or not b:
            return []
        if a.get("gpu") != b.get("gpu"):
            return []
        out = []
        for key in FIELDS:
            x, y = a["metrics"].get(key), b["metrics"].get(key)
            if number(x) and number(y):
                out.append((key, round(x, 2), round(y, 2), round(y - x, 2)))
        return out

    def export_session(self, path):
        if not self.last_session:
            raise ValueError("Noch keine abgeschlossene Gaming-Sitzung.")
        with open(path, "w", encoding="utf-8") as target:
            json.dump({"application": "Vitalux", "session": self.last_session,
                       "mangohud": self.mangohud}, target, ensure_ascii=False, indent=2)

    def import_mangohud(self, path, max_bytes=20_000_000, max_rows=150000):
        """Opt-in MangoHud CSV parser; strict size/row limits for responsive GUI.

        fps values are sourced from logs, never estimated from hardware load.
        1%-low is an approximate worst-1%-of-samples mean, not a frame-perfect
        1% low unless every frame is independently represented.
        """
        path = Path(path)
        if path.stat().st_size > max_bytes:
            raise ValueError("MangoHud-Protokoll zu groß (maximal 20 MB).")
        fps, frames = [], []
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
            # MangoHud CSV has optional metadata lines before the column header.
            header = None
            for _ in range(40):
                line = source.readline()
                if not line:
                    break
                names = [name.strip().lower() for name in next(csv.reader([line]))]
                if "fps" in names or "frametime" in names:
                    header = names
                    break
            if not header:
                raise ValueError("MangoHud-Spalten fps/frametime nicht gefunden.")
            for idx, row in enumerate(csv.reader(source)):
                if idx >= max_rows:
                    break
                if not row or len(row) != len(header):
                    continue
                data = dict(zip(header, row))
                try:
                    v = float(data.get("fps") or "nan")
                    ft = float(data.get("frametime") or "nan")
                except ValueError:
                    continue
                if number(v) and 1 <= v <= 2000:
                    fps.append(v)
                if number(ft) and .05 <= ft <= 10000:
                    frames.append(ft)
        if not fps and not frames:
            raise ValueError("Keine gültigen FPS-/Frametime-Werte gefunden.")
        result = {"source": path.name, "samples": len(fps) or len(frames)}
        if fps:
            result.update(avg_fps=round(statistics.fmean(fps), 1),
                          one_percent_low_approx=round(statistics.fmean(
                              sorted(fps)[:max(1, math.ceil(len(fps) * .01))]), 1))
        if frames:
            result["avg_frametime_ms"] = round(statistics.fmean(frames), 2)
            result["p99_frametime_ms"] = round(sorted(frames)[min(
                len(frames)-1, math.ceil(len(frames) * .99)-1)], 2)
        self.mangohud = result
        return result
