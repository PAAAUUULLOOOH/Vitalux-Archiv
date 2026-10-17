#!/usr/bin/env bash
# One-version recovery guard for installed/portable Vitalux AppImages.
# The .previous AppImage is preserved on healthy exits and replaced by the
# immediate predecessor on the next update. No user downloads are touched.
set -u
BASE="${1:?AppDir}"
TARGET="${2:?AppImage}"
shift 2
PREVIOUS="${TARGET}.previous"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/vitalux"
mkdir -p -- "$STATE"
LOG="$STATE/restart.log"
# The running mount identifies the exact version that failed.
VERSION="$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' "$BASE/vitalux/__init__.py" 2>/dev/null)"
log_line() {
  printf '[%s] [Vitalux v%s] %s\n' "$(date -Is)" "${VERSION:-unknown}" "$*" >> "$LOG"
}
log_child() {
  while IFS= read -r line || [[ -n "$line" ]]; do
    log_line "$line"
  done
}

# Never trust or follow an unrelated/symlinked rollback file.
if [[ ! -f "$PREVIOUS" || -L "$PREVIOUS" || ! -f "$TARGET" || -L "$TARGET" ]]; then
  exec bash "$BASE/run.sh" "$@"
fi

log_line "Starting updated Vitalux with previous version retained."
# Our normal launcher captures Python and Qt diagnostics in vitalux.log.
# Wait for the real application, not the AppImage mount/launcher alone.
VITALUX_GUARDED=1 bash "$BASE/run.sh" "$@"
status=$?
case "$status" in
  0|129|130|143)
    # Normal exit, terminal interrupt or a typical session-shutdown signal.
    # Retain previous until the NEXT successful update replaces it.
    exit "$status"
    ;;
esac

log_line "Vitalux exited unexpectedly (status $status). Attempting rollback."
if [[ ! -f "$PREVIOUS" || -L "$PREVIOUS" || ! -f "$TARGET" || -L "$TARGET" ]]; then
  log_line "Rollback skipped: valid previous AppImage no longer present."
  exit "$status"
fi
TMP="$(mktemp "${TARGET}.rollback-XXXXXXXX")" || exit "$status"
trap 'rm -f -- "$TMP"' EXIT
if ! cp -p -- "$PREVIOUS" "$TMP"; then
  log_line "Rollback copy failed."
  exit "$status"
fi
chmod u+x "$TMP" || exit "$status"
if ! mv -f -- "$TMP" "$TARGET"; then
  log_line "Rollback swap failed."
  exit "$status"
fi
trap - EXIT
rm -f -- "$PREVIOUS"
log_line "Recovered previous Vitalux version. Restarting it."
# Launch the restored version once, without inheriting the failed AppImage mount.
unset APPDIR APPIMAGE LD_LIBRARY_PATH LD_PRELOAD PYTHONHOME PYTHONPATH PYTHONUSERBASE
( "$TARGET" --launch "$@" 2>&1 | log_child ) &
exit 0
