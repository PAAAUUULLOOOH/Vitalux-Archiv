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
  # ZIP installations keep precisely the last update's .backup. Restore this
  # working version if the new program exits abnormally; never roll back for
  # normal termination, terminal interruptions or session shutdown.
  case "$STATUS" in
    129|130|143) ;;
    *)
      if [ -z "${APPIMAGE:-}" ] && [ "${VITALUX_ROLLBACK_ACTIVE:-0}" != "1" ] && [ -f "$HERE/.backup/metadata.json" ] && [ -f "$HERE/.backup/vitalux/__main__.py" ]; then
        printf '\n=== Vitalux: Absturz mit Status %s, vorherige ZIP-Version wird wiederhergestellt ===\n' "$STATUS" >> "$LOG"
        if "$PY" -c '
import os, shutil
from vitalux import updater
updater.restore_previous()
shutil.rmtree(os.path.join(updater.app_root(), ".backup"))
' >> "$LOG" 2>&1; then
          echo 'Vitalux: vorherige Version wiederhergestellt; automatischer Neustart.' >> "$LOG"
          if command -v notify-send >/dev/null 2>&1; then
            notify-send 'Vitalux – Wiederherstellung' 'Die vorherige Version wurde nach einem Absturz automatisch wiederhergestellt.' >/dev/null 2>&1 || true
          fi
          export VITALUX_ROLLBACK_ACTIVE=1
          exec bash "$HERE/run.sh" "$@"
        fi
        echo 'Vitalux: automatische Wiederherstellung fehlgeschlagen; Backup nicht gelöscht.' >> "$LOG"
      fi
      ;;
  esac
  if [ "${VITALUX_GUARDED:-0}" = "1" ]; then
    # The external AppImage watchdog will restore the previous version.
    # Do not block automatic recovery behind a modal error dialog.
    echo "Vitalux: Fehlercode $STATUS – automatische Wiederherstellung läuft." >> "$LOG"
  else
    notify_error "Vitalux konnte nicht gestartet werden (Fehlercode $STATUS)."
  fi
  tail -n 30 "$LOG" >&2 || true
fi
exit "$STATUS"
