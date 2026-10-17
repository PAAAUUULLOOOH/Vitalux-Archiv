#!/usr/bin/env bash
# Vitalux – KDE/Wayland/X11 Portable-Starter (kein Terminal notwendig).
# Alle gebündelten Programmkomponenten bleiben im Vitalux-Verzeichnis.
set -u
if ! cd -- "$(dirname -- "${BASH_SOURCE[0]}")"; then
  printf 'Vitalux: Programmverzeichnis nicht erreichbar.\n' >&2
  exit 1
fi
HERE="$PWD"
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/vitalux"
mkdir -p -- "$STATE_DIR"
LOG="$STATE_DIR/vitalux.log"
QT_CHECK="$(mktemp "$STATE_DIR/.qtcheck.XXXXXX")"
trap 'rm -f -- "$QT_CHECK"' EXIT
PY="$HERE/runtime/bin/python3.12"
export PATH="$HERE/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# Python aus dem Portable-Paket statt aus der Host-Installation laden.
unset PYTHONHOME PYTHONPATH PYTHONUSERBASE

notify_error() {
  local title='Vitalux – Startfehler' message="$1"
  printf '%s\nDetails: %s\n' "$message" "$LOG" >&2
  # Bei Dolphin-Doppelklick sonst unsichtbare Fehler anzeigen.
  if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    if command -v kdialog >/dev/null 2>&1; then
      kdialog --title "$title" --error "$(printf '%s\n\nDetails: %s' "$message" "$LOG")" 2>/dev/null && return 0
    fi
    if [ -x "$PY" ]; then
      # Die mitgelieferte Qt-Laufzeit als eigenständigen Fehlerdialog nutzen.
      "$PY" -c 'import sys
from PySide6.QtWidgets import QApplication,QMessageBox
app=QApplication([])
QMessageBox.critical(None,"Vitalux – Startfehler",sys.argv[1]+"\n\nDetails: "+sys.argv[2])
' "$message" "$LOG" 2>/dev/null && return 0
    fi
    if command -v notify-send >/dev/null 2>&1; then
      notify-send "$title" "$message (siehe vitalux.log)" 2>/dev/null || true
    fi
  fi
}

# Some extractors discard executable bits. Recover local permissions offline.
if [ -f "$PY" ] && [ ! -x "$PY" ]; then chmod u+x -- "$PY" 2>/dev/null || true; fi
if [ -f "$HERE/bin/fio.real" ] && [ ! -x "$HERE/bin/fio.real" ]; then chmod u+x -- "$HERE/bin/fio.real" 2>/dev/null || true; fi
if [ -f "$HERE/bin/fio" ] && [ ! -x "$HERE/bin/fio" ]; then chmod u+x -- "$HERE/bin/fio" 2>/dev/null || true; fi
if [ ! -x "$PY" ]; then
  echo 'Fehler: Gebündeltes Python fehlt (runtime/bin/python3.12).' >>"$LOG"
  notify_error 'Die gebündelte Python-Laufzeit fehlt oder ist nicht ausführbar.'
  exit 1
fi
if ! "$PY" -c 'import PySide6.QtWidgets; import PySide6.QtSvg; import psutil' 2>"$QT_CHECK"; then
  { echo '=== Python/Qt konnte nicht geladen werden ==='; cat "$QT_CHECK"; } >>"$LOG"
  notify_error 'Die mitgelieferte Python/Qt-Laufzeit konnte nicht geladen werden.'
  exit 1
fi
rm -f -- "$QT_CHECK"
"$PY" -m vitalux >>"$LOG" 2>&1
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  notify_error "Vitalux konnte nicht gestartet werden (Fehlercode $STATUS)."
  tail -n 30 "$LOG" >&2 || true
fi
exit "$STATUS"
