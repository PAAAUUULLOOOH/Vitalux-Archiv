#!/usr/bin/env bash
# Vitalux – KDE/Wayland/X11 Portable-Starter (kein Terminal notwendig).
# Alle gebündelten Programmkomponenten bleiben im Vitalux-Verzeichnis.
set -uo pipefail
if ! cd -- "$(dirname -- "${BASH_SOURCE[0]}")"; then
  printf 'Vitalux: Programmverzeichnis nicht erreichbar.\n' >&2
  exit 1
fi
HERE="$PWD"
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/vitalux"
mkdir -p -- "$STATE_DIR"
LOG="$STATE_DIR/vitalux.log"
# Every launcher, Python and Qt diagnostic line carries a local ISO-8601 time
# and timezone, even when a native malloc/Qt abort bypasses Python handlers.
log_line() {
  printf '[%s] [Vitalux v%s] %s\n' "$(date -Is)" "${VERSION:-unknown}" "$*" >>"$LOG"
}
VERSION="$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' "$HERE/vitalux/__init__.py" 2>/dev/null)"
log_line "=== Vitalux ${VERSION:-unknown} start (launcher PID $BASHPID) ==="
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
  log_line 'Fehler: Gebündeltes Python fehlt (runtime/bin/python3.12).'
  notify_error 'Die gebündelte Python-Laufzeit fehlt oder ist nicht ausführbar.'
  exit 1
fi
if ! "$PY" -c 'import PySide6.QtWidgets; import PySide6.QtSvg; import psutil' 2>"$QT_CHECK"; then
  log_line '=== Python/Qt konnte nicht geladen werden ==='
  while IFS= read -r line || [[ -n "$line" ]]; do
    log_line "$line"
  done <"$QT_CHECK"
  notify_error 'Die mitgelieferte Python/Qt-Laufzeit konnte nicht geladen werden.'
  exit 1
fi
rm -f -- "$QT_CHECK"
# Capture stdout and stderr together to retain the original event ordering.
# PIPESTATUS[0] is the *app's* exit code, not that of the log writer.
"$PY" -m vitalux 2>&1 | while IFS= read -r line || [[ -n "$line" ]]; do
  log_line "$line"
done
STATUS=${PIPESTATUS[0]}
log_line "=== Vitalux ended (exit code $STATUS) ==="
if [ "$STATUS" -eq 42 ]; then
  log_line '=== Grafik-Rendering geändert – Vitalux wird kontrolliert neu gestartet ==='
  exec bash "$HERE/run.sh" "$@"
fi
if [ "$STATUS" -ne 0 ]; then
  # Python's fatal handler writes raw native frames to errors.log before
  # exiting. A post-crash footer gives that frame block the crash *time*
  # and exact version, even if no Python exception could be raised.
  printf '[%s] [Vitalux v%s] Process crashed (exit code %s; see vitalux.log)\n' \
    "$(date -Is)" "${VERSION:-unknown}" "$STATUS" >>"$STATE_DIR/errors.log"
  # ZIP installations keep precisely the last update's .backup. Restore this
  # working version if the new program exits abnormally; never roll back for
  # normal termination, terminal interruptions or session shutdown.
  case "$STATUS" in
    129|130|143) ;;
    *)
      if [ -z "${APPIMAGE:-}" ] && [ "${VITALUX_ROLLBACK_ACTIVE:-0}" != "1" ] && [ -f "$HERE/.backup/metadata.json" ] && [ -f "$HERE/.backup/vitalux/__main__.py" ]; then
        log_line "=== Vitalux: Absturz mit Status $STATUS, vorherige ZIP-Version wird wiederhergestellt ==="
        if "$PY" -c '
import os, shutil
from vitalux import updater
updater.restore_previous()
shutil.rmtree(os.path.join(updater.app_root(), ".backup"))
' 2>&1 | while IFS= read -r line || [[ -n "$line" ]]; do
          log_line "$line"
        done; then
          log_line 'Vitalux: vorherige Version wiederhergestellt; automatischer Neustart.'
          if command -v notify-send >/dev/null 2>&1; then
            notify-send 'Vitalux – Wiederherstellung' 'Die vorherige Version wurde nach einem Absturz automatisch wiederhergestellt.' >/dev/null 2>&1 || true
          fi
          export VITALUX_ROLLBACK_ACTIVE=1
          exec bash "$HERE/run.sh" "$@"
        fi
        log_line 'Vitalux: automatische Wiederherstellung fehlgeschlagen; Backup nicht gelöscht.'
      fi
      ;;
  esac
  if [ "${VITALUX_GUARDED:-0}" = "1" ]; then
    # The external AppImage watchdog will restore the previous version.
    # Do not block automatic recovery behind a modal error dialog.
    log_line "Vitalux: Fehlercode $STATUS – automatische Wiederherstellung läuft."
  else
    notify_error "Vitalux konnte nicht gestartet werden (Fehlercode $STATUS)."
  fi
  tail -n 30 "$LOG" >&2 || true
fi
exit "$STATUS"
