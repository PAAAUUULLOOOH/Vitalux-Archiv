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

# Never trust or follow an unrelated/symlinked rollback file.
if [[ ! -f "$PREVIOUS" || -L "$PREVIOUS" || ! -f "$TARGET" || -L "$TARGET" ]]; then
  exec bash "$BASE/run.sh" "$@"
fi

echo "[$(date -Is)] Starting updated Vitalux with previous version retained." >> "$LOG"
# Our normal launcher captures Python and Qt diagnostics in vitalux.log.
# Wait for the real application, not the AppImage mount/launcher alone.
bash "$BASE/run.sh" "$@"
status=$?
case "$status" in
  0|129|130|143)
    # Normal exit, terminal interrupt or a typical session-shutdown signal.
    # Retain previous until the NEXT successful update replaces it.
    exit "$status"
    ;;
esac

echo "[$(date -Is)] Vitalux exited unexpectedly (status $status). Attempting rollback." >> "$LOG"
if [[ ! -f "$PREVIOUS" || -L "$PREVIOUS" || ! -f "$TARGET" || -L "$TARGET" ]]; then
  echo "[$(date -Is)] Rollback skipped: valid previous AppImage no longer present." >> "$LOG"
  exit "$status"
fi
TMP="$(mktemp "${TARGET}.rollback-XXXXXXXX")" || exit "$status"
trap 'rm -f -- "$TMP"' EXIT
if ! cp -p -- "$PREVIOUS" "$TMP"; then
  echo "[$(date -Is)] Rollback copy failed." >> "$LOG"
  exit "$status"
fi
chmod u+x "$TMP" || exit "$status"
if ! mv -f -- "$TMP" "$TARGET"; then
  echo "[$(date -Is)] Rollback swap failed." >> "$LOG"
  exit "$status"
fi
trap - EXIT
rm -f -- "$PREVIOUS"
echo "[$(date -Is)] Recovered previous Vitalux version. Restarting it." >> "$LOG"
# Launch the restored version once, without inheriting the failed AppImage mount.
unset APPDIR APPIMAGE LD_LIBRARY_PATH LD_PRELOAD PYTHONHOME PYTHONPATH PYTHONUSERBASE
"$TARGET" --launch "$@" >> "$LOG" 2>&1 &
exit 0
