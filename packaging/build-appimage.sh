#!/usr/bin/env bash
set -euo pipefail
SRC="$(realpath "${1:?source}")"
OUT="$(realpath -m "${2:?output}")"
TOOL="${3:?appimagetool}"
[[ -f "$SRC/run.sh" && -f "$SRC/runtime/bin/python3.12" && -f "$SRC/vitalux/__main__.py" && -f "$SRC/assets/vitalux.svg" ]] || exit 2
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DIR="$TMP/Vitalux.AppDir"
mkdir -p "$DIR" "$(dirname "$OUT")"
cp -a "$SRC"/. "$DIR"/
rm -rf "$DIR/.git" "$DIR/.github" "$DIR/.build" "$DIR/.pytest_cache" "$DIR/tests"
rm -f "$DIR/Vitalux-starten.desktop" "$DIR/Vitalux-im-Menue-installieren.sh" "$DIR/Vitalux-installieren.sh" "$DIR/Vitalux-deinstallieren.sh"
mkdir -p "$DIR/packaging"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/AppRun" "$DIR/AppRun"
cp "$HERE/appimage-first-run.py" "$DIR/packaging/"
cp "$HERE/appimage-integration.sh" "$DIR/packaging/"
cp "$HERE/appimage-rollback-watch.sh" "$DIR/packaging/"
chmod 755 "$DIR/AppRun" "$DIR/packaging/appimage-integration.sh" "$DIR/packaging/appimage-rollback-watch.sh" "$DIR/run.sh" "$DIR/runtime/bin/python3.12"
cp "$DIR/assets/vitalux.svg" "$DIR/vitalux.svg"
ln -s vitalux.svg "$DIR/.DirIcon"
cat > "$DIR/vitalux.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Vitalux
Comment=Linux Hardware- und Systemmonitor
Exec=AppRun
Icon=vitalux
Terminal=false
Categories=System;Monitor;
DESKTOP
ARCH=x86_64 "$TOOL" --no-appstream "$DIR" "$OUT"
test -s "$OUT"
chmod 755 "$OUT"
