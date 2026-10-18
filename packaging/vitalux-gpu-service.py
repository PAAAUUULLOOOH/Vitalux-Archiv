#!/usr/bin/env python3
"""One-time, explicitly authorized system-service setup for Vitalux GPU tuning.

Runs only when the user clicks 'GPU-Steuerung einrichten' and approves polkit.
Ships an unchanged upstream open-source GPU backend, not a replacement GUI.
The backend must run as a host system service to work on Wayland and X11.
"""
from __future__ import annotations

import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "bin" / "vitalux-gpu-engine"
INSTALLED_ENGINE = Path("/usr/local/libexec/vitalux/gpu-engine")
UNIT = Path("/etc/systemd/system/vitalux-gpu.service")
CONFIG = Path("/etc/lact/config.yaml")
LICENSE = ROOT / "LICENSES" / "LACT-MIT.txt"
INSTALLED_LICENSE = Path("/usr/local/share/doc/vitalux-gpu/LACT-MIT.txt")

SERVICE = """[Unit]
Description=Vitalux GPU-Steuerung
After=multi-user.target
ConditionPathExists=/usr/local/libexec/vitalux/gpu-engine

[Service]
Type=simple
ExecStart=/usr/local/libexec/vitalux/gpu-engine daemon
Nice=-10
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
"""


def run(*args):
    subprocess.run(args, check=True, timeout=35)


def authorized_username():
    """Trust polkit's caller UID; never accept a user name from the command line."""
    if os.geteuid() != 0:
        raise RuntimeError("Für die Systemeinrichtung ist eine Administratorbestätigung erforderlich.")
    value = os.environ.get("PKEXEC_UID")
    if not value or not value.isdecimal():
        raise RuntimeError("Bitte die Einrichtung über Vitalux und die Administratorabfrage starten.")
    entry = pwd.getpwuid(int(value))
    if entry.pw_uid == 0 or not re.fullmatch(r"[a-z_][a-z0-9_.-]*[$]?", entry.pw_name):
        raise RuntimeError("Unzulässiges Benutzerkonto für die GPU-Steuerung.")
    return entry.pw_name


def configured_for_user(content, username):
    """Conservative insertion into top-level 'daemon:' YAML settings only."""
    rows = content.splitlines(keepends=True)
    headers = [i for i, row in enumerate(rows) if re.match(r"^daemon:\s*(?:#.*)?$", row)]
    if not headers:
        if re.search(r"^daemon:", content, re.M):
            raise RuntimeError("Bestehende, nicht unterstützte daemon-Konfiguration wird nicht überschrieben.")
        return (content.rstrip("\n") + "\n" if content.strip() else "version: 7\n") + f"daemon:\n  log_level: info\n  admin_user: {username}\n"
    start = headers[0]
    end = next((i for i in range(start + 1, len(rows))
                if rows[i].strip() and not rows[i].startswith((" ", "\t", "#"))),
               len(rows))
    for i in range(start + 1, end):
        match = re.match(r"^\s+admin_user:\s*([^#\n]*)", rows[i])
        if match:
            value = match.group(1).strip().strip("\"'")
            if value != username:
                raise RuntimeError("Die GPU-Konfiguration erlaubt einem anderen Administrator Zugriff. "
                                   "Vitalux ändert diese vorhandene Berechtigung nicht.")
            return content
    rows.insert(start + 1, f"  admin_user: {username}\n")
    return "".join(rows)


def install(username):
    if not ENGINE.is_file() or ENGINE.stat().st_size < 100_000 or not LICENSE.is_file():
        raise RuntimeError("Der originale GPU-Steuerungsdienst fehlt im Vitalux-Paket.")
    # Never interfere with another product's already-running GPU service.
    if subprocess.run(["systemctl", "is-active", "--quiet", "lactd.service"],
                      check=False, timeout=8).returncode == 0:
        raise RuntimeError("Ein anderer GPU-Dienst ist bereits aktiv. "
                           "Bitte zuerst dessen Socketberechtigungen prüfen.")
    old_config = CONFIG.read_text(encoding="utf-8") if CONFIG.is_file() else ""
    updated = configured_for_user(old_config, username)
    INSTALLED_ENGINE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ENGINE, INSTALLED_ENGINE)
    INSTALLED_ENGINE.chmod(0o755)
    INSTALLED_LICENSE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LICENSE, INSTALLED_LICENSE)
    INSTALLED_LICENSE.chmod(0o644)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if updated != old_config or not CONFIG.exists():
        if CONFIG.is_file():
            backup = CONFIG.with_suffix(".yaml.vitalux-backup")
            if not backup.exists():
                shutil.copy2(CONFIG, backup)
        # Keep GPU config readable only by root to avoid exposing config hooks.
        CONFIG.write_text(updated, encoding="utf-8")
        CONFIG.chmod(0o600)
    UNIT.write_text(SERVICE, encoding="utf-8")
    UNIT.chmod(0o644)
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", "vitalux-gpu.service")
    if subprocess.run(["systemctl", "is-active", "--quiet", "vitalux-gpu.service"],
                      check=False, timeout=8).returncode:
        raise RuntimeError("Vitalux GPU-Steuerung konnte nicht gestartet werden.")
    print("Vitalux GPU-Steuerung aktiviert.")


def remove():
    if UNIT.is_file():
        run("systemctl", "disable", "--now", "vitalux-gpu.service")
        UNIT.unlink()
        run("systemctl", "daemon-reload")
    INSTALLED_ENGINE.unlink(missing_ok=True)
    INSTALLED_LICENSE.unlink(missing_ok=True)
    # User profiles and overclock configurations intentionally remain intact.
    print("Vitalux GPU-Steuerung entfernt. Gespeicherte Profile bleiben erhalten.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--install", "--remove"):
        raise RuntimeError("Unbekannter Installationsauftrag.")
    username = authorized_username()
    if sys.argv[1] == "--install":
        install(username)
    else:
        remove()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        print(f"Vitalux GPU-Steuerung: {exc}", file=sys.stderr)
        sys.exit(1)
