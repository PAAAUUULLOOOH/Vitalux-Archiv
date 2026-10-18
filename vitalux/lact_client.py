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
            raise LactError("LACT-Dienst nicht gefunden. Installiere LACT und aktiviere lactd.") from exc
        except PermissionError as exc:
            raise LactError("Kein Zugriff auf /run/lactd.sock. Prüfe admin_user/admin_group in /etc/lact/config.yaml.") from exc
        except (OSError, TimeoutError) as exc:
            raise LactError(f"LACT-Verbindung fehlgeschlagen: {exc}") from exc
        if not line or len(line) > MAX_REPLY_BYTES:
            raise LactError("LACT hat keine gültige oder eine zu große Antwort geliefert.")
        try:
            response = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise LactError("Ungültige Antwort vom LACT-Dienst.") from exc
        if not isinstance(response, dict) or response.get("status") not in ("ok", "error"):
            raise LactError("Unbekanntes LACT-Antwortformat.")
        if response["status"] == "error":
            raise LactError(str(response.get("data") or "LACT hat den Befehl abgelehnt."))
        return response.get("data")

    def devices(self):
        data = self.request("list_devices")
        if not isinstance(data, list):
            raise LactError("Ungültige LACT-Geräteliste.")
        return [item for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]

    def gpu_config(self, gpu_id):
        data = self.request("get_gpu_config", {"id": gpu_id})
        # LACT returns null for an untouched GPU. In that case its actual
        # GpuConfig default is the empty JSON object.
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise LactError("Ungültige LACT-GPU-Konfiguration.")
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
            raise LactError("Ungültige LACT-Profilantwort.")
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
                       "fan_control_settings", *CLOCK_FIELDS):
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
