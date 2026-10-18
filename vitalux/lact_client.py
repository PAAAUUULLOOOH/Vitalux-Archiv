"""Native local transport for LACT's original lactd GPU control engine.

The GPU configuration logic runs in LACT, not in Vitalux. Protocol:
https://github.com/ilya-zlobintsev/LACT/blob/master/docs/API.md

No shell commands, privilege escalation or remote TCP connections are used.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import socket


SOCKET_PATH = "/run/lactd.sock"
MAX_REPLY_BYTES = 4 * 1024 * 1024


class LactError(RuntimeError):
    """LACT is absent, inaccessible, or rejected the request."""


class LactClient:
    def __init__(self, socket_path=SOCKET_PATH, timeout=2.0):
        self.socket_path = socket_path
        self.timeout = timeout

    def request(self, command, args=None):
        payload = {"command": command}
        if args is not None:
            payload["args"] = args
        try:
            message = (json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                connection.connect(self.socket_path)
                connection.sendall(message)
                with connection.makefile("rb") as stream:
                    line = stream.readline(MAX_REPLY_BYTES + 1)
        except FileNotFoundError as exc:
            raise LactError("Vitalux GPU-Steuerung noch nicht eingerichtet.") from exc
        except PermissionError as exc:
            raise LactError("Vitalux GPU-Steuerung: Zugriff auf den Dienst verweigert.") from exc
        except (OSError, TimeoutError) as exc:
            raise LactError(f"Vitalux GPU-Verbindung fehlgeschlagen: {exc}") from exc
        if not line or len(line) > MAX_REPLY_BYTES:
            raise LactError("Die Vitalux GPU-Steuerung antwortet nicht korrekt.")
        try:
            response = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise LactError("Ungültige Antwort vom GPU-Steuerungsdienst.") from exc
        if not isinstance(response, dict) or response.get("status") not in ("ok", "error"):
            raise LactError("Unbekanntes Antwortformat der GPU-Steuerung.")
        if response["status"] == "error":
            data = response.get("data")
            if isinstance(data, dict):
                # Original backend often wraps Rust deserialization errors.
                description = data.get("description") or data.get("message")
                source = data.get("source")
                if isinstance(source, dict):
                    description = source.get("description") or description
                raise LactError(str(description or "GPU-Einstellung wurde abgelehnt."))
            raise LactError(str(data or "GPU-Einstellung wurde abgelehnt."))
        return response.get("data")

    def devices(self):
        data = self.request("list_devices")
        if not isinstance(data, list):
            raise LactError("Ungültige GPU-Geräteliste.")
        return [item for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]

    def gpu_config(self, gpu_id):
        data = self.request("get_gpu_config", {"id": gpu_id})
        # LACT returns null for an untouched GPU. In that case its actual
        # GpuConfig default is the empty JSON object.
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise LactError("Ungültige GPU-Konfiguration.")
        return data

    def device_stats(self, gpu_id):
        return self.request("device_stats", {"id": gpu_id})

    def device_clocks(self, gpu_id):
        return self.request("device_clocks_info", {"id": gpu_id})

    def set_gpu_config(self, gpu_id, config):
        if not isinstance(config, dict):
            raise ValueError("GPU-Konfiguration muss ein JSON-Objekt sein.")
        return self.request("set_gpu_config", {"id": gpu_id, "config": config})

    def confirm(self):
        return self.request("confirm_pending_config", {"command": "confirm"})

    def revert(self):
        return self.request("confirm_pending_config", {"command": "revert"})

    def profiles(self):
        data = self.request("list_profiles", {"include_state": True})
        if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
            raise LactError("Ungültige GPU-Profilantwort.")
        return data

    def select_profile(self, name=None, auto=False):
        return self.request("set_profile", {"name": name, "auto_switch": bool(auto)})

    def create_profile(self, name, base="default"):
        if not name or not name.strip():
            raise ValueError("Profilname darf nicht leer sein.")
        return self.request("create_profile", {"name": name.strip(), "base": base})

    def delete_profile(self, name):
        return self.request("delete_profile", {"name": name})

    def set_profile_rule(self, name, rule=None, hooks=None):
        return self.request("set_profile_rule", {
            "name": name, "rule": rule, "hooks": hooks or {}
        })


CLOCK_FIELDS = (
    "min_core_clock", "max_core_clock", "min_memory_clock", "max_memory_clock",
    "voltage_offset", "min_voltage", "max_voltage", "voltage_boost"
)


def merged_gpu_config(current, overrides):
    """Preserve every LACT field we do not explicitly edit (including future fields)."""
    if not isinstance(current, dict) or not isinstance(overrides, dict):
        raise ValueError("Ungültige Konfiguration.")
    updated = deepcopy(current)
    for key, value in overrides.items():
        if key not in ("power_cap", "performance_level", "fan_control_enabled",
                       "fan_control_settings", "gpu_clock_offsets", *CLOCK_FIELDS):
            raise ValueError(f"Nicht freigegebenes Einstellungsfeld: {key}")
        if key == "fan_control_enabled" and not isinstance(value, bool):
            raise ValueError("Ungültige Lüftersteuerung.")
        if key in CLOCK_FIELDS and value is not None and (type(value) is not int):
            raise ValueError(f"Ungültiger Takt-/Spannungswert: {key}")
        if key == "power_cap" and value is not None:
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError("Das Power-Limit muss positiv und endlich sein.")
        if key == "performance_level" and value not in ("auto", "low", "high", "manual", None):
            raise ValueError("Unbekannter Performance-Modus.")
        if key == "gpu_clock_offsets" and not (
            isinstance(value, dict) and all(
                isinstance(k, str) and k.isdecimal() and type(v) is int
                for k, v in value.items()
            )
        ):
            raise ValueError("Ungültige GPU-Takt-Offsets.")
        if key == "fan_control_settings" and value is not None and not isinstance(value, dict):
            raise ValueError("Ungültige Lüfterparameter.")
        updated[key] = deepcopy(value)
    return updated


def parse_fan_curve(text):
    """UI format: five newline-separated entries '40: 30' (degrees C : percent)."""
    points = {}
    for row in text.replace(";", "\n").splitlines():
        row = row.strip()
        if not row:
            continue
        if ":" not in row:
            raise ValueError("Lüfterkurve: bitte Temperatur:Prozent pro Zeile eingeben.")
        temperature, speed = row.split(":", 1)
        try:
            t = int(temperature.strip())
            s = float(speed.strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError("Lüfterkurve enthält keine gültigen Zahlen.") from exc
        if not 0 <= t <= 120 or not math.isfinite(s) or not 0 <= s <= 100:
            raise ValueError("Lüfterkurve: Temperatur 0–120 °C, Geschwindigkeit 0–100 %.")
        if str(t) in points:
            raise ValueError("Doppelte Temperatur in der Lüfterkurve.")
        points[str(t)] = s / 100
    if len(points) < 2:
        raise ValueError("Lüfterkurve benötigt mindestens zwei Stützpunkte.")
    ordered = sorted(points, key=lambda k: int(k))
    if any(points[ordered[i]] > points[ordered[i + 1]] for i in range(len(ordered) - 1)):
        raise ValueError("Die Lüftergeschwindigkeit darf bei steigender Temperatur nicht sinken.")
    return {key: points[key] for key in ordered}


def format_fan_curve(curve):
    if not isinstance(curve, dict):
        return "40: 30\n50: 35\n60: 50\n70: 75\n80: 100"
    try:
        return "\n".join(
            f"{int(t)}: {round(float(s) * 100):d}"
            for t, s in sorted(curve.items(), key=lambda pair: int(pair[0]))
        )
    except (TypeError, ValueError):
        return ""


DEFAULT_FAN_CURVE = {"40": .3, "50": .35, "60": .5, "70": .75, "80": 1.0}


def fan_temperature_sources(stats):
    """Return temperature sensor keys the original service allows for fan control."""
    if not isinstance(stats, dict):
        return ["edge"]
    temps = stats.get("temps") or {}
    if not isinstance(temps, dict):
        return ["edge"]
    choices = [name for name, row in temps.items()
               if isinstance(name, str) and isinstance(row, dict)
               and not row.get("display_only", False) and row.get("current") is not None]
    return choices or ["edge"]


def complete_fan_settings(current, stats, *, mode, speed_percent, curve):
    """Produce the complete required LACT 0.10.1 FanControlSettings schema.

    In addition to mode/speed/curve the service *requires* temperature_key
    and interval_ms, even for an initially unconfigured GPU.
    """
    if mode not in ("static", "curve"):
        raise ValueError("Unbekannter Lüftermodus.")
    if not isinstance(speed_percent, (int, float)) or isinstance(speed_percent, bool) or not math.isfinite(speed_percent) or not 0 <= speed_percent <= 100:
        raise ValueError("Lüftergeschwindigkeit muss zwischen 0 und 100 % liegen.")
    result = deepcopy(current) if isinstance(current, dict) else {}
    temps = fan_temperature_sources(stats)
    fan = stats.get("fan") or {} if isinstance(stats, dict) else {}
    if not isinstance(fan, dict):
        fan = {}
    sensor = result.get("temperature_key") or fan.get("temperature_key")
    if not isinstance(sensor, str) or not sensor.strip():
        sensor = "edge" if "edge" in temps else temps[0]
    result["temperature_key"] = sensor
    interval = result.get("interval_ms")
    result["interval_ms"] = interval if type(interval) is int and 100 <= interval <= 60000 else 500
    result["mode"] = mode
    result["static_speed"] = float(speed_percent) / 100
    existing_curve = result.get("curve")
    result["curve"] = deepcopy(curve if mode == "curve" else existing_curve or DEFAULT_FAN_CURVE)
    if not isinstance(result["curve"], dict) or len(result["curve"]) < 2:
        raise ValueError("Die Lüfterkurve benötigt mindestens zwei Punkte.")
    return result


def read_gpu_metrics(stats):
    """Present current readings, not editable clock limits, without invented data."""
    stats = stats if isinstance(stats, dict) else {}
    clocks = stats.get("clockspeed") or {}
    power = stats.get("power") or {}
    fan = stats.get("fan") or {}
    voltage = stats.get("voltage") or {}
    temps = stats.get("temps") or {}
    def sub(mapping, key):
        return mapping.get(key) if isinstance(mapping, dict) else None
    def fmt(value, unit, digits=0):
        return "–" if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) else f"{value:.{digits}f} {unit}"
    temps = temps if isinstance(temps, dict) else {}
    edge = sub(temps, "edge") or sub(temps, "junction")
    v = sub(edge, "current")
    return {
        "gpu": fmt(sub(clocks, "gpu_clockspeed"), "MHz"),
        "vram": fmt(sub(clocks, "vram_clockspeed"), "MHz"),
        "voltage": fmt(sub(voltage, "gpu"), "mV"),
        "temperature": fmt(v, "°C", 1),
        "power": fmt(sub(power, "average") if sub(power, "average") is not None else sub(power, "current"), "W", 1),
        "fan": fmt(sub(fan, "speed_current"), "U/min"),
        "power_cap": fmt(sub(power, "cap_current"), "W", 1),
        "load": fmt(sub(stats, "busy_percent"), "%"),
    }
