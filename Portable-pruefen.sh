#!/usr/bin/env bash
# Offline-Kontrolle ohne Installation oder Benchmark-Schreibvorgang.
set -u
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1
ROOT="$PWD"
PY="$ROOT/runtime/bin/python3.12"
export LD_LIBRARY_PATH="$ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# Set execute bits only in own extracted app directory.
for executable in "$PY" "$ROOT/bin/fio" "$ROOT/bin/fio.real"; do
  if [[ -f "$executable" && ! -x "$executable" ]]; then chmod u+x -- "$executable" 2>/dev/null || true; fi
done
if [[ ! -x "$PY" ]]; then
  printf 'FEHLER: gebuendelte Python-Laufzeit fehlt oder ist nicht ausfuehrbar.\n' >&2
  exit 1
fi
"$PY" -m vitalux.portable_diagnostics --display
