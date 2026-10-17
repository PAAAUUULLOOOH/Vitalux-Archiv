#!/usr/bin/env bash
set -euo pipefail
MODE="${1:---install}"
SRC="${APPIMAGE:-}"
DIR="$HOME/.local/opt/vitalux"
TARGET="$DIR/Vitalux.AppImage"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
MENU="$DATA/applications/vitalux.desktop"
ICON="$DATA/icons/hicolor/scalable/apps/vitalux.svg"
LAUNCH="$HOME/.local/bin/vitalux"
if [[ "$MODE" == "--uninstall" ]]; then
  rm -f -- "$MENU" "$ICON" "$LAUNCH" "$TARGET" "$TARGET.previous"
  echo 'Vitalux deinstalliert; Benutzereinstellungen bleiben erhalten.'
  exit 0
fi
[[ "$MODE" == "--install" && -f "$SRC" && -f "${APPDIR:-}/assets/vitalux.svg" ]] || exit 2
mkdir -p "$DIR" "$(dirname "$MENU")" "$(dirname "$ICON")" "$(dirname "$LAUNCH")"
if [[ "$(realpath "$SRC")" != "$(realpath -m "$TARGET")" ]]; then
  TEMP="$(mktemp "$DIR/.vitalux-new-XXXXXXXX")"
  trap 'rm -f -- "${TEMP:-}"' EXIT
  cp "$SRC" "$TEMP"
  chmod 755 "$TEMP"
  [[ ! -f "$TARGET" ]] || cp -p "$TARGET" "$TARGET.previous"
  mv -f "$TEMP" "$TARGET"
  trap - EXIT
fi
cp -f "$APPDIR/assets/vitalux.svg" "$ICON"
cat > "$LAUNCH" <<'WRAPPER'
#!/usr/bin/env bash
exec "$HOME/.local/opt/vitalux/Vitalux.AppImage" --launch "$@"
WRAPPER
chmod 755 "$LAUNCH"
printf '[Desktop Entry]\nType=Application\nName=Vitalux\nExec="%s"\nTryExec=%s\nIcon=vitalux\nTerminal=false\nCategories=System;Monitor;\n' "$LAUNCH" "$LAUNCH" > "$MENU"
chmod 644 "$MENU"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$(dirname "$MENU")" >/dev/null 2>&1 || true
echo 'Vitalux ist im Anwendungsmenü installiert.'
